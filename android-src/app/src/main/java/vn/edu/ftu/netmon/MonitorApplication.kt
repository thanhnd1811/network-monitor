package vn.edu.ftu.netmon

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class MonitorApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        scheduleBackgroundCheck()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = getSystemService(NotificationManager::class.java)
        val alertChannel = NotificationChannel(
            CHANNEL_ALERT,
            "Cảnh báo đường mạng",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Thông báo khi có đường mạng bị mất kết nối"
            enableVibration(true)
            enableLights(true)
        }
        val recoverChannel = NotificationChannel(
            CHANNEL_RECOVER,
            "Đường mạng hoạt động lại",
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "Thông báo khi đường mạng đã được khôi phục"
        }
        nm.createNotificationChannels(listOf(alertChannel, recoverChannel))
    }

    private fun scheduleBackgroundCheck() {
        // Periodic worker — Android minimum interval is 15 minutes
        val request = PeriodicWorkRequestBuilder<MonitorWorker>(15, TimeUnit.MINUTES)
            .setConstraints(MonitorWorker.CONSTRAINTS)
            .build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            MonitorWorker.UNIQUE_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            request
        )
    }

    companion object {
        const val CHANNEL_ALERT   = "ftu_netmon_alert"
        const val CHANNEL_RECOVER = "ftu_netmon_recover"
    }
}
