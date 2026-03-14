package com.example.notepassingapp.ble

import java.util.UUID

object BleConstants {
    val SERVICE_UUID: UUID = UUID.fromString("0000AA01-0000-1000-8000-00805F9B34FB")

    const val SCAN_DURATION_MS = 4_000L
    const val SCAN_INTERVAL_MS = 8_000L
    const val RESOLVE_BATCH_MS = 10_000L

    const val GRACE_PERIOD_MS = 60_000L
    const val STALE_CLEANUP_MS = 120_000L

    const val NOTIFICATION_CHANNEL_ID = "ble_service_channel"
    const val NOTIFICATION_ID = 1001
}
