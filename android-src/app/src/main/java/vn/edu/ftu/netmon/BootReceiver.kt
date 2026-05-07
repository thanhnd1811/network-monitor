package vn.edu.ftu.netmon

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

/**
 * Re-schedules the periodic worker after device reboot or app update.
 * Without this, the worker stops running until the user manually opens the app again.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        val action = intent.action ?: return
        if (action == Intent.ACTION_BOOT_COMPLETED ||
            action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            val req = PeriodicWorkRequestBuilder<MonitorWorker>(15, TimeUnit.MINUTES)
                .setConstraints(MonitorWorker.CONSTRAINTS)
                .build()
            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
                MonitorWorker.UNIQUE_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                req
            )
        }
    }
}
