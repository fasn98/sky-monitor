package io.github.fasn98.skymonitor.diag

import android.graphics.ImageFormat
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraMetadata
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.time.OffsetDateTime
import java.util.Locale
import kotlin.math.atan
import kotlin.math.sqrt

/**
 * What a third-party app can actually use on this device, per camera.
 *
 * Every value comes from CameraCharacteristics (Android Camera2 API reference:
 * https://developer.android.com/reference/android/hardware/camera2/CameraCharacteristics).
 * Nothing is estimated except the field of view, which is labelled as a rectilinear
 * approximation (wide lenses have distortion, so the real FOV differs).
 */
data class CameraInfo(
    val id: String,
    val parentLogicalId: String?,
    val openableDirectly: Boolean,
    val facing: String,
    val rawCapable: Boolean,
    val manualSensor: Boolean,
    val focalLengthsMm: List<Double>,
    val maxExposureS: Double?,
    val isoRange: Pair<Int, Int>?,
    val diagonalFovDeg: Double?,
    val json: JSONObject,
) {
    /** Usable by the test capture: opened directly, RAW output and manual exposure. */
    val captureEligible: Boolean get() = openableDirectly && rawCapable && manualSensor

    fun label(): String {
        val focal = focalLengthsMm.joinToString("/") { fmt(it, 2) }
        val exp = maxExposureS?.let { "${fmt(it, 1)} s" } ?: "?"
        return "Câmera $id · $facing · ${focal} mm · exp. máx $exp"
    }

    fun summary(): String = buildString {
        append("■ Câmera ").append(id)
        if (parentLogicalId != null) append(" (física, dentro da lógica ").append(parentLogicalId).append(")")
        append('\n')
        append("  Lado: ").append(facing)
        append(" · Pode ser aberta direto: ").append(yesNo(openableDirectly)).append('\n')
        append("  Focal: ").append(focalLengthsMm.joinToString(", ") { fmt(it, 2) }).append(" mm")
        diagonalFovDeg?.let { append(" · FOV diagonal ≈ ").append(fmt(it, 0)).append("° (aprox.)") }
        append('\n')
        append("  RAW: ").append(yesNo(rawCapable))
        append(" · Exposição manual: ").append(yesNo(manualSensor)).append('\n')
        append("  Exposição máxima: ").append(maxExposureS?.let { "${fmt(it, 2)} s" } ?: "não informada")
        isoRange?.let { append(" · ISO: ").append(it.first).append("–").append(it.second) }
        append('\n')
        append("  → Captura de teste: ")
        append(
            when {
                captureEligible -> "SIM"
                !openableDirectly -> "não (só acessível via câmera lógica)"
                else -> "não (falta RAW ou exposição manual)"
            },
        )
        append('\n')
    }

    private fun yesNo(b: Boolean) = if (b) "sim" else "não"
}

internal fun fmt(value: Double, decimals: Int): String =
    String.format(Locale.ROOT, "%.${decimals}f", value)

object CameraReport {

    fun collect(manager: CameraManager): List<CameraInfo> {
        val openable = manager.cameraIdList.toList()
        val result = openable.map { id -> describe(id, null, true, manager.getCameraCharacteristics(id)) }
            .toMutableList()
        val seen = openable.toMutableSet()
        for (logicalId in openable) {
            val physicalIds = manager.getCameraCharacteristics(logicalId).physicalCameraIds
            for (pid in physicalIds) {
                if (seen.add(pid)) {
                    result += describe(pid, logicalId, false, manager.getCameraCharacteristics(pid))
                }
            }
        }
        return result
    }

    fun toJson(cameras: List<CameraInfo>, cameraPermissionGranted: Boolean): JSONObject =
        JSONObject()
            .put("schema", "skymonitor.camera-diagnostic/1")
            .put("generated_at", OffsetDateTime.now().toString())
            .put(
                "device",
                JSONObject()
                    .put("manufacturer", Build.MANUFACTURER)
                    .put("model", Build.MODEL)
                    .put("android_release", Build.VERSION.RELEASE)
                    .put("sdk_int", Build.VERSION.SDK_INT)
                    .put("build_fingerprint", Build.FINGERPRINT),
            )
            .put("camera_permission_granted", cameraPermissionGranted)
            .put("cameras", JSONArray(cameras.map { it.json }))

