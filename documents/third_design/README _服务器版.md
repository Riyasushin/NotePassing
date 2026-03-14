# NotePassing API

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Anonymous nearby messaging API for ephemeral social interactions via Bluetooth Low Energy (BLE).

NotePassing is a privacy-first messaging backend that enables users to discover and chat with nearby people without revealing their identity. Users broadcast temporary IDs via BLE, exchange messages when close to each other, and can build connections through a friend system.

---

## ✨ Features

- **🔒 Anonymous by Design** - Users identified by device IDs with privacy-controlled profiles
- **📡 BLE-based Discovery** - Scan nearby devices using temporary broadcast IDs
- **💬 Ephemeral Messaging** - Chat with nearby strangers without adding friends first
- **👥 Friend System** - Send friend requests to build permanent connections
- **⚡ Real-time** - WebSocket support for instant message delivery
- **🛡️ Privacy Controls** - Anonymous mode, blocking, and granular profile visibility

---

## 🏗️ Architecture

### Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI (async) |
| Database | PostgreSQL (production) / SQLite (testing) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| WebSocket | Native FastAPI WebSockets |
| Deployment | Docker + Docker Compose |

### Data Model

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  devices    │◄────┤  temp_ids   │     │   blocks    │
│  (users)    │     │  (BLE IDs)  │     │ (blacklist) │
└──────┬──────┘     └─────────────┘     └─────────────┘
       │
       ├──► friendships (pending/accepted/rejected)
       │
       ├──► sessions ──► messages
       │
       └──► presences (nearby tracking)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ (or use Docker)
- Docker & Docker Compose (optional)

### Option 1: Docker Compose (Recommended)

```bash
# Clone and start
git clone <repo-url>
cd notepassing-backend
cp .env.example .env
# Edit .env if needed

docker-compose up -d

# API available at http://localhost:8000
# Docs available at http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set environment variables
cp .env.example .env
# Edit .env with your database URL

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📚 API Overview

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/device/init` | POST | Initialize or recover a device |
| `/device/{id}` | GET | Get device profile (with privacy filtering) |
| `/device/{id}` | PUT | Update device profile |
| `/temp-id/refresh` | POST | Generate new temporary BLE ID |
| `/presence/resolve` | POST | Resolve scanned temp IDs to profiles |
| `/presence/disconnect` | POST | Report device leaving Bluetooth range |
| `/friends` | GET | List friends |
| `/friends/request` | POST | Send friend request |
| `/friends/{id}` | PUT | Accept/reject friend request |
| `/friends/{id}` | DELETE | Remove friend |
| `/messages` | POST | Send message |
| `/messages/{session_id}` | GET | Get message history |
| `/messages/read` | POST | Mark messages as read |
| `/blocks` | POST | Block user |

### WebSocket Events

Connect to `/api/v1/ws?device_id={device_id}`

**Client → Server:**
- `send_message` - Send a message
- `mark_read` - Mark messages as read
- `ping` - Keep connection alive

**Server → Client:**
- `connected` - Connection confirmed
- `new_message` - New message received
- `message_sent` - Message delivery confirmation
- `friend_request` - New friend request
- `friend_response` - Friend request response
- `boost` - Friend came nearby
- `session_expired` - Temporary session ended
- `messages_read` - Messages marked as read

---

## 🔐 Privacy & Security

### Temp ID Lifecycle
- Valid for **10 minutes** (5 min active + 5 min buffer)
- Derived from `device_id` + `secret_key` for verification
- Automatic rotation prevents tracking

### Session Types
| Type | Description | Limitations |
|------|-------------|-------------|
| **Temporary** | Non-friends chatting | Max 2 messages before reply, expires on disconnect |
| **Permanent** | Friends chatting | No restrictions |

### Profile Visibility
| Mode | Friends | Strangers (Anonymous) | Strangers (Public) |
|------|---------|----------------------|-------------------|
| Avatar | ✅ Visible | ❌ Hidden | ✅ Visible |
| Nickname | ✅ Visible | 仅显示 `不愿透露姓名的ta` | ✅ Visible |
| Role Name | ✅ Visible | ❌ Hidden | ❌ Hidden |
| Profile | ✅ Visible | ❌ Hidden | ❌ Hidden |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_device.py -v
```

---

## 📁 Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Settings management
│   ├── database.py          # DB connection & session
│   ├── dependencies.py      # FastAPI dependencies
│   ├── models/              # SQLAlchemy models
│   │   ├── device.py
│   │   ├── temp_id.py
│   │   ├── presence.py
│   │   ├── session.py
│   │   ├── message.py
│   │   ├── friendship.py
│   │   ├── block.py
│   │   └── ws_connection.py
│   ├── routers/             # API route handlers
│   │   ├── device.py
│   │   ├── temp_id.py
│   │   ├── presence.py
│   │   ├── friendship.py
│   │   ├── message.py
│   │   ├── block.py
│   │   └── websocket.py
│   ├── schemas/             # Pydantic request/response models
│   ├── services/            # Business logic
│   │   ├── device_service.py
│   │   ├── temp_id_service.py
│   │   ├── presence_service.py
│   │   ├── relation_service.py
│   │   ├── message_service.py
│   │   └── websocket_manager.py
│   └── utils/               # Utilities & helpers
├── alembic/                 # Database migrations
├── tests/                   # Test suite
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Container definition
├── pyproject.toml           # Dependencies & tool config
└── README.md
```

---

## ⚙️ Configuration

Environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection string |
| `SECRET_KEY` | `change-me-in-production` | Key for temp ID generation |
| `DEBUG` | `true` | Enable debug mode |
| `TEMP_ID_EXPIRE_MINUTES` | `10` | Temp ID total lifetime |
| `TEMP_ID_BUFFER_MINUTES` | `5` | Buffer for old ID after refresh |
| `BOOST_COOLDOWN_MINUTES` | `5` | Minimum time between boost alerts |

---

## 🛣️ Roadmap

- [ ] Media message support (images, voice)
- [ ] End-to-end encryption
- [ ] Group chats for nearby users
- [ ] Geofenced message broadcasting
- [ ] Push notifications (APNs/FCM)
- [ ] Message persistence improvements

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with [FastAPI](https://fastapi.tiangolo.com) and [SQLAlchemy](https://www.sqlalchemy.org/).

</div>
