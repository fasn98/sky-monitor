package io.github.fasn98.skymonitor.diag

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Typeface
import android.hardware.camera2.CameraManager
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.view.WindowInsets
import android.view.WindowManager
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

class MainActivity : Activity() {

    private lateinit var manager: CameraManager
    private lateinit var output: TextView
    private lateinit var scroll: ScrollView
    private lateinit var cameraSpinner: Spinner
    private lateinit var exposureInput: EditText
    private lateinit var isoInput: EditText
    private lateinit var captureButton: Button

    private var cameras: List<CameraInfo> = emptyList()
    private var eligible: List<CameraInfo> = emptyList()
    private var reportJson: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        manager = getSystemService(CameraManager::class.java)
        setContentView(buildUi())
        if (hasCameraPermission()) {
            generateReport()
        } else {
            requestPermissions(arrayOf(Manifest.permission.CAMERA), REQUEST_CAMERA)
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CAMERA) {
            if (!hasCameraPermission()) {
                append("Permissão de câmera negada: alguns dados não aparecem e a captura de teste fica desativada.")
            }
            generateReport()
        }
    }

    private fun hasCameraPermission() =
        checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED

    // ------------------------------------------------------------------ report

    private fun generateReport() {
        output.text = ""
        try {
            cameras = CameraReport.collect(manager)
        } catch (e: Exception) {
            append("ERRO ao ler as câmeras: ${e.javaClass.simpleName}: ${e.message}")
            return
        }
        val json = CameraReport.toJson(cameras, hasCameraPermission()).toString(2)
        reportJson = json

        append("Sky Monitor — diagnóstico de câmeras")
        append("${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL} · Android ${android.os.Build.VERSION.RELEASE}")
        append("${cameras.size} câmeras encontradas.\n")
        cameras.forEach { append(it.summary()) }

        try {
            val stamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"))
            val name = "skymonitor_diag_report_$stamp.json"
            Downloads.save(this, name, "application/json") { it.write(json.toByteArray()) }
            append("Relatório completo salvo em ${Downloads.FOLDER_LABEL}/$name")
        } catch (e: Exception) {
            append("Não foi possível salvar o JSON: ${e.message}")
        }

        eligible = cameras.filter { it.captureEligible }
        cameraSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            eligible.map { it.label() },
        )
        captureButton.isEnabled = eligible.isNotEmpty() && hasCameraPermission()
        if (eligible.isEmpty()) {
            append("\nNenhuma câmera permite RAW + exposição manual para apps de terceiros.")
        }
    }

    private fun shareReport() {
        val json = reportJson ?: return
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, "Sky Monitor — diagnóstico de câmeras")
            putExtra(Intent.EXTRA_TEXT, json)
        }
        startActivity(Intent.createChooser(intent, "Compartilhar relatório"))
    }

    // ------------------------------------------------------------------ capture

    private fun startCapture() {
        val camera = eligible.getOrNull(cameraSpinner.selectedItemPosition) ?: return
        val exposure = exposureInput.text.toString().replace(',', '.').toDoubleOrNull()
        val iso = isoInput.text.toString().toIntOrNull()
        if (exposure == null || exposure <= 0 || iso == null || iso <= 0) {
            append("Informe exposição (s) e ISO válidos.")
            return
        }
        captureButton.isEnabled = false
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        append("\n— Captura de teste: ${camera.label()}")
        TestCapture(
            context = applicationContext,
            manager = manager,
            log = { msg -> runOnUiThread { append(msg) } },
            onFinished = {
                runOnUiThread {
                    captureButton.isEnabled = true
                    window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                }
            },
        ).start(camera.id, exposure, iso)
    }

    // ----------------------------------------------------------------------- UI

    private fun append(line: String) {
        output.append(line + "\n")
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
    }

    private fun buildUi(): View {
        val pad = (16 * resources.displayMetrics.density).toInt()

        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
        }

        column.addView(TextView(this).apply {
            text = "Sky Monitor — diagnóstico"
            textSize = 20f
            setTypeface(typeface, Typeface.BOLD)
        })

        val reportRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        reportRow.addView(Button(this).apply {
            text = "Gerar relatório"
            setOnClickListener { generateReport() }
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        reportRow.addView(Button(this).apply {
            text = "Compartilhar"
            setOnClickListener { shareReport() }
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        column.addView(reportRow)

        column.addView(TextView(this).apply {
            text = "\nCaptura de teste (RAW, manual)"
            setTypeface(typeface, Typeface.BOLD)
        })
        cameraSpinner = Spinner(this)
        column.addView(cameraSpinner)

        val paramsRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        exposureInput = EditText(this).apply {
            hint = "Exposição (s)"
            setText("10")
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL
        }
        isoInput = EditText(this).apply {
            hint = "ISO"
            setText("800")
            inputType = InputType.TYPE_CLASS_NUMBER
        }
        paramsRow.addView(exposureInput, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        paramsRow.addView(isoInput, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        column.addView(paramsRow)

        captureButton = Button(this).apply {
            text = "Capturar DNG de teste"
            isEnabled = false
            setOnClickListener { startCapture() }
        }
        column.addView(captureButton)

        output = TextView(this).apply {
            typeface = Typeface.MONOSPACE
            textSize = 12f
            setTextIsSelectable(true)
        }
        column.addView(output)

        scroll = ScrollView(this).apply { addView(column) }
        // targetSdk 35 draws edge-to-edge: keep content clear of status/navigation bars.
        scroll.setOnApplyWindowInsetsListener { v, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.ime())
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        return scroll
    }

    private companion object {
        const val REQUEST_CAMERA = 1
    }
}
