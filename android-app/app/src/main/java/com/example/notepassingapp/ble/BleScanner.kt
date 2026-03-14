package com.example.notepassingapp.ble

import android.bluetooth.BluetoothManager
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.ParcelUuid
import android.util.Log
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

data class BleFoundDevice(
    val tempId: String,
    val rssi: Int,
    val timestamp: Long = System.currentTimeMillis()
)

class BleScanner(private val context: Context) {

    private val TAG = "BleScanner"
    @Volatile
    private var scanning = false

    private val _found = MutableSharedFlow<BleFoundDevice>(extraBufferCapacity = 64)
    val found: SharedFlow<BleFoundDevice> = _found.asSharedFlow()

    private val callback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            parse(result)
        }

        override fun onBatchScanResults(results: MutableList<ScanResult>) {
            results.forEach { parse(it) }
        }

        override fun onScanFailed(errorCode: Int) {
            Log.e(TAG, "Scan failed: $errorCode")
            scanning = false
        }
    }

    private fun parse(result: ScanResult) {
        val bytes = result.scanRecord
            ?.getServiceData(ParcelUuid(BleConstants.SERVICE_UUID)) ?: return
        val tempId = bytes.joinToString("") { "%02x".format(it) }
        if (tempId.isNotEmpty()) {
            _found.tryEmit(BleFoundDevice(tempId, result.rssi))
        }
    }

    @Suppress("MissingPermission")
    fun start() {
        val bm = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        val adapter = bm?.adapter
        if (adapter == null || !adapter.isEnabled) {
            Log.w(TAG, "Bluetooth disabled")
            return
        }

        val bleScanner = adapter.bluetoothLeScanner ?: run {
            Log.w(TAG, "BLE scanner not available")
            return
        }

        val filter = ScanFilter.Builder()
            .setServiceUuid(ParcelUuid(BleConstants.SERVICE_UUID))
            .build()
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .setReportDelay(0)
            .build()

        try {
            bleScanner.startScan(listOf(filter), settings, callback)
            scanning = true
        } catch (e: SecurityException) {
            Log.e(TAG, "Permission denied", e)
        }
    }

    @Suppress("MissingPermission")
    fun stop() {
        if (!scanning) return
        try {
            val bm = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
            bm?.adapter?.bluetoothLeScanner?.stopScan(callback)
        } catch (_: SecurityException) {}
        scanning = false
    }

    fun isScanning() = scanning
}
