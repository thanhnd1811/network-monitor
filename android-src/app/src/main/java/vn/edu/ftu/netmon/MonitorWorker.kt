package vn.edu.ftu.netmon

import android.content.Context
import android.content.SharedPreferences
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.NetworkType
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Background worker. Runs at most every 15 min (Android system limit on free tier).
 * Fetches status.json from GitHub Pages, compares each line with the previously stored
 * up/down state, and emits a notification when ANY line transitions.
 */
class MonitorWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val prefs = applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        try {
            val json = fetchStatusJson() ?: return@withContext Result.retry()
            val lines = parseLines(json)
            if (lines.isEmpty()) return@withContext Result.success()

            evaluateAndNotify(lines, prefs)
            Result.success()
        } catch (t: Throwable) {
            Result.retry()
        }
    }

    private fun fetchStatusJson(): JSONObject? {
        val baseUrl = BuildConfig.DASHBOARD_URL.trimEnd('/')
        val url = URL("$baseUrl/data/status.json?t=${System.currentTimeMillis()}")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 10_000
            readTimeout = 15_000
            requestMethod = "GET"
            setRequestProperty("Accept", "application/json")
        }
        return try {
            if (conn.responseCode != 200) null
            else JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
        } finally {
            conn.disconnect()
        }
    }

    private data class LineState(
        val id: String, val name: String, val ip: String, val isp: String, val up: Boolean
    )

    private fun parseLines(json: JSONObject): List<LineState> {
        val out = mutableListOf<LineState>()
        val locs = json.optJSONArray("locations") ?: return out
        for (i in 0 until locs.length()) {
            val loc = locs.getJSONObject(i)
            val ls = loc.optJSONArray("lines") ?: continue
            for (j in 0 until ls.length()) {
                val l = ls.getJSONObject(j)
                out.add(
                    LineState(
                        id   = l.optString("id"),
                        name = l.optString("name"),
                        ip   = l.optString("ip"),
                        isp  = l.optString("isp"),
                        up   = l.optBoolean("up", true)
                    )
                )
            }
        }
        return out
    }

    private fun evaluateAndNotify(lines: List<LineState>, prefs: SharedPreferences) {
        val nm = NotificationManagerCompat.from(applicationContext)
        val firstRun = !prefs.contains(KEY_INITIALIZED)
        val edits = prefs.edit()
        val newlyDown = mutableListOf<LineState>()
        val newlyUp = mutableListOf<LineState>()

        for (line in lines) {
            val key = "state.${line.id}"
            val prevUp = if (prefs.contains(key)) prefs.getBoolean(key, true) else line.up
            edits.putBoolean(key, line.up)
            if (firstRun) continue
            if (prevUp && !line.up) newlyDown.add(line)
            if (!prevUp && line.up) newlyUp.add(line)
        }
        edits.putBoolean(KEY_INITIALIZED, true).apply()

        if (firstRun) return  // Don't notify on first sync

        if (newlyDown.isNotEmpty()) notifyDown(nm, newlyDown)
        if (newlyUp.isNotEmpty()) notifyUp(nm, newlyUp)
    }

    private fun notifyDown(nm: NotificationManagerCompat, lines: List<LineState>) {
        val title = if (lines.size == 1)
            "MẤT KẾT NỐI: ${lines[0].name}"
        else
            "MẤT KẾT NỐI: ${lines.size} đường mạng"
        val body = lines.joinToString("\n") { "• ${it.isp} ${it.name} (${it.ip})" }

        val n = NotificationCompat.Builder(applicationContext, MonitorApplication.CHANNEL_ALERT)
            .setContentTitle(title)
            .setContentText(body.lineSequence().first())
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setSmallIcon(R.drawable.ic_alert)
            .setColor(0xFFEF4444.toInt())
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setContentIntent(openAppIntent(applicationContext))
            .build()
        try { nm.notify(NOTIF_ID_DOWN, n) } catch (_: SecurityException) {}
    }

    private fun notifyUp(nm: NotificationManagerCompat, lines: List<LineState>) {
        val title = if (lines.size == 1)
            "Đã hoạt động trở lại: ${lines[0].name}"
        else
            "${lines.size} đường mạng đã hoạt động trở lại"
        val body = lines.joinToString("\n") { "• ${it.isp} ${it.name} (${it.ip})" }

        val n = NotificationCompat.Builder(applicationContext, MonitorApplication.CHANNEL_RECOVER)
            .setContentTitle(title)
            .setContentText(body.lineSequence().first())
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setSmallIcon(R.drawable.ic_recover)
            .setColor(0xFF22C55E.toInt())
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .setContentIntent(openAppIntent(applicationContext))
            .build()
        try { nm.notify(NOTIF_ID_UP, n) } catch (_: SecurityException) {}
    }

    private fun openAppIntent(ctx: Context) =
        android.app.PendingIntent.getActivity(
            ctx, 0,
            android.content.Intent(ctx, MainActivity::class.java),
            android.app.PendingIntent.FLAG_IMMUTABLE or android.app.PendingIntent.FLAG_UPDATE_CURRENT
        )

    companion object {
        const val UNIQUE_NAME = "ftu-netmon-periodic"
        const val PREFS = "ftu-netmon-prefs"
        const val KEY_INITIALIZED = "initialized"
        const val NOTIF_ID_DOWN = 1001
        const val NOTIF_ID_UP   = 1002

        val CONSTRAINTS: Constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
    }
}
