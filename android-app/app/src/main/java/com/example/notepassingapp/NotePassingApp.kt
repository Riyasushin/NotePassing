package com.example.notepassingapp

import android.app.Application
import com.example.notepassingapp.data.local.AppDatabase
import com.example.notepassingapp.util.DeviceManager

/**
 * 自定义 Application 类，App 启动时最先执行。
 * 在这里初始化全局单例，避免在各处重复创建。
 */
class NotePassingApp : Application() {

    lateinit var database: AppDatabase
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        DeviceManager.init(this)
        database = AppDatabase.getInstance(this)
    }

    companion object {
        lateinit var instance: NotePassingApp
            private set
    }
}
