package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.BlockEntity
import com.example.notepassingapp.data.local.entity.FriendEntity
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.dto.*
import com.example.notepassingapp.util.DeviceManager
import com.google.gson.Gson

object RelationRepository {

    private const val TAG = "RelationRepository"
    private val gson = Gson()
    private val friendDao = NotePassingApp.instance.database.friendDao()
    private val blockDao = NotePassingApp.instance.database.blockDao()

    /**
     * 从服务器同步好友列表到本地 Room。
     */
    suspend fun syncFriends(): Boolean {
        return try {
            val response = ApiClient.relationApi.getFriendsList(DeviceManager.getDeviceId())
            if (response.isSuccess && response.data != null) {
                response.data.friends.forEach { dto ->
                    val existing = friendDao.getByDeviceId(dto.deviceId)
                    val entity = FriendEntity(
                        deviceId = dto.deviceId,
                        nickname = dto.nickname,
                        avatar = dto.avatar,
                        tags = gson.toJson(dto.tags),
                        profile = dto.profile,
                        meetCount = existing?.meetCount ?: 1,
                        isNearby = existing?.isNearby ?: false,
                        lastChatAt = existing?.lastChatAt
                    )
                    friendDao.insertOrReplace(entity)
                }
                Log.d(TAG, "Synced ${response.data.friends.size} friends")
                true
            } else {
                Log.w(TAG, "Sync friends failed: ${response.code}")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Sync friends error", e)
            false
        }
    }

    suspend fun sendFriendRequest(receiverId: String, message: String? = null): Result<FriendRequestData> {
        return try {
            val request = FriendRequestBody(
                senderId = DeviceManager.getDeviceId(),
                receiverId = receiverId,
                message = message
            )
            val response = ApiClient.relationApi.sendFriendRequest(request)
            if (response.isSuccess && response.data != null) {
                Result.success(response.data)
            } else {
                Result.failure(Exception("${response.code}: ${response.message}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun respondFriendRequest(requestId: String, accept: Boolean): Boolean {
        return try {
            val body = FriendRespondBody(
                deviceId = DeviceManager.getDeviceId(),
                action = if (accept) "accept" else "reject"
            )
            val response = ApiClient.relationApi.respondFriendRequest(requestId, body)
            if (response.isSuccess && accept && response.data?.friend != null) {
                val friend = response.data.friend!!
                friendDao.insertOrReplace(
                    FriendEntity(
                        deviceId = friend.deviceId,
                        nickname = friend.nickname,
                        avatar = friend.avatar
                    )
                )
            }
            response.isSuccess
        } catch (e: Exception) {
            Log.e(TAG, "Respond friend request error", e)
            false
        }
    }

    suspend fun blockUser(targetId: String): Boolean {
        return try {
            val request = BlockRequest(
                deviceId = DeviceManager.getDeviceId(),
                targetId = targetId
            )
            val response = ApiClient.relationApi.blockUser(request)
            if (response.isSuccess) {
                blockDao.insert(BlockEntity(deviceId = targetId))
                friendDao.delete(targetId)
            }
            response.isSuccess
        } catch (e: Exception) {
            Log.e(TAG, "Block user error", e)
            false
        }
    }

    suspend fun unblockUser(targetId: String): Boolean {
        return try {
            val response = ApiClient.relationApi.unblockUser(
                targetId, DeviceManager.getDeviceId()
            )
            if (response.isSuccess) {
                blockDao.delete(targetId)
            }
            response.isSuccess
        } catch (e: Exception) {
            Log.e(TAG, "Unblock user error", e)
            false
        }
    }
}
