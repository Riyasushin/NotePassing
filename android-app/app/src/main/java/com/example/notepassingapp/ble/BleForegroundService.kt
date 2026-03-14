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
import androidx.core.app.NotificationCompat
import com.example.notepassingapp.MainActivity
import com.example.notepassingapp.R

class BleForegroundService : Service() {

    override fun onCreate() {
        super.onCreate()
        createChannel()
        startForeground(BleConstants.NOTIFICATION_ID, buildNotification())
        BleManager.start(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            BleManager.stop()
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }
        return START_STICKY
    }

    override fun onDestroy() {
        BleManager.stop()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(
                BleConstants.NOTIFICATION_CHANNEL_ID,
                "附近发现",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "BLE 扫描和广播服务"
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
    }

    private fun buildNotification(): Notification {
        val pi = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, BleConstants.NOTIFICATION_CHANNEL_ID)
            .setContentTitle("NotePassing")
            .setContentText("正在发现附近的人…")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(pi)
            .setOngoing(true)
            .build()
    }

    companion object {
        const val ACTION_STOP = "com.example.notepassingapp.STOP_BLE"

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
