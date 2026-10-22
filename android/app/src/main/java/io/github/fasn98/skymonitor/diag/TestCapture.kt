package io.github.fasn98.skymonitor.diag

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.ImageFormat
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraMetadata
import android.hardware.camera2.CaptureFailure
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.CaptureResult
import android.hardware.camera2.DngCreator
import android.hardware.camera2.TotalCaptureResult
import android.hardware.camera2.params.OutputConfiguration
import android.hardware.camera2.params.SessionConfiguration
import android.media.Image
import android.media.ImageReader
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.concurrent.Executor

/**
 * One long-exposure RAW capture with fully manual settings, saved as DNG.
 *
 * The point is to verify, on the real device, that what CameraCharacteristics advertises
 * is honoured: the requested exposure time and ISO are compared with the values the
 * camera reports in the capture result (SENSOR_EXPOSURE_TIME / SENSOR_SENSITIVITY), and
 * the wall-clock duration of the capture is measured independently.
 *
 * All callbacks run on a private HandlerThread. [log] must be thread-safe.
 */
class TestCapture(
    private val context: Context,
    private val manager: CameraManager,
    private val log: (String) -> Unit,
    private val onFinished: () -> Unit,
) {
    private val thread = HandlerThread("skymonitor-diag-capture").apply { start() }
    private val handler = Handler(thread.looper)
    private val executor = Executor { handler.post(it) }

    private var camera: CameraDevice? = null
    private var session: CameraCaptureSession? = null
    private var reader: ImageReader? = null
    private var image: Image? = null
    private var result: TotalCaptureResult? = null
    private var finished = false

    private lateinit var cameraId: String
    private lateinit var characteristics: CameraCharacteristics
    private var requestedExposureNs = 0L
    private var requestedIso = 0
    private var startedAtMs = 0L

    @SuppressLint("MissingPermission") // Caller only starts after CAMERA permission is granted.
    fun start(cameraId: String, exposureSeconds: Double, iso: Int) {
        handler.post {
            try {
                this.cameraId = cameraId
                characteristics = manager.getCameraCharacteristics(cameraId)
                val expRange = characteristics.get(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE)
                    ?: return@post fail("Câmera não informa a faixa de exposição")
                val isoRange = characteristics.get(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE)
                    ?: return@post fail("Câmera não informa a faixa de ISO")

                val wantedNs = (exposureSeconds * 1e9).toLong()
                requestedExposureNs = wantedNs.coerceIn(expRange.lower, expRange.upper)
                requestedIso = iso.coerceIn(isoRange.lower, isoRange.upper)
                if (requestedExposureNs != wantedNs) {
                    log("Aviso: exposição ajustada para ${fmt(requestedExposureNs / 1e9, 3)} s (limite da câmera)")
                }
                if (requestedIso != iso) log("Aviso: ISO ajustado para $requestedIso (limite da câmera)")

                val rawSize = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
                    ?.getOutputSizes(ImageFormat.RAW_SENSOR)
                    ?.maxByOrNull { it.width.toLong() * it.height }
                    ?: return@post fail("Câmera sem saída RAW_SENSOR")

                val r = ImageReader.newInstance(rawSize.width, rawSize.height, ImageFormat.RAW_SENSOR, 2)
                r.setOnImageAvailableListener({ rd ->
                    image = rd.acquireNextImage()
                    maybeSave()
                }, handler)
                reader = r

                val timeoutMs = requestedExposureNs / 1_000_000 + 30_000
                handler.postDelayed({ fail("Tempo esgotado após ${timeoutMs / 1000} s") }, timeoutMs)

                log("Abrindo câmera $cameraId (RAW ${rawSize.width}x${rawSize.height})…")
                manager.openCamera(cameraId, executor, object : CameraDevice.StateCallback() {
                    override fun onOpened(device: CameraDevice) {
                        camera = device
                        createSession(device, r)
                    }

                    override fun onDisconnected(device: CameraDevice) = fail("Câmera desconectada")
                    override fun onError(device: CameraDevice, error: Int) =
                        fail("Erro ao abrir a câmera (código $error)")
                })
            } catch (e: Exception) {
                fail("${e.javaClass.simpleName}: ${e.message}")
            }
        }
    }

    private fun createSession(device: CameraDevice, r: ImageReader) {
        val config = SessionConfiguration(
            SessionConfiguration.SESSION_REGULAR,
            listOf(OutputConfiguration(r.surface)),
            executor,
            object : CameraCaptureSession.StateCallback() {
                override fun onConfigured(s: CameraCaptureSession) {
                    session = s
                    capture(device, s, r)
                }

                override fun onConfigureFailed(s: CameraCaptureSession) = fail("Falha ao configurar a sessão")
            },
        )
        device.createCaptureSession(config)
    }

    private fun capture(device: CameraDevice, s: CameraCaptureSession, r: ImageReader) {
        try {
            val b = device.createCaptureRequest(CameraDevice.TEMPLATE_MANUAL)
            b.addTarget(r.surface)
            b.set(CaptureRequest.CONTROL_MODE, CameraMetadata.CONTROL_MODE_OFF)
            b.set(CaptureRequest.CONTROL_AE_MODE, CameraMetadata.CONTROL_AE_MODE_OFF)
            b.set(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_OFF)
            val minFocus = characteristics.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE) ?: 0f
            if (minFocus > 0f) b.set(CaptureRequest.LENS_FOCUS_DISTANCE, 0f) // 0 diopters = infinity
            b.set(CaptureRequest.SENSOR_EXPOSURE_TIME, requestedExposureNs)
            b.set(CaptureRequest.SENSOR_FRAME_DURATION, requestedExposureNs)
            b.set(CaptureRequest.SENSOR_SENSITIVITY, requestedIso)
            val nrModes = characteristics.get(CameraCharacteristics.NOISE_REDUCTION_AVAILABLE_NOISE_REDUCTION_MODES)
            if (nrModes?.contains(CameraMetadata.NOISE_REDUCTION_MODE_OFF) == true) {
                b.set(CaptureRequest.NOISE_REDUCTION_MODE, CameraMetadata.NOISE_REDUCTION_MODE_OFF)
            }

            log(
                "Capturando: ${fmt(requestedExposureNs / 1e9, 3)} s, ISO $requestedIso, foco infinito" +
                    if (minFocus > 0f) "" else " (foco fixo)",
            )
            startedAtMs = SystemClock.elapsedRealtime()
            s.capture(b.build(), object : CameraCaptureSession.CaptureCallback() {
                override fun onCaptureCompleted(
                    session: CameraCaptureSession,
                    request: CaptureRequest,
                    res: TotalCaptureResult,
                ) {
                    result = res
                    maybeSave()
                }

                override fun onCaptureFailed(
                    session: CameraCaptureSession,
                    request: CaptureRequest,
                    failure: CaptureFailure,
                ) = fail("Captura falhou (motivo ${failure.reason})")
            }, handler)
        } catch (e: Exception) {
            fail("${e.javaClass.simpleName}: ${e.message}")
        }
    }

    private fun maybeSave() {
        if (finished) return
        val img = image ?: return
        val res = result ?: return
        val elapsedS = (SystemClock.elapsedRealtime() - startedAtMs) / 1000.0

        val actualExpNs = res.get(CaptureResult.SENSOR_EXPOSURE_TIME)
        val actualIso = res.get(CaptureResult.SENSOR_SENSITIVITY)
        log("Resultado informado pela câmera:")
        log("  exposição pedida ${fmt(requestedExposureNs / 1e9, 3)} s → informada ${actualExpNs?.let { fmt(it / 1e9, 3) + " s" } ?: "não informada"}")
        log("  ISO pedido $requestedIso → informado ${actualIso ?: "não informado"}")
        log("  duração real da captura (relógio): ${fmt(elapsedS, 1)} s")
        if (actualExpNs != null && actualExpNs < requestedExposureNs * 0.95) {
            log("  ⚠ A câmera usou MENOS exposição do que a pedida.")
        }

        try {
            val stamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"))
            val name = "skymonitor_diag_cam${cameraId}_$stamp.dng"
            Downloads.save(context, name, "image/x-adobe-dng") { out ->
                val creator = DngCreator(characteristics, res)
                try {
                    creator.writeImage(out, img)
                } finally {
                    creator.close()
                }
            }
            log("DNG salvo em ${Downloads.FOLDER_LABEL}/$name")
            finish("Captura de teste concluída.")
        } catch (e: Exception) {
            fail("Erro ao salvar DNG: ${e.javaClass.simpleName}: ${e.message}")
        }
    }

    private fun fail(message: String) {
        if (finished) return
        log("ERRO: $message")
        finish(null)
    }

    private fun finish(message: String?) {
        if (finished) return
        finished = true
        message?.let(log)
        handler.removeCallbacksAndMessages(null)
        runCatching { session?.close() }
        runCatching { camera?.close() }
        runCatching { image?.close() }
        runCatching { reader?.close() }
        thread.quitSafely()
        onFinished()
    }
}
