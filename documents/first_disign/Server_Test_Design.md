# NotePassing Server 测试设计文档

> 本文档详细描述 Server 端所有测试用例设计，包括单元测试、集成测试、WebSocket 测试等。

---

## 目录

1. [测试策略](#1-测试策略)
2. [单元测试](#2-单元测试)
3. [集成测试](#3-集成测试)
4. [WebSocket 测试](#4-websocket-测试)
5. [并发测试](#5-并发测试)
6. [性能测试](#6-性能测试)
7. [测试数据](#7-测试数据)
8. [测试环境](#8-测试环境)

---

## 1. 测试策略

### 1.1 测试金字塔

```
       /\
      /  \      E2E 测试 (少量)
     /----\     
    /      \    集成测试 (中等)
   /--------\
  /          \  单元测试 (大量)
 /------------\
```

### 1.2 测试覆盖目标

| 层级 | 覆盖率目标 | 说明 |
|------|-----------|------|
| 单元测试 | ≥ 80% | Service 层核心逻辑 |
| 集成测试 | 100% | 所有 API 端点 |
| WebSocket | 100% | 所有消息类型 |

### 1.3 测试分类

| 类型 | 说明 |
|------|------|
| 正向测试 | 验证正常流程 |
| 负向测试 | 验证错误处理 |
| 边界测试 | 验证极限条件 |
| 并发测试 | 验证多线程安全 |
| 性能测试 | 验证性能指标 |

---

## 2. 单元测试

### 2.1 Device Service Tests

**文件:** `tests/unit/test_device_service.py`

#### TC-DEV-001: 创建设备 - 新设备
```python
def test_create_device_new():
    """测试创建新设备"""
    # Input
    device_id = "550e8400e29b41d4a716446655440000"
    nickname = "测试用户"
    
    # Execute
    result = device_service.init_device(device_id, nickname)
    
    # Assert
    assert result["is_new"] == True
    assert result["nickname"] == nickname
    assert result["device_id"] == device_id
```

#### TC-DEV-002: 创建设备 - 已存在设备
```python
def test_create_device_existing():
    """测试已存在设备恢复"""
    # Setup
    device_id = "550e8400e29b41d4a716446655440000"
    device_service.init_device(device_id, "原始昵称")
    
    # Execute
    result = device_service.init_device(device_id, "新昵称")
    
    # Assert
    assert result["is_new"] == False
    assert result["nickname"] == "原始昵称"  # 保持原昵称
```

#### TC-DEV-003: 创建设备 - 无效 device_id
```python
def test_create_device_invalid_id():
    """测试无效 device_id 格式"""
    # Input
    device_id = "invalid-id"
    
    # Execute & Assert
    with pytest.raises(ValidationError) as exc:
        device_service.init_device(device_id, "昵称")
    assert exc.value.code == 5001
```

#### TC-DEV-004: 获取设备资料 - 好友视角
```python
def test_get_device_profile_as_friend():
    """测试好友视角获取完整资料"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    create_friendship(device_a, device_b)
    
    # Execute
    profile = device_service.get_device_profile(device_b, requester_id=device_a)
    
    # Assert
    assert profile["device_id"] == device_b
    assert profile["is_friend"] == True
    assert "avatar" in profile
```

#### TC-DEV-005: 获取设备资料 - 陌生人视角匿名模式
```python
def test_get_device_profile_stranger_anonymous():
    """测试陌生人视角匿名模式资料"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b", is_anonymous=True)
    
    # Execute
    profile = device_service.get_device_profile(device_b, requester_id=device_a)
    
    # Assert
    assert profile["is_friend"] == False
    assert profile.get("avatar") is None  # 匿名模式下隐藏头像
    assert profile["role_name"] is not None
```

#### TC-DEV-006: 更新设备资料
```python
def test_update_device_profile():
    """测试更新设备资料"""
    # Setup
    device_id = create_device("device_1")
    updates = {
        "nickname": "新昵称",
        "tags": ["摄影", "旅行"],
        "is_anonymous": True
    }
    
    # Execute
    result = device_service.update_device(device_id, updates)
    
    # Assert
    assert result["nickname"] == "新昵称"
    assert result["tags"] == ["摄影", "旅行"]
    assert result["is_anonymous"] == True
    assert "updated_at" in result
```

#### TC-DEV-007: 更新设备 - 昵称过长
```python
def test_update_device_nickname_too_long():
    """测试昵称超过 50 字符"""
    # Input
    device_id = create_device("device_1")
    updates = {"nickname": "x" * 51}
    
    # Execute & Assert
    with pytest.raises(ValidationError) as exc:
        device_service.update_device(device_id, updates)
    assert exc.value.code == 5001
```

---

### 2.2 Temp ID Service Tests

**文件:** `tests/unit/test_temp_id_service.py`

#### TC-TEMP-001: 生成临时 ID
```python
def test_generate_temp_id():
    """测试生成新的临时 ID"""
    # Setup
    device_id = create_device("device_1")
    
    # Execute
    result = temp_id_service.refresh_temp_id(device_id)
    
    # Assert
    assert len(result["temp_id"]) == 32
    assert "expires_at" in result
    assert result["expires_at"] > datetime.now()
```

#### TC-TEMP-002: 刷新临时 ID - 旧 ID 缓冲
```python
def test_refresh_temp_id_buffer():
    """测试刷新时旧 ID 进入缓冲期"""
    # Setup
    device_id = create_device("device_1")
    old_temp = temp_id_service.refresh_temp_id(device_id)["temp_id"]
    
    # Execute
    result = temp_id_service.refresh_temp_id(device_id, current_temp_id=old_temp)
    
    # Assert
    assert result["temp_id"] != old_temp
    # 旧 ID 仍应有效（5分钟缓冲）
    assert temp_id_service.resolve_temp_id(old_temp) == device_id
```

#### TC-TEMP-003: 解析有效临时 ID
```python
def test_resolve_valid_temp_id():
    """测试解析有效的临时 ID"""
    # Setup
    device_id = create_device("device_1")
    temp_id = temp_id_service.refresh_temp_id(device_id)["temp_id"]
    
    # Execute
    resolved = temp_id_service.resolve_temp_id(temp_id)
    
    # Assert
    assert resolved == device_id
```

#### TC-TEMP-004: 解析过期临时 ID
```python
def test_resolve_expired_temp_id():
    """测试解析过期的临时 ID"""
    # Setup
    device_id = create_device("device_1")
    temp_id = "expired_temp_id"
    # 手动插入过期记录
    db.temp_ids.insert({
        "temp_id": temp_id,
        "device_id": device_id,
        "expires_at": datetime.now() - timedelta(minutes=1)
    })
    
    # Execute & Assert
    with pytest.raises(NotFoundError) as exc:
        temp_id_service.resolve_temp_id(temp_id)
    assert exc.value.code == 4006
```

---

### 2.3 Presence Service Tests

**文件:** `tests/unit/test_presence_service.py`

#### TC-PRE-001: 解析附近设备
```python
def test_resolve_nearby_devices():
    """测试解析附近设备列表"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    temp_b = temp_id_service.refresh_temp_id(device_b)["temp_id"]
    
    scanned = [{"temp_id": temp_b, "rssi": -65}]
    
    # Execute
    result = presence_service.resolve_nearby(device_a, scanned)
    
    # Assert
    assert len(result["nearby_devices"]) == 1
    assert result["nearby_devices"][0]["device_id"] == device_b
    assert result["nearby_devices"][0]["distance_estimate"] > 0
```

#### TC-PRE-002: 解析附近设备 - 过滤屏蔽
```python
def test_resolve_nearby_filter_blocked():
    """测试解析时过滤被屏蔽设备"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    block_service.block_device(device_a, device_b)  # A 屏蔽 B
    
    temp_b = temp_id_service.refresh_temp_id(device_b)["temp_id"]
    scanned = [{"temp_id": temp_b, "rssi": -65}]
    
    # Execute
    result = presence_service.resolve_nearby(device_a, scanned)
    
    # Assert
    assert len(result["nearby_devices"]) == 0
```

#### TC-PRE-003: 距离估算
```python
def test_distance_estimation():
    """测试 RSSI 转距离估算"""
    test_cases = [
        (-40, 0.1),   # 很近
        (-65, 2.0),   # 适中
        (-85, 20.0),  # 较远
    ]
    
    for rssi, expected_range in test_cases:
        distance = presence_service.estimate_distance(rssi)
        assert abs(distance - expected_range) < expected_range * 0.5
```

#### TC-PRE-004: Boost 检测 - 首次进入范围
```python
def test_boost_detection_first_time():
    """测试好友首次进入范围触发 Boost"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    create_friendship(device_a, device_b)
    temp_b = temp_id_service.refresh_temp_id(device_b)["temp_id"]
    
    scanned = [{"temp_id": temp_b, "rssi": -65}]
    
    # Execute
    result = presence_service.resolve_nearby(device_a, scanned)
    
    # Assert
    assert len(result["boost_alerts"]) == 1
    assert result["boost_alerts"][0]["device_id"] == device_b
```

#### TC-PRE-005: Boost 检测 - 5分钟冷却
```python
def test_boost_detection_cooldown():
    """测试 Boost 5分钟冷却"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    create_friendship(device_a, device_b)
    temp_b = temp_id_service.refresh_temp_id(device_b)["temp_id"]
    
    # 第一次触发 Boost
    presence_service.resolve_nearby(device_a, [{"temp_id": temp_b, "rssi": -65}])
    
    # 立即再次扫描
    result = presence_service.resolve_nearby(device_a, [{"temp_id": temp_b, "rssi": -65}])
    
    # Assert
    assert len(result["boost_alerts"]) == 0  # 冷却中，不触发
```

#### TC-PRE-006: 上报离开范围
```python
def test_report_disconnect():
    """测试上报设备离开范围"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    session = create_temp_session(device_a, device_b)
    
    # Execute
    result = presence_service.report_disconnect(device_a, device_b)
    
    # Assert
    assert result["session_expired"] == True
    assert result["session_id"] == session.id
```

---

### 2.4 Messaging Service Tests

**文件:** `tests/unit/test_messaging_service.py`

#### TC-MSG-001: 发送消息 - 好友
```python
def test_send_message_friend():
    """测试好友间发送消息"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    create_friendship(device_a, device_b)
    
    # Execute
    result = messaging_service.send_message(
        sender_id=device_a,
        receiver_id=device_b,
        content="你好",
        type="common"
    )
    
    # Assert
    assert result["message_id"] is not None
    assert result["status"] == "sent"
```

#### TC-MSG-002: 发送消息 - 非好友首次
```python
def test_send_message_stranger_first():
    """测试非好友首次发送消息"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    
    # Execute
    result = messaging_service.send_message(
        sender_id=device_a,
        receiver_id=device_b,
        content="你好",
        type="common"
    )
    
    # Assert
    assert result["message_id"] is not None
    assert result["session_id"] is not None
```

#### TC-MSG-003: 发送消息 - 非好友第2条
```python
def test_send_message_stranger_second():
    """测试非好友发送第2条消息"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    
    # 发送第一条
    messaging_service.send_message(device_a, device_b, "第一条", "common")
    
    # Execute - 发送第二条
    result = messaging_service.send_message(
        sender_id=device_a,
        receiver_id=device_b,
        content="第二条",
        type="common"
    )
    
    # Assert
    assert result["message_id"] is not None
```

#### TC-MSG-004: 发送消息 - 非好友第3条（超限）
```python
def test_send_message_stranger_third_blocked():
    """测试非好友发送第3条消息被拦截"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    
    # 发送两条
    messaging_service.send_message(device_a, device_b, "第一条", "common")
    messaging_service.send_message(device_a, device_b, "第二条", "common")
    
    # Execute & Assert
    with pytest.raises(BusinessError) as exc:
        messaging_service.send_message(device_a, device_b, "第三条", "common")
    assert exc.value.code == 4001
```

#### TC-MSG-005: 发送消息 - 被对方屏蔽
```python
def test_send_message_blocked():
    """测试向屏蔽自己的用户发送消息"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    block_service.block_device(device_b, device_a)  # B 屏蔽 A
    
    # Execute & Assert
    with pytest.raises(BusinessError) as exc:
        messaging_service.send_message(device_a, device_b, "你好", "common")
    assert exc.value.code == 4004
```

#### TC-MSG-006: 获取历史消息
```python
def test_get_messages():
    """测试获取会话历史消息"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    session = create_session(device_a, device_b)
    
    # 创建 25 条消息
    for i in range(25):
        create_message(session, device_a, device_b, f"消息{i}")
    
    # Execute
    result = messaging_service.get_messages(session.id, device_a, limit=20)
    
    # Assert
    assert len(result["messages"]) == 20
    assert result["has_more"] == True
```

#### TC-MSG-007: 标记已读
```python
def test_mark_messages_read():
    """测试标记消息已读"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    session = create_session(device_a, device_b)
    
    msg1 = create_message(session, device_a, device_b, "消息1")
    msg2 = create_message(session, device_a, device_b, "消息2")
    
    # Execute
    result = messaging_service.mark_read(device_b, [msg1, msg2])
    
    # Assert
    assert result["updated_count"] == 2
    
    # 验证状态更新
    messages = messaging_service.get_messages(session.id, device_a)
    assert all(m["status"] == "read" for m in messages["messages"])
```

---

### 2.5 Relation Service Tests

**文件:** `tests/unit/test_relation_service.py`

#### TC-REL-001: 发送好友申请
```python
def test_send_friend_request():
    """测试发送好友申请"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    
    # Execute
    result = relation_service.send_friend_request(
        sender_id=device_a,
        receiver_id=device_b,
        message="想加你为好友"
    )
    
    # Assert
    assert result["request_id"] is not None
    assert result["status"] == "pending"
```

#### TC-REL-002: 发送好友申请 - 重复申请
```python
def test_send_friend_request_duplicate():
    """测试重复发送好友申请"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    relation_service.send_friend_request(device_a, device_b)
    
    # Execute & Assert
    with pytest.raises(BusinessError) as exc:
        relation_service.send_friend_request(device_a, device_b)
    assert exc.value.code == 4009
```

#### TC-REL-003: 发送好友申请 - 冷却中
```python
def test_send_friend_request_cooldown():
    """测试被拒绝后 24h 内重复申请"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    request = relation_service.send_friend_request(device_a, device_b)
    relation_service.respond_to_request(request["request_id"], device_b, "reject")
    
    # Execute & Assert
    with pytest.raises(BusinessError) as exc:
        relation_service.send_friend_request(device_a, device_b)
    assert exc.value.code == 4005
```

#### TC-REL-004: 接受好友申请
```python
def test_accept_friend_request():
    """测试接受好友申请"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    request = relation_service.send_friend_request(device_a, device_b)
    
    # Execute
    result = relation_service.respond_to_request(
        request["request_id"], device_b, "accept"
    )
    
    # Assert
    assert result["status"] == "accepted"
    assert result["session_id"] is not None
    assert result["friend"]["device_id"] == device_a
```

#### TC-REL-005: 接受好友申请 - 临时会话升级
```python
def test_accept_friend_request_upgrade_session():
    """测试接受申请时临时会话升级为永久"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    temp_session = create_temp_session(device_a, device_b)
    request = relation_service.send_friend_request(device_a, device_b)
    
    # Execute
    result = relation_service.respond_to_request(
        request["request_id"], device_b, "accept"
    )
    
    # Assert
    # 临时会话应被升级为永久
    session = session_service.get_session(temp_session.id)
    assert session["is_temp"] == False
```

#### TC-REL-006: 删除好友
```python
def test_delete_friend():
    """测试删除好友"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    create_friendship(device_a, device_b)
    
    # Execute
    relation_service.delete_friend(device_a, device_b)
    
    # Assert
    friends = relation_service.get_friends(device_a)
    assert len(friends["friends"]) == 0
```

#### TC-REL-007: 屏蔽用户
```python
def test_block_user():
    """测试屏蔽用户"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    
    # Execute
    result = block_service.block_device(device_a, device_b)
    
    # Assert
    assert result is True
    assert block_service.is_blocked(device_a, device_b) == True
```

#### TC-REL-008: 屏蔽好友
```python
def test_block_friend():
    """测试屏蔽好友会删除好友关系"""
    # Setup
    device_a = create_device("device_a")
    device_b = create_device("device_b")
    create_friendship(device_a, device_b)
    
    # Execute
    block_service.block_device(device_a, device_b)
    
    # Assert
    friends = relation_service.get_friends(device_a)
    assert len(friends["friends"]) == 0  # 好友关系被删除
```

---

## 3. 集成测试

### 3.1 Device API Tests

**文件:** `tests/integration/test_device_api.py`

#### TC-API-DEV-001: POST /device/init - 成功
```python
def test_api_device_init_success(client):
    """测试设备初始化 API"""
    response = client.post("/api/v1/device/init", json={
        "device_id": "550e8400e29b41d4a716446655440000",
        "nickname": "测试用户"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["is_new"] == True
```

#### TC-API-DEV-002: POST /device/init - 无效 device_id
```python
def test_api_device_init_invalid_id(client):
    """测试设备初始化 - 无效 device_id"""
    response = client.post("/api/v1/device/init", json={
        "device_id": "invalid-id",
        "nickname": "测试用户"
    })
    
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == 5001
```

#### TC-API-DEV-003: GET /device/{device_id} - 成功
```python
def test_api_get_device_success(client):
    """测试获取设备资料 API"""
    # 先初始化
    client.post("/api/v1/device/init", json={
        "device_id": "device_a",
        "nickname": "用户A"
    })
    
    response = client.get("/api/v1/device/device_a?requester_id=device_a")
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["nickname"] == "用户A"
```

#### TC-API-DEV-004: GET /device/{device_id} - 设备未初始化
```python
def test_api_get_device_not_initialized(client):
    """测试获取未初始化设备"""
    response = client.get("/api/v1/device/unknown_device?requester_id=device_a")
    
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == 4007
```

#### TC-API-DEV-005: PUT /device/{device_id} - 成功
```python
def test_api_update_device_success(client):
    """测试更新设备资料 API"""
    client.post("/api/v1/device/init", json={
        "device_id": "device_a",
        "nickname": "原昵称"
    })
    
    response = client.put("/api/v1/device/device_a", json={
        "nickname": "新昵称",
        "tags": ["摄影"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["nickname"] == "新昵称"
```

---

### 3.2 Temp ID API Tests

**文件:** `tests/integration/test_temp_id_api.py`

#### TC-API-TEMP-001: POST /temp-id/refresh - 成功
```python
def test_api_refresh_temp_id(client):
    """测试刷新临时 ID API"""
    client.post("/api/v1/device/init", json={
        "device_id": "device_a",
        "nickname": "用户A"
    })
    
    response = client.post("/api/v1/temp-id/refresh", json={
        "device_id": "device_a"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]["temp_id"]) == 32
```

---

### 3.3 Presence API Tests

**文件:** `tests/integration/test_presence_api.py`

#### TC-API-PRE-001: POST /presence/resolve - 成功
```python
def test_api_resolve_nearby(client):
    """测试解析附近设备 API"""
    # 初始化两个设备
    client.post("/api/v1/device/init", json={
        "device_id": "device_a", "nickname": "用户A"
    })
    client.post("/api/v1/device/init", json={
        "device_id": "device_b", "nickname": "用户B"
    })
    
    # 获取 device_b 的 temp_id
    temp_response = client.post("/api/v1/temp-id/refresh", json={
        "device_id": "device_b"
    })
    temp_id = temp_response.json()["data"]["temp_id"]
    
    # 解析附近设备
    response = client.post("/api/v1/presence/resolve", json={
        "device_id": "device_a",
        "scanned_devices": [{"temp_id": temp_id, "rssi": -65}]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]["nearby_devices"]) == 1
```

---

### 3.4 Messaging API Tests

**文件:** `tests/integration/test_messaging_api.py`

#### TC-API-MSG-001: POST /messages - 好友消息
```python
def test_api_send_message_friend(client):
    """测试发送好友消息 API"""
    # 初始化和建立好友关系
    client.post("/api/v1/device/init", json={"device_id": "device_a", "nickname": "用户A"})
    client.post("/api/v1/device/init", json={"device_id": "device_b", "nickname": "用户B"})
    
    # 发送好友申请并接受
    request_response = client.post("/api/v1/friends/request", json={
        "sender_id": "device_a",
        "receiver_id": "device_b"
    })
    request_id = request_response.json()["data"]["request_id"]
    
    client.put(f"/api/v1/friends/{request_id}", json={
        "device_id": "device_b",
        "action": "accept"
    })
    
    # 发送消息
    response = client.post("/api/v1/messages", json={
        "sender_id": "device_a",
        "receiver_id": "device_b",
        "content": "你好",
        "type": "common"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["message_id"] is not None
```

#### TC-API-MSG-002: POST /messages - 临时消息超限
```python
def test_api_send_message_temp_limit(client):
    """测试临时消息超限"""
    client.post("/api/v1/device/init", json={"device_id": "device_a", "nickname": "用户A"})
    client.post("/api/v1/device/init", json={"device_id": "device_b", "nickname": "用户B"})
    
    # 发送 3 条消息
    for i in range(3):
        response = client.post("/api/v1/messages", json={
            "sender_id": "device_a",
            "receiver_id": "device_b",
            "content": f"消息{i}",
            "type": "common"
        })
    
    assert response.status_code == 400
    assert response.json()["code"] == 4001
```

#### TC-API-MSG-003: GET /messages/{session_id}
```python
def test_api_get_messages(client):
    """测试获取历史消息 API"""
    # 初始化、建好友关系、发送消息
    setup_friendship_and_messages(client)
    session_id = get_session_id(client, "device_a", "device_b")
    
    response = client.get(f"/api/v1/messages/{session_id}?device_id=device_a&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]["messages"]) <= 10
```

---

### 3.5 Relation API Tests

**文件:** `tests/integration/test_relation_api.py`

#### TC-API-REL-001: GET /friends
```python
def test_api_get_friends(client):
    """测试获取好友列表 API"""
    client.post("/api/v1/device/init", json={"device_id": "device_a", "nickname": "用户A"})
    client.post("/api/v1/device/init", json={"device_id": "device_b", "nickname": "用户B"})
    
    # 建立好友关系
    request_response = client.post("/api/v1/friends/request", json={
        "sender_id": "device_a", "receiver_id": "device_b"
    })
    client.put(f"/api/v1/friends/{request_response.json()['data']['request_id']}", json={
        "device_id": "device_b", "action": "accept"
    })
    
    response = client.get("/api/v1/friends?device_id=device_a")
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]["friends"]) == 1
```

#### TC-API-REL-002: POST /friends/request - 冷却中
```python
def test_api_friend_request_cooldown(client):
    """测试好友申请冷却"""
    client.post("/api/v1/device/init", json={"device_id": "device_a", "nickname": "用户A"})
    client.post("/api/v1/device/init", json={"device_id": "device_b", "nickname": "用户B"})
    
    # 发送申请并拒绝
    request_response = client.post("/api/v1/friends/request", json={
        "sender_id": "device_a", "receiver_id": "device_b"
    })
    client.put(f"/api/v1/friends/{request_response.json()['data']['request_id']}", json={
        "device_id": "device_b", "action": "reject"
    })
    
    # 立即再次申请
    response = client.post("/api/v1/friends/request", json={
        "sender_id": "device_a", "receiver_id": "device_b"
    })
    
    assert response.status_code == 429
    assert response.json()["code"] == 4005
```

---

## 4. WebSocket 测试

### 4.1 Connection Tests

**文件:** `tests/websocket/test_connection.py`

#### TC-WS-CONN-001: 成功连接
```python
async def test_websocket_connect_success(websocket_client):
    """测试 WebSocket 成功连接"""
    # 先初始化设备
    await init_device("device_ws_1")
    
    async with websocket_client.connect(f"/api/v1/ws?device_id=device_ws_1") as ws:
        # 接收 connected 确认
        response = await ws.receive_json()
        assert response["type"] == "connected"
        assert response["payload"]["device_id"] == "device_ws_1"
```

#### TC-WS-CONN-002: 未初始化设备连接
```python
async def test_websocket_connect_not_initialized(websocket_client):
    """测试未初始化设备连接被拒绝"""
    with pytest.raises(Exception):
        async with websocket_client.connect("/api/v1/ws?device_id=unknown") as ws:
            pass
```

#### TC-WS-CONN-003: 重复连接
```python
async def test_websocket_duplicate_connection(websocket_client):
    """测试同一设备重复连接"""
    await init_device("device_ws_dup")
    
    async with websocket_client.connect("/api/v1/ws?device_id=device_ws_dup") as ws1:
        # 第二个连接应断开第一个
        async with websocket_client.connect("/api/v1/ws?device_id=device_ws_dup") as ws2:
            # 第一个连接应收到断开通知或异常
            pass
```

---

### 4.2 Message Tests

**文件:** `tests/websocket/test_messaging.py`

#### TC-WS-MSG-001: 发送消息
```python
async def test_websocket_send_message(websocket_client):
    """测试通过 WebSocket 发送消息"""
    await init_device("device_a")
    await init_device("device_b")
    await make_friends("device_a", "device_b")
    
    async with websocket_client.connect("/api/v1/ws?device_id=device_a") as ws_a:
        async with websocket_client.connect("/api/v1/ws?device_id=device_b") as ws_b:
            # 等待 connected 确认
            await ws_a.receive_json()
            await ws_b.receive_json()
            
            # A 发送消息给 B
            await ws_a.send_json({
                "action": "send_message",
                "payload": {
                    "receiver_id": "device_b",
                    "content": "你好",
                    "type": "common"
                }
            })
            
            # B 接收消息
            received = await ws_b.receive_json()
            assert received["type"] == "new_message"
            assert received["payload"]["content"] == "你好"
            assert received["payload"]["sender_id"] == "device_a"
```

#### TC-WS-MSG-002: 消息送达确认
```python
async def test_websocket_message_delivery(websocket_client):
    """测试消息发送确认"""
    await init_device("device_a")
    await init_device("device_b")
    await make_friends("device_a", "device_b")
    
    async with websocket_client.connect("/api/v1/ws?device_id=device_a") as ws:
        await ws.receive_json()  # connected
        
        await ws.send_json({
            "action": "send_message",
            "payload": {
                "receiver_id": "device_b",
                "content": "测试",
                "type": "common"
            }
        })
        
        # 接收发送确认
        response = await ws.receive_json()
        assert response["type"] == "message_sent"
        assert response["payload"]["message_id"] is not None
```

#### TC-WS-MSG-003: 标记已读
```python
async def test_websocket_mark_read(websocket_client):
    """测试 WebSocket 标记已读"""
    await init_device("device_a")
    await init_device("device_b")
    await make_friends("device_a", "device_b")
    
    # 先发送一条消息
    msg_id = await send_message("device_a", "device_b", "你好")
    
    async with websocket_client.connect("/api/v1/ws?device_id=device_b") as ws_b:
        async with websocket_client.connect("/api/v1/ws?device_id=device_a") as ws_a:
            await ws_a.receive_json()
            await ws_b.receive_json()
            
            # B 标记已读
            await ws_b.send_json({
                "action": "mark_read",
                "payload": {"message_ids": [msg_id]}
            })
            
            # A 接收已读回执
            received = await ws_a.receive_json()
            assert received["type"] == "messages_read"
            assert msg_id in received["payload"]["message_ids"]
```

---

### 4.3 Friend Request Tests

**文件:** `tests/websocket/test_friend_request.py`

#### TC-WS-FR-001: 好友申请推送
```python
async def test_websocket_friend_request(websocket_client):
    """测试好友申请实时推送"""
    await init_device("device_a")
    await init_device("device_b")
    
    async with websocket_client.connect("/api/v1/ws?device_id=device_b") as ws_b:
        await ws_b.receive_json()  # connected
        
        # A 发送好友申请
        await send_friend_request_http("device_a", "device_b")
        
        # B 接收推送
        received = await ws_b.receive_json()
        assert received["type"] == "friend_request"
        assert received["payload"]["sender"]["device_id"] == "device_a"
```

#### TC-WS-FR-002: 好友申请结果推送
```python
async def test_websocket_friend_response(websocket_client):
    """测试好友申请结果推送"""
    await init_device("device_a")
    await init_device("device_b")
    request_id = await send_friend_request_http("device_a", "device_b")
    
    async with websocket_client.connect("/api/v1/ws?device_id=device_a") as ws_a:
        await ws_a.receive_json()  # connected
        
        # B 接受申请
        await respond_friend_request_http(request_id, "device_b", "accept")
        
        # A 接收结果
        received = await ws_a.receive_json()
        assert received["type"] == "friend_response"
        assert received["payload"]["status"] == "accepted"
        assert received["payload"]["session_id"] is not None
```

---

### 4.4 Boost Tests

**文件:** `tests/websocket/test_boost.py`

#### TC-WS-BOOST-001: Boost 推送
```python
async def test_websocket_boost(websocket_client):
    """测试好友接近 Boost 推送"""
    await init_device("device_a")
    await init_device("device_b")
    await make_friends("device_a", "device_b")
    
    async with websocket_client.connect("/api/v1/ws?device_id=device_a") as ws_a:
        await ws_a.receive_json()  # connected
        
        # B 进入 A 的蓝牙范围
        temp_id = await refresh_temp_id("device_b")
        await resolve_nearby_http("device_a", [{"temp_id": temp_id, "rssi": -60}])
        
        # A 接收 Boost
        received = await ws_a.receive_json()
        assert received["type"] == "boost"
        assert received["payload"]["device_id"] == "device_b"
        assert received["payload"]["distance_estimate"] < 5.0
```

---

### 4.5 Session Expired Tests

**文件:** `tests/websocket/test_session.py`

#### TC-WS-SESS-001: 临时会话过期推送
```python
async def test_websocket_session_expired(websocket_client):
    """测试临时会话过期推送"""
    await init_device("device_a")
    await init_device("device_b")
    session_id = await create_temp_session("device_a", "device_b")
    
    async with websocket_client.connect("/api/v1/ws?device_id=device_a") as ws_a:
        async with websocket_client.connect("/api/v1/ws?device_id=device_b") as ws_b:
            await ws_a.receive_json()
            await ws_b.receive_json()
            
            # 上报离开范围
            await report_disconnect_http("device_a", "device_b")
            
            # 双方都接收 session_expired
            for ws in [ws_a, ws_b]:
                received = await ws.receive_json()
                assert received["type"] == "session_expired"
                assert received["payload"]["session_id"] == session_id
```

---

### 4.6 Heartbeat Tests

**文件:** `tests/websocket/test_heartbeat.py`

#### TC-WS-HB-001: Ping-Pong
```python
async def test_websocket_ping_pong(websocket_client):
    """测试 WebSocket 心跳"""
    await init_device("device_hb")
    
    async with websocket_client.connect("/api/v1/ws?device_id=device_hb") as ws:
        await ws.receive_json()  # connected
        
        await ws.send_json({"action": "ping"})
        
        response = await ws.receive_json()
        assert response["type"] == "pong"
```

---

## 5. 并发测试

### 5.1 消息并发测试

**文件:** `tests/concurrent/test_message_concurrency.py`

#### TC-CON-MSG-001: 并发发送消息
```python
async def test_concurrent_message_send():
    """测试并发发送消息"""
    device_a = create_device("con_device_a")
    device_b = create_device("con_device_b")
    make_friends(device_a, device_b)
    
    async def send_message_task(idx):
        return messaging_service.send_message(
            device_a, device_b, f"并发消息{idx}", "common"
        )
    
    # 100 个并发发送
    tasks = [send_message_task(i) for i in range(100)]
    results = await asyncio.gather(*tasks)
    
    # 验证所有消息都成功
    assert len(results) == 100
    assert all(r["message_id"] is not None for r in results)
    
    # 验证消息顺序（至少大致有序）
    messages = messaging_service.get_messages(
        get_session_id(device_a, device_b), device_a, limit=100
    )
    assert len(messages["data"]["messages"]) == 100
```

#### TC-CON-MSG-002: 多设备同时扫描
```python
async def test_concurrent_presence_resolve():
    """测试多设备同时扫描同一设备"""
    target_device = create_device("target")
    temp_id = temp_id_service.refresh_temp_id(target_device)["temp_id"]
    
    scanner_devices = [create_device(f"scanner_{i}") for i in range(10)]
    
    async def scan_task(scanner_id):
        return presence_service.resolve_nearby(
            scanner_id, [{"temp_id": temp_id, "rssi": -65}]
        )
    
    # 10 个设备同时扫描
    tasks = [scan_task(d) for d in scanner_devices]
    results = await asyncio.gather(*tasks)
    
    # 所有扫描都应成功
    assert all(len(r["nearby_devices"]) == 1 for r in results)
```

---

### 5.2 Temp ID 并发测试

**文件:** `tests/concurrent/test_temp_id_concurrency.py`

#### TC-CON-TEMP-001: 并发刷新 Temp ID
```python
async def test_concurrent_temp_id_refresh():
    """测试并发刷新同一设备的 Temp ID"""
    device_id = create_device("con_temp_device")
    
    async def refresh_task():
        return temp_id_service.refresh_temp_id(device_id)
    
    # 10 个并发刷新请求
    tasks = [refresh_task() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    # 所有请求都应返回有效的 temp_id
    temp_ids = [r["temp_id"] for r in results]
    assert all(len(t) == 32 for t in temp_ids)
    
    # 只有一个 temp_id 应该是最新的（最后一个）
    latest_temp = temp_ids[-1]
    resolved = temp_id_service.resolve_temp_id(latest_temp)
    assert resolved == device_id
```

---

### 5.3 WebSocket 并发测试

**文件:** `tests/concurrent/test_websocket_concurrency.py`

#### TC-CON-WS-001: 多客户端同时连接
```python
async def test_websocket_multiple_clients(websocket_client):
    """测试大量客户端同时连接"""
    device_count = 100
    
    for i in range(device_count):
        await init_device(f"ws_device_{i}")
    
    connections = []
    for i in range(device_count):
        ws = await websocket_client.connect(f"/api/v1/ws?device_id=ws_device_{i}")
        connections.append(ws)
    
    # 验证所有连接都成功
    assert len(connections) == device_count
    
    # 验证都能收发消息
    for ws in connections[:10]:  # 抽样验证
        response = await ws.receive_json()
        assert response["type"] == "connected"
    
    # 清理
    for ws in connections:
        await ws.close()
```

---

## 6. 性能测试

### 6.1 API 性能测试

**文件:** `tests/performance/test_api_performance.py`

#### TC-PERF-API-001: 设备初始化性能
```python
def test_device_init_performance(client):
    """测试设备初始化性能"""
    import time
    
    start = time.time()
    for i in range(1000):
        response = client.post("/api/v1/device/init", json={
            "device_id": f"perf_device_{i}",
            "nickname": f"用户{i}"
        })
        assert response.status_code == 200
    
    elapsed = time.time() - start
    # 1000 次初始化应在 10 秒内完成
    assert elapsed < 10.0
```

#### TC-PERF-API-002: 消息发送性能
```python
def test_message_send_performance(client):
    """测试消息发送性能"""
    import time
    
    # 准备好友关系
    client.post("/api/v1/device/init", json={"device_id": "perf_sender", "nickname": "发送者"})
    client.post("/api/v1/device/init", json={"device_id": "perf_receiver", "nickname": "接收者"})
    
    request_response = client.post("/api/v1/friends/request", json={
        "sender_id": "perf_sender",
        "receiver_id": "perf_receiver"
    })
    client.put(f"/api/v1/friends/{request_response.json()['data']['request_id']}", json={
        "device_id": "perf_receiver",
        "action": "accept"
    })
    
    start = time.time()
    for i in range(1000):
        response = client.post("/api/v1/messages", json={
            "sender_id": "perf_sender",
            "receiver_id": "perf_receiver",
            "content": f"性能测试消息{i}",
            "type": "common"
        })
        assert response.status_code == 200
    
    elapsed = time.time() - start
    # 1000 条消息应在 5 秒内完成
    assert elapsed < 5.0
```

---

### 6.2 WebSocket 性能测试

**文件:** `tests/performance/test_websocket_performance.py`

#### TC-PERF-WS-001: 消息吞吐量
```python
async def test_websocket_throughput(websocket_client):
    """测试 WebSocket 消息吞吐量"""
    await init_device("throughput_a")
    await init_device("throughput_b")
    await make_friends("throughput_a", "throughput_b")
    
    async with websocket_client.connect("/api/v1/ws?device_id=throughput_a") as ws_a:
        async with websocket_client.connect("/api/v1/ws?device_id=throughput_b") as ws_b:
            await ws_a.receive_json()
            await ws_b.receive_json()
            
            message_count = 1000
            start = time.time()
            
            # 发送消息
            for i in range(message_count):
                await ws_a.send_json({
                    "action": "send_message",
                    "payload": {
                        "receiver_id": "throughput_b",
                        "content": f"消息{i}",
                        "type": "common"
                    }
                })
            
            # 接收所有消息
            received = 0
            while received < message_count:
                msg = await ws_b.receive_json()
                if msg["type"] == "new_message":
                    received += 1
            
            elapsed = time.time() - start
            throughput = message_count / elapsed
            
            # 吞吐量应大于 500 条/秒
            assert throughput > 500
```

---

## 7. 测试数据

### 7.1  fixtures

```python
# tests/conftest.py

import pytest
from app import create_app

@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app(testing=True)
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """HTTP 测试客户端"""
    return app.test_client()

@pytest.fixture
async def websocket_client(app):
    """WebSocket 测试客户端"""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def db(app):
    """数据库连接"""
    from app.db import get_db
    return get_db()

@pytest.fixture(autouse=True)
def clean_db(db):
    """每次测试前清理数据库"""
    db.execute("TRUNCATE TABLE devices, friendships, sessions, messages, temp_ids, presence, blocks CASCADE")
    yield
```

### 7.2 辅助函数

```python
# tests/helpers.py

def create_device(device_id, **kwargs):
    """创建设备"""
    from app.services.device_service import device_service
    return device_service.init_device(device_id, nickname=kwargs.get("nickname", f"用户{device_id}"), **kwargs)

def make_friends(device_a, device_b):
    """建立好友关系"""
    from app.services.relation_service import relation_service
    request = relation_service.send_friend_request(device_a, device_b)
    return relation_service.respond_to_request(request["request_id"], device_b, "accept")

def create_temp_session(device_a, device_b):
    """创建临时会话"""
    from app.services.messaging_service import messaging_service
    result = messaging_service.send_message(device_a, device_b, "创建会话", "common")
    return result["session_id"]
```

---

## 8. 测试环境

### 8.1 目录结构

```
tests/
├── __init__.py
├── conftest.py              # 全局 fixtures
├── helpers.py               # 测试辅助函数
├── unit/                    # 单元测试
│   ├── __init__.py
│   ├── test_device_service.py
│   ├── test_temp_id_service.py
│   ├── test_presence_service.py
│   ├── test_messaging_service.py
│   └── test_relation_service.py
├── integration/             # 集成测试
│   ├── __init__.py
│   ├── test_device_api.py
│   ├── test_temp_id_api.py
│   ├── test_presence_api.py
│   ├── test_messaging_api.py
│   └── test_relation_api.py
├── websocket/               # WebSocket 测试
│   ├── __init__.py
│   ├── test_connection.py
│   ├── test_messaging.py
│   ├── test_friend_request.py
│   ├── test_boost.py
│   ├── test_session.py
│   └── test_heartbeat.py
├── concurrent/              # 并发测试
│   ├── __init__.py
│   ├── test_message_concurrency.py
│   ├── test_temp_id_concurrency.py
│   └── test_websocket_concurrency.py
└── performance/             # 性能测试
    ├── __init__.py
    ├── test_api_performance.py
    └── test_websocket_performance.py
```

### 8.2 运行命令

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行 WebSocket 测试
pytest tests/websocket/

# 运行并发测试
pytest tests/concurrent/

# 运行性能测试
pytest tests/performance/ --timeout=300

# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 并行运行测试
pytest -n auto
```

### 8.3 CI/CD 配置

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: notepassing_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=app
      
      - name: Run integration tests
        run: pytest tests/integration/ -v
      
      - name: Run WebSocket tests
        run: pytest tests/websocket/ -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 附录：测试用例清单

| ID | 模块 | 名称 | 类型 |
|----|------|------|------|
| TC-DEV-001 | Device | 创建设备-新设备 | 单元测试 |
| TC-DEV-002 | Device | 创建设备-已存在 | 单元测试 |
| TC-DEV-003 | Device | 创建设备-无效ID | 单元测试 |
| TC-DEV-004 | Device | 获取资料-好友 | 单元测试 |
| TC-DEV-005 | Device | 获取资料-陌生人 | 单元测试 |
| TC-DEV-006 | Device | 更新资料 | 单元测试 |
| TC-DEV-007 | Device | 昵称过长 | 单元测试 |
| TC-TEMP-001 | Temp ID | 生成临时ID | 单元测试 |
| TC-TEMP-002 | Temp ID | 刷新缓冲 | 单元测试 |
| TC-TEMP-003 | Temp ID | 解析有效ID | 单元测试 |
| TC-TEMP-004 | Temp ID | 解析过期ID | 单元测试 |
| TC-PRE-001 | Presence | 解析附近 | 单元测试 |
| TC-PRE-002 | Presence | 过滤屏蔽 | 单元测试 |
| TC-PRE-003 | Presence | 距离估算 | 单元测试 |
| TC-PRE-004 | Presence | Boost触发 | 单元测试 |
| TC-PRE-005 | Presence | Boost冷却 | 单元测试 |
| TC-PRE-006 | Presence | 上报离开 | 单元测试 |
| TC-MSG-001 | Messaging | 好友消息 | 单元测试 |
| TC-MSG-002 | Messaging | 陌生人首条 | 单元测试 |
| TC-MSG-003 | Messaging | 陌生人第2条 | 单元测试 |
| TC-MSG-004 | Messaging | 陌生人超限 | 单元测试 |
| TC-MSG-005 | Messaging | 被屏蔽 | 单元测试 |
| TC-MSG-006 | Messaging | 获取历史 | 单元测试 |
| TC-MSG-007 | Messaging | 标记已读 | 单元测试 |
| TC-REL-001 | Relation | 发送申请 | 单元测试 |
| TC-REL-002 | Relation | 重复申请 | 单元测试 |
| TC-REL-003 | Relation | 申请冷却 | 单元测试 |
| TC-REL-004 | Relation | 接受申请 | 单元测试 |
| TC-REL-005 | Relation | 会话升级 | 单元测试 |
| TC-REL-006 | Relation | 删除好友 | 单元测试 |
| TC-REL-007 | Relation | 屏蔽用户 | 单元测试 |
| TC-REL-008 | Relation | 屏蔽好友 | 单元测试 |
| TC-API-* | All | API集成测试 | 集成测试 |
| TC-WS-* | WebSocket | WebSocket测试 | WebSocket测试 |
| TC-CON-* | Concurrent | 并发测试 | 并发测试 |
| TC-PERF-* | Performance | 性能测试 | 性能测试 |
