package com.example.notepassingapp.data.remote

import com.example.notepassingapp.data.remote.api.*
import com.google.gson.GsonBuilder
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {

    private val gson = GsonBuilder()
        .setDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
        .create()

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    val okHttpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(NetworkConfig.CONNECT_TIMEOUT_SEC, TimeUnit.SECONDS)
            .readTimeout(NetworkConfig.READ_TIMEOUT_SEC, TimeUnit.SECONDS)
            .writeTimeout(NetworkConfig.WRITE_TIMEOUT_SEC, TimeUnit.SECONDS)
            .addInterceptor(DebugLogInterceptor)
            .addInterceptor(loggingInterceptor)
            .build()
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(NetworkConfig.BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
    }

    val deviceApi: DeviceApi by lazy { retrofit.create(DeviceApi::class.java) }
    val tempIdApi: TempIdApi by lazy { retrofit.create(TempIdApi::class.java) }
    val presenceApi: PresenceApi by lazy { retrofit.create(PresenceApi::class.java) }
    val messageApi: MessageApi by lazy { retrofit.create(MessageApi::class.java) }
    val relationApi: RelationApi by lazy { retrofit.create(RelationApi::class.java) }
}
