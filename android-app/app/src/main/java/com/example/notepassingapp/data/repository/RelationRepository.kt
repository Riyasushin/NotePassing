package com.example.notepassingapp.data.repository

import android.util.Log
import com.example.notepassingapp.NotePassingApp
import com.example.notepassingapp.data.local.entity.BlockEntity
import com.example.notepassingapp.data.local.entity.FriendEntity
import com.example.notepassingapp.data.local.entity.FriendRequestDirection
import com.example.notepassingapp.data.local.entity.FriendRequestEntity
import com.example.notepassingapp.data.remote.ApiClient
import com.example.notepassingapp.data.remote.dto.*
import com.example.notepassingapp.data.remote.ws.WsFriendDeletedPayload
import com.example.notepassingapp.data.remote.ws.WsFriendRequestPayload
import com.example.notepassingapp.data.remote.ws.WsFriendResponsePayload
import com.example.notepassingapp.util.DeviceManager
import com.google.gson.Gson
import java.time.Instant

object RelationRepository {

    private const val TAG = "RelationRepository"
    private val gson = Gson()
    private val friendDao = NotePassingApp.instance.database.friendDao()
    private val friendRequestDao = NotePassingApp.instance.database.friendRequestDao()
    private val blockDao = NotePassingApp.instance.database.blockDao()
    private val chatHistoryDao = NotePassingApp.instance.database.chatHistoryDao()

