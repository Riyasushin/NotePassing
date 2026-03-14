package com.example.notepassingapp.data.remote.api

import com.example.notepassingapp.data.remote.dto.*
import retrofit2.http.*

/**
 * 契约 §5 Relation Service
 */
interface RelationApi {

    @GET("friends")
    suspend fun getFriendsList(
        @Query("device_id") deviceId: String
    ): ApiResponse<FriendsListData>

    @GET("friends/requests")
    suspend fun getPendingRequests(
        @Query("device_id") deviceId: String
    ): ApiResponse<PendingFriendRequestsData>

    @POST("friends/request")
    suspend fun sendFriendRequest(
        @Body request: FriendRequestBody
    ): ApiResponse<FriendRequestData>

    @PUT("friends/{request_id}")
    suspend fun respondFriendRequest(
        @Path("request_id") requestId: String,
        @Body request: FriendRespondBody
    ): ApiResponse<FriendAcceptData>

    @DELETE("friends/{friend_device_id}")
    suspend fun deleteFriend(
        @Path("friend_device_id") friendDeviceId: String,
        @Query("device_id") deviceId: String
    ): ApiResponse<Unit?>

    @POST("block")
    suspend fun blockUser(
        @Body request: BlockRequest
    ): ApiResponse<Unit?>

    @DELETE("block/{target_device_id}")
    suspend fun unblockUser(
        @Path("target_device_id") targetDeviceId: String,
        @Query("device_id") deviceId: String
    ): ApiResponse<Unit?>
}
