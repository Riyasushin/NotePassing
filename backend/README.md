# NotePassing Backend

NotePassing API - Anonymous nearby messaging service.

## Features

- **Device Management**: Device registration, profile management with privacy controls
- **Temp ID Service**: Temporary BLE broadcast IDs with rotation
- **Messaging**: Friend and stranger messaging with temporary sessions
- **Friendship**: Friend requests, acceptance/rejection with 24h cooldown
- **Blocking**: User blocking with automatic friendship removal
- **WebSocket**: Real-time message delivery and notifications

## Requirements

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) - Python package manager
- PostgreSQL (optional, SQLite for testing)

## Quick Start

### Development Setup

```bash
# Clone and navigate
cd backend

# Create virtual environment
uv venv --python python3.10

# Install dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Start development server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Setup

```bash
# Start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run migrations (if needed)
docker-compose exec backend alembic upgrade head
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/notepassing

# Security
SECRET_KEY=your-secret-key-here-change-in-production

# Application
DEBUG=true
TEMP_ID_EXPIRE_MINUTES=10
TEMP_ID_BUFFER_MINUTES=5
BOOST_COOLDOWN_MINUTES=5
```

## API Documentation

When running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### REST Endpoints

#### Device Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/device/init` | Initialize/recover device |
| GET | `/api/v1/device/{device_id}?requester_id={id}` | Get device profile |
| PUT | `/api/v1/device/{device_id}` | Update device profile |

#### Temp ID Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/temp-id/refresh` | Generate new temp ID |

#### Messaging Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/messages` | Send message |
| GET | `/api/v1/messages/{session_id}` | Get message history |
| POST | `/api/v1/messages/read` | Mark messages as read |

#### Friendship Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/friends` | Get friend list |
| POST | `/api/v1/friends/request` | Send friend request |
| PUT | `/api/v1/friends/{request_id}` | Accept/reject request |
| DELETE | `/api/v1/friends/{friend_id}` | Delete friendship |

#### Block Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/block` | Block user |
| DELETE | `/api/v1/block/{target_id}` | Unblock user |

### WebSocket

```
WSS /api/v1/ws?device_id={device_id}
```

**Client → Server Actions:**
```json
{"action": "send_message", "payload": {"receiver_id": "...", "content": "...", "type": "common"}}
{"action": "mark_read", "payload": {"message_ids": ["..."]}}
{"action": "ping"}
```

**Server → Client Events:**
```json
{"type": "connected", "payload": {"device_id": "...", "server_time": "..."}}
{"type": "new_message", "payload": {...}}
{"type": "message_sent", "payload": {...}}
{"type": "friend_request", "payload": {...}}
{"type": "error", "payload": {"code": 4001, "message": "..."}}
```

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_device.py -v
uv run pytest tests/test_integration.py -v

# Run with coverage
uv run pytest tests/ --cov=app --cov-report=html

# Run integration tests only
uv run pytest tests/test_integration.py -v
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry
│   ├── config.py            # Settings
│   ├── database.py          # DB connection
│   ├── dependencies.py      # FastAPI deps
│   ├── models/              # SQLAlchemy models
│   │   ├── device.py
│   │   ├── temp_id.py
│   │   ├── session.py
│   │   ├── message.py
│   │   ├── friendship.py
│   │   ├── block.py
│   │   └── ...
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   │   ├── device_service.py
│   │   ├── temp_id_service.py
│   │   ├── message_service.py
│   │   ├── relation_service.py
│   │   └── websocket_manager.py
│   ├── routers/             # API routes
│   │   ├── device.py
│   │   ├── temp_id.py
│   │   ├── message.py
│   │   ├── friendship.py
│   │   ├── block.py
│   │   └── websocket.py
│   └── utils/               # Utilities
│       ├── error_codes.py
│       ├── exceptions.py
│       ├── response.py
│       ├── uuid_utils.py
│       └── validators.py
├── tests/                   # Test files
├── pyproject.toml           # Project config
├── Dockerfile               # Docker build
├── docker-compose.yml       # Docker compose
└── README.md                # This file
```

## Business Logic

### Temp Session Rules
- Non-friends can send max 2 messages before receiving a reply
- Session expires 1 minute after Bluetooth disconnect
- Auto-creates on first message

### Friend Request Rules
- 24h cooldown after rejection
- Cannot send if blocked (4004)
- Duplicate requests rejected (4009)

### Privacy Rules
- Anonymous mode: strangers see `role_name`, not `avatar`
- Friends always see full profile
- Blocked users invisible to each other

### Temp ID Lifecycle
- Valid for 10 minutes (5 active + 5 buffer)
- Refresh before expiration
- Old ID valid for 5 minutes after refresh

## Error Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 4001 | Temp chat limit reached |
| 4002 | Temp session expired |
| 4003 | Not in Bluetooth range |
| 4004 | Blocked by user |
| 4005 | Friend request cooldown |
| 4006 | Invalid temp ID |
| 4007 | Device not initialized |
| 4008 | Friendship not exist |
| 4009 | Duplicate operation |
| 5001 | Invalid params |
| 5002 | Server error |

## License

MIT License
