package com.example.notepassingapp.ble

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.example.notepassingapp.MainActivity
import com.example.notepassingapp.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class BleForegroundService : Service() {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onCreate() {
        super.onCreate()
        createChannel()
        acquireWakeLock()
        startForeground(BleConstants.NOTIFICATION_ID, buildNotification(BleManager.state.value))
        observeBleState()
        BleManager.start(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopRadarService()
            return START_NOT_STICKY
        }
        return START_STICKY
    }

    override fun onDestroy() {
        serviceScope.cancel()
        releaseWakeLock()
        BleManager.stop()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(
                BleConstants.NOTIFICATION_CHANNEL_ID,
                "雷达持续运行",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "BLE 扫描和广播服务，保持附近雷达在后台持续工作"
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
    }

    private fun buildNotification(state: BleManager.State): Notification {
        val openAppIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val stopIntent = PendingIntent.getService(
            this,
            1,
            Intent(this, BleForegroundService::class.java).apply {
                action = ACTION_STOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val message = buildNotificationText(state)

        return NotificationCompat.Builder(this, BleConstants.NOTIFICATION_CHANNEL_ID)
            .setContentTitle("雷达持续运行中")
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(openAppIntent)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .addAction(R.drawable.ic_launcher_foreground, "停止雷达", stopIntent)
            .build()
    }

    private fun buildNotificationText(state: BleManager.State): String {
        return when {
            state.isScanning && state.foundCount > 0 -> "正在扫描并广播，已发现 ${state.foundCount} 位附近用户。息屏后也会继续保持雷达运行。"
            state.isScanning -> "正在扫描并广播附近的人。息屏后也会继续保持雷达运行。"
            state.foundCount > 0 -> "等待下一轮扫描，当前已发现 ${state.foundCount} 位附近用户。"
            else -> "后台会持续扫描和广播附近的人。"
        }
    }

    private fun observeBleState() {
        serviceScope.launch {
            BleManager.state.collectLatest { state ->
                NotificationManagerCompat.from(this@BleForegroundService)
                    .notify(BleConstants.NOTIFICATION_ID, buildNotification(state))
            }
        }
    }

    private fun acquireWakeLock() {
        val powerManager = getSystemService(Context.POWER_SERVICE) as? PowerManager ?: return
        if (wakeLock?.isHeld == true) return

        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            WAKE_LOCK_TAG
        ).apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun releaseWakeLock() {
        wakeLock?.let { lock ->
            if (lock.isHeld) {
                lock.release()
            }
        }
        wakeLock = null
    }

    private fun stopRadarService() {
        BleManager.stop()
        releaseWakeLock()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    companion object {
        const val ACTION_STOP = "com.example.notepassingapp.STOP_BLE"
        private const val WAKE_LOCK_TAG = "NotePassing:BleForegroundService"

        fun start(context: Context) {
            val intent = Intent(context, BleForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.startService(
                Intent(context, BleForegroundService::class.java).apply {
                    action = ACTION_STOP
                }
            )
        }
    }
}