    private fun describe(
        id: String,
        parent: String?,
        openable: Boolean,
        ch: CameraCharacteristics,
    ): CameraInfo {
        val j = JSONObject()
        j.put("id", id)
        j.put("parent_logical_id", parent ?: JSONObject.NULL)
        j.put("openable_directly", openable)

        val facing = when (ch.get(CameraCharacteristics.LENS_FACING)) {
            CameraMetadata.LENS_FACING_BACK -> "traseira"
            CameraMetadata.LENS_FACING_FRONT -> "frontal"
            CameraMetadata.LENS_FACING_EXTERNAL -> "externa"
            else -> "desconhecida"
        }
        j.put("facing", facing)
        j.put("hardware_level", hardwareLevel(ch.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL)))

        val caps = ch.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)?.toList().orEmpty()
        j.put("capabilities", JSONArray(caps.map(::capabilityName)))
        val raw = CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_RAW in caps
        val manual = CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR in caps

        val focal = ch.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)
            ?.map { it.toDouble() }.orEmpty()
        j.put("focal_lengths_mm", JSONArray(focal))

        val size = ch.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)
        if (size != null) {
            j.put("sensor_physical_size_mm", JSONArray(listOf(size.width.toDouble(), size.height.toDouble())))
        }
        ch.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE)?.let {
            j.put("pixel_array_size", JSONArray(listOf(it.width, it.height)))
        }
        ch.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE)?.let {
            j.put("active_array_rect", JSONArray(listOf(it.left, it.top, it.right, it.bottom)))
        }

        var diagonalFov: Double? = null
        val f = focal.minOrNull()
        if (f != null && f > 0 && size != null) {
            val w = size.width.toDouble()
            val h = size.height.toDouble()
            fun fov(d: Double) = Math.toDegrees(2 * atan(d / (2 * f)))
            diagonalFov = fov(sqrt(w * w + h * h))
            j.put(
                "fov_deg_rectilinear_approx",
                JSONObject().put("horizontal", fov(w)).put("vertical", fov(h)).put("diagonal", diagonalFov),
            )
        }

        val exposure = ch.get(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE)
        val maxExposureS = exposure?.upper?.let { it / 1e9 }
        if (exposure != null) {
            j.put("exposure_time_range_s", JSONArray(listOf(exposure.lower / 1e9, exposure.upper / 1e9)))
        }
        ch.get(CameraCharacteristics.SENSOR_INFO_MAX_FRAME_DURATION)?.let {
            j.put("max_frame_duration_s", it / 1e9)
        }
        val iso = ch.get(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE)
        if (iso != null) j.put("sensitivity_range_iso", JSONArray(listOf(iso.lower, iso.upper)))
        ch.get(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY)?.let {
            j.put("max_analog_sensitivity_iso", it)
        }

        val map = ch.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
        val rawSizes = map?.getOutputSizes(ImageFormat.RAW_SENSOR)?.toList().orEmpty()
        j.put("raw_sensor_output_sizes", JSONArray(rawSizes.map { "${it.width}x${it.height}" }))

        ch.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT)?.let {
            j.put("cfa_arrangement", cfaName(it))
        }
        ch.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL)?.let { j.put("white_level", it) }
        ch.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN)?.let { pattern ->
            val values = IntArray(4)
            pattern.copyTo(values, 0)
            j.put("black_level_pattern", JSONArray(values.toList()))
        }

        // Focus distances are in diopters (1/m). Minimum focus distance 0 means fixed focus.
        ch.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE)?.let {
            j.put("minimum_focus_distance_diopters", it.toDouble())
        }
        ch.get(CameraCharacteristics.LENS_INFO_HYPERFOCAL_DISTANCE)?.let {
            j.put("hyperfocal_distance_diopters", it.toDouble())
        }
        ch.get(CameraCharacteristics.LENS_INFO_FOCUS_DISTANCE_CALIBRATION)?.let {
            j.put(
                "focus_distance_calibration",
                when (it) {
                    CameraMetadata.LENS_INFO_FOCUS_DISTANCE_CALIBRATION_UNCALIBRATED -> "uncalibrated"
                    CameraMetadata.LENS_INFO_FOCUS_DISTANCE_CALIBRATION_APPROXIMATE -> "approximate"
                    CameraMetadata.LENS_INFO_FOCUS_DISTANCE_CALIBRATION_CALIBRATED -> "calibrated"
                    else -> "unknown($it)"
                },
            )
        }
        ch.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION)?.let {
            j.put("optical_stabilization_modes", JSONArray(it.toList()))
        }
        ch.get(CameraCharacteristics.NOISE_REDUCTION_AVAILABLE_NOISE_REDUCTION_MODES)?.let {
            j.put("noise_reduction_modes", JSONArray(it.toList()))
        }
        ch.get(CameraCharacteristics.LENS_DISTORTION)?.let {
            j.put("lens_distortion", JSONArray(it.map { v -> v.toDouble() }))
        }
        ch.get(CameraCharacteristics.LENS_INTRINSIC_CALIBRATION)?.let {
            j.put("lens_intrinsic_calibration", JSONArray(it.map { v -> v.toDouble() }))
        }
        ch.get(CameraCharacteristics.CONTROL_ZOOM_RATIO_RANGE)?.let {
            j.put("zoom_ratio_range", JSONArray(listOf(it.lower.toDouble(), it.upper.toDouble())))
        }

        return CameraInfo(
            id = id,
            parentLogicalId = parent,
            openableDirectly = openable,
            facing = facing,
            rawCapable = raw && rawSizes.isNotEmpty(),
            manualSensor = manual,
            focalLengthsMm = focal,
            maxExposureS = maxExposureS,
            isoRange = iso?.let { it.lower to it.upper },
            diagonalFovDeg = diagonalFov,
            json = j,
        )
    }

    private fun hardwareLevel(level: Int?): String = when (level) {
        CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_LEGACY -> "LEGACY"
        CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_LIMITED -> "LIMITED"
        CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_FULL -> "FULL"
        CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_3 -> "LEVEL_3"
        CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_EXTERNAL -> "EXTERNAL"
        null -> "unknown"
        else -> "unknown($level)"
    }

    private fun capabilityName(cap: Int): String = when (cap) {
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_BACKWARD_COMPATIBLE -> "BACKWARD_COMPATIBLE"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR -> "MANUAL_SENSOR"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_POST_PROCESSING -> "MANUAL_POST_PROCESSING"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_RAW -> "RAW"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_PRIVATE_REPROCESSING -> "PRIVATE_REPROCESSING"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_READ_SENSOR_SETTINGS -> "READ_SENSOR_SETTINGS"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_BURST_CAPTURE -> "BURST_CAPTURE"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_YUV_REPROCESSING -> "YUV_REPROCESSING"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT -> "DEPTH_OUTPUT"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_CONSTRAINED_HIGH_SPEED_VIDEO -> "CONSTRAINED_HIGH_SPEED_VIDEO"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MOTION_TRACKING -> "MOTION_TRACKING"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA -> "LOGICAL_MULTI_CAMERA"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MONOCHROME -> "MONOCHROME"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_SECURE_IMAGE_DATA -> "SECURE_IMAGE_DATA"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_SYSTEM_CAMERA -> "SYSTEM_CAMERA"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_OFFLINE_PROCESSING -> "OFFLINE_PROCESSING"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_ULTRA_HIGH_RESOLUTION_SENSOR -> "ULTRA_HIGH_RESOLUTION_SENSOR"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_REMOSAIC_REPROCESSING -> "REMOSAIC_REPROCESSING"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_DYNAMIC_RANGE_TEN_BIT -> "DYNAMIC_RANGE_TEN_BIT"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_STREAM_USE_CASE -> "STREAM_USE_CASE"
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_COLOR_SPACE_PROFILES -> "COLOR_SPACE_PROFILES"
        else -> "UNKNOWN($cap)"
    }

    private fun cfaName(value: Int): String = when (value) {
        CameraMetadata.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_RGGB -> "RGGB"
        CameraMetadata.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_GRBG -> "GRBG"
        CameraMetadata.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_GBRG -> "GBRG"
        CameraMetadata.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_BGGR -> "BGGR"
        CameraMetadata.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_RGB -> "RGB"
        CameraMetadata.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_MONO -> "MONO"
        CameraMetadata.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_NIR -> "NIR"
        else -> "UNKNOWN($value)"
    }
}
