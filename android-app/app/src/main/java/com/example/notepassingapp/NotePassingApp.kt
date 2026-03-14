package com.example.notepassingapp

import android.app.Application
import android.util.Log
import com.example.notepassingapp.data.local.AppDatabase
import com.example.notepassingapp.data.remote.ws.WebSocketManager
import com.example.notepassingapp.data.repository.DeviceRepository
import com.example.notepassingapp.data.repository.RelationRepository
import com.example.notepassingapp.util.DeviceManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class NotePassingApp : Application() {

    lateinit var database: AppDatabase
        private set

    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        instance = this
        DeviceManager.init(this)
        database = AppDatabase.getInstance(this)

        if (DeviceManager.isInitialized()) {
            bootstrapNetwork()
        }
    }

    /**
     * 引导完成后的网络初始化：device/init → WS 连接 → 同步好友。
     * 在 Onboarding 完成后也会调用此方法。
     */
    fun bootstrapNetwork() {
        appScope.launch {
            val result = DeviceRepository.initDevice()
            Log.d("NotePassingApp", "Device init result: $result")

            WebSocketManager.connect()
            RelationRepository.syncFriends()
        }
    }

    companion object {
        lateinit var instance: NotePassingApp
            private set
    }
}
