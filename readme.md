# NotePassing 塞纸条

基于 BLE 蓝牙发现的近距离社交 Android App。用户通过蓝牙广播在同一物理空间内发现彼此，发起短距聊天、添加好友。

## 技术栈

- **Android**: Kotlin / Jetpack Compose / BLE API / Room / Coroutines
- **Server**: Python FastAPI / WebSocket
- **Database**: PostgreSQL + Redis
- **Auth**: Supabase

## 项目结构

```
NotePassing/
├── android-app/          # Android 客户端
│   └── (MVVM: ui / data / repository / ble)
├── documents/            # 项目开发资料
├── designs/              # 项目设计
└── README.md
```

---