    /**
     * 从服务器同步好友列表到本地 Room。
     */
    suspend fun syncFriends(): Boolean {
        return try {
            val response = ApiClient.relationApi.getFriendsList(DeviceManager.getDeviceId())
            if (response.isSuccess && response.data != null) {
                val localIds = friendDao.getAllDeviceIds().toSet()
                val serverIds = response.data.friends.map { it.deviceId }.toSet()

                response.data.friends.forEach { dto ->
                    val existing = friendDao.getByDeviceId(dto.deviceId)
                    val entity = FriendEntity(
                        deviceId = dto.deviceId,
                        nickname = dto.nickname,
                        avatar = dto.avatar,
                        tags = gson.toJson(dto.tags),
                        profile = dto.profile,
                        isAnonymous = dto.isAnonymous,
                        sessionId = existing?.sessionId,
                        meetCount = existing?.meetCount ?: 1,
                        isNearby = existing?.isNearby ?: false,
                        lastChatAt = existing?.lastChatAt,
                        createdAt = existing?.createdAt ?: System.currentTimeMillis()
                    )
                    friendDao.insertOrReplace(entity)
                }

                val removedIds = localIds - serverIds
                if (serverIds.isEmpty()) {
                    friendDao.deleteAll()
                } else {
                    friendDao.deleteNotIn(serverIds.toList())
                }
                removedIds.forEach { deviceId ->
                    friendRequestDao.deleteByPeerDeviceId(deviceId)
                    markChatHistoryAsStranger(deviceId, setSessionExpired = true)
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

    suspend fun syncIncomingFriendRequests(): Boolean {
        return try {
            val response = ApiClient.relationApi.getPendingRequests(DeviceManager.getDeviceId())
            if (!response.isSuccess || response.data == null) {
                Log.w(TAG, "Sync pending requests failed: ${response.code}")
                return false
            }

            friendRequestDao.deleteByDirection(FriendRequestDirection.INCOMING)
            val entities = response.data.requests.map { dto ->
                FriendRequestEntity(
                    requestId = dto.requestId,
                    peerDeviceId = dto.senderId,
                    peerNickname = dto.nickname,
                    peerAvatar = dto.avatar,
                    message = dto.message,
                    direction = FriendRequestDirection.INCOMING,
                    createdAt = parseIsoTime(dto.createdAt)
                )
            }
            friendRequestDao.insertOrReplaceAll(entities)
            Log.d(TAG, "Synced ${entities.size} incoming friend requests")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Sync pending requests error", e)
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
                val history = chatHistoryDao.getByDeviceId(receiverId)
                friendRequestDao.insertOrReplace(
                    FriendRequestEntity(
                        requestId = response.data.requestId,
                        peerDeviceId = receiverId,
                        peerNickname = history?.nickname ?: receiverId.take(8),
                        peerAvatar = history?.avatar,
                        message = message,
                        direction = FriendRequestDirection.OUTGOING
                    )
                )
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
            val pendingRequest = friendRequestDao.getByRequestId(requestId)
            val body = FriendRespondBody(
                deviceId = DeviceManager.getDeviceId(),
                action = if (accept) "accept" else "reject"
            )
            val response = ApiClient.relationApi.respondFriendRequest(requestId, body)
            if (response.isSuccess && accept && response.data?.friend != null) {
                val friend = response.data.friend!!
                upsertFriend(
                    deviceId = friend.deviceId,
                    nickname = friend.nickname,
                    avatar = friend.avatar,
                    sessionId = response.data.sessionId
                )
                syncFriends()
            }
            if (response.isSuccess) {
                friendRequestDao.deleteByRequestId(requestId)
                pendingRequest?.let { request ->
                    if (accept) {
                        markChatHistoryAsFriend(request.peerDeviceId, response.data?.sessionId)
                    }
                }
            }
            response.isSuccess
        } catch (e: Exception) {
            Log.e(TAG, "Respond friend request error", e)
            false
        }
    }

    suspend fun deleteFriend(friendDeviceId: String): Boolean {
        return try {
            val response = ApiClient.relationApi.deleteFriend(
                friendDeviceId,
                DeviceManager.getDeviceId()
            )
            if (response.isSuccess) {
                friendDao.delete(friendDeviceId)
                friendRequestDao.deleteByPeerDeviceId(friendDeviceId)
                markChatHistoryAsStranger(friendDeviceId, setSessionExpired = true)
            }
            response.isSuccess
        } catch (e: Exception) {
            Log.e(TAG, "Delete friend error", e)
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
                friendRequestDao.deleteByPeerDeviceId(targetId)
                markChatHistoryAsStranger(targetId)
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

    suspend fun saveIncomingFriendRequest(payload: WsFriendRequestPayload) {
        friendRequestDao.insertOrReplace(
            FriendRequestEntity(
                requestId = payload.requestId,
                peerDeviceId = payload.sender.deviceId,
                peerNickname = payload.sender.nickname,
                peerAvatar = payload.sender.avatar,
                message = payload.message,
                direction = FriendRequestDirection.INCOMING
            )
        )
    }

    suspend fun handleFriendResponse(payload: WsFriendResponsePayload) {
        friendRequestDao.deleteByRequestId(payload.requestId)

        if (payload.status != "accepted" || payload.friend == null) {
            return
        }

        upsertFriend(
            deviceId = payload.friend.deviceId,
            nickname = payload.friend.nickname,
            avatar = null,
            sessionId = payload.sessionId
        )
        markChatHistoryAsFriend(payload.friend.deviceId, payload.sessionId)
        syncFriends()
    }

    suspend fun handleFriendDeleted(payload: WsFriendDeletedPayload) {
        friendDao.delete(payload.peerDeviceId)
        friendRequestDao.deleteByPeerDeviceId(payload.peerDeviceId)
        markChatHistoryAsStranger(payload.peerDeviceId, setSessionExpired = true)
    }

    private suspend fun upsertFriend(
        deviceId: String,
        nickname: String,
        avatar: String?,
        sessionId: String?
    ) {
        val existing = friendDao.getByDeviceId(deviceId)
        val history = chatHistoryDao.getByDeviceId(deviceId)

        friendDao.insertOrReplace(
            FriendEntity(
                deviceId = deviceId,
                nickname = nickname.ifBlank { existing?.nickname ?: history?.nickname ?: "新好友" },
                avatar = avatar ?: existing?.avatar ?: history?.avatar,
                tags = existing?.tags ?: "[]",
                profile = existing?.profile ?: history?.profile.orEmpty(),
                isAnonymous = existing?.isAnonymous ?: history?.isAnonymous ?: false,
                sessionId = sessionId ?: existing?.sessionId,
                meetCount = existing?.meetCount ?: 0,
                isNearby = existing?.isNearby ?: false,
                lastChatAt = existing?.lastChatAt,
                createdAt = existing?.createdAt ?: System.currentTimeMillis()
            )
        )
    }

    private suspend fun markChatHistoryAsFriend(deviceId: String, sessionId: String?) {
        val history = chatHistoryDao.getByDeviceId(deviceId) ?: return
        chatHistoryDao.insertOrReplace(
            history.copy(
                isFriend = true,
                sessionId = sessionId ?: history.sessionId,
                isSessionExpired = false
            )
        )
    }

    private suspend fun markChatHistoryAsStranger(
        deviceId: String,
        setSessionExpired: Boolean = false,
    ) {
        val history = chatHistoryDao.getByDeviceId(deviceId) ?: return
        chatHistoryDao.insertOrReplace(
            history.copy(
                isFriend = false,
                isSessionExpired = setSessionExpired
            )
        )
    }

    private fun parseIsoTime(value: String): Long {
        return try {
            Instant.parse(value).toEpochMilli()
        } catch (_: Exception) {
            System.currentTimeMillis()
        }
    }
}
