package io.github.fasn98.skymonitor.diag

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import java.io.IOException
import java.io.OutputStream

/** Saves files to the public Download/SkyMonitor folder via MediaStore (no permission needed). */
object Downloads {
    private val folder = Environment.DIRECTORY_DOWNLOADS + "/SkyMonitor"

    fun save(context: Context, displayName: String, mimeType: String, write: (OutputStream) -> Unit): Uri {
        val resolver = context.contentResolver
        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, displayName)
            put(MediaStore.Downloads.MIME_TYPE, mimeType)
            put(MediaStore.Downloads.RELATIVE_PATH, folder)
            put(MediaStore.Downloads.IS_PENDING, 1)
        }
        val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: throw IOException("MediaStore recusou criar $displayName")
        try {
            val stream = resolver.openOutputStream(uri) ?: throw IOException("Sem stream para $uri")
            stream.use(write)
            values.clear()
            values.put(MediaStore.Downloads.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
            return uri
        } catch (e: Exception) {
            resolver.delete(uri, null, null)
            throw e
        }
    }

    const val FOLDER_LABEL = "Download/SkyMonitor"
}
