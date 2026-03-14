package com.example.notepassingapp.ble

import android.bluetooth.BluetoothManager
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.bluetooth.le.BluetoothLeAdvertiser
import android.content.Context
import android.os.ParcelUuid
import android.util.Log

class BleAdvertiser(private val context: Context) {

    private val TAG = "BleAdvertiser"
    private var advertiser: BluetoothLeAdvertiser? = null
    @Volatile
    private var advertising = false

    private val callback = object : AdvertiseCallback() {
        override fun onStartSuccess(settingsInEffect: AdvertiseSettings?) {
            Log.d(TAG, "Advertising started")
            advertising = true
        }

        override fun onStartFailure(errorCode: Int) {
            Log.e(TAG, "Advertising failed: $errorCode")
            advertising = false
        }
    }

    @Suppress("MissingPermission")
    fun start(tempIdHex: String) {
        val bm = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        val adapter = bm?.adapter
        if (adapter == null || !adapter.isEnabled) {
            Log.w(TAG, "Bluetooth disabled")
            return
        }

        advertiser = adapter.bluetoothLeAdvertiser ?: run {
            Log.w(TAG, "BLE advertiser not supported on this device")
            return
        }

        stop()

        val settings = AdvertiseSettings.Builder()
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
            .setConnectable(false)
            .setTimeout(0)
            .build()

        val serviceUuid = ParcelUuid(BleConstants.SERVICE_UUID)
        val data = AdvertiseData.Builder()
            .addServiceData(serviceUuid, hexToBytes(tempIdHex))
            .setIncludeDeviceName(false)
            .setIncludeTxPowerLevel(false)
            .build()

        try {
            advertiser?.startAdvertising(settings, data, callback)
            Log.d(TAG, "Advertising tempId=${tempIdHex.take(8)}…")
        } catch (e: SecurityException) {
            Log.e(TAG, "Permission denied", e)
        }
    }

    @Suppress("MissingPermission")
    fun stop() {
        if (advertising) {
            try { advertiser?.stopAdvertising(callback) } catch (_: SecurityException) {}
            advertising = false
        }
    }

    fun isAdvertising() = advertising

    private fun hexToBytes(hex: String): ByteArray {
        val h = hex.replace(" ", "")
        return ByteArray(h.length / 2) { i ->
            h.substring(i * 2, i * 2 + 2).toInt(16).toByte()
        }
    }
}
