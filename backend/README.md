# NotePassing Backend

NotePassing API - Anonymous nearby messaging service.

## Requirements

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) - Python package manager

## Setup

```bash
# Create virtual environment
uv venv --python python3.10

# Install dependencies (including dev)
uv pip install -e ".[dev]"
```

## Run Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_device.py -v

# Run with coverage
uv run pytest tests/ --cov=app --cov-report=html
```

## Start Development Server

```bash
# Start server
uv run python -m app.main

# Or with auto-reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Device Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/device/init` | Initialize/recover device |
| GET | `/api/v1/device/{device_id}?requester_id={id}` | Get device profile |
| PUT | `/api/v1/device/{device_id}` | Update device profile |

### Example Requests

```bash
# Initialize device
curl -X POST http://localhost:8000/api/v1/device/init \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "550e8400e29b41d4a716446655440000",
    "nickname": "Test User",
    "tags": ["test"],
    "profile": "Hello world"
  }'

# Get device profile
curl "http://localhost:8000/api/v1/device/550e8400e29b41d4a716446655440000?requester_id=550e8400e29b41d4a716446655440000"

# Update device
curl -X PUT http://localhost:8000/api/v1/device/550e8400e29b41d4a716446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "nickname": "Updated Name",
    "is_anonymous": true
  }'
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
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── routers/             # API routes
│   └── utils/               # Utilities
├── tests/                   # Test files
└── pyproject.toml           # Project config
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/notepassing
SECRET_KEY=your-secret-key
DEBUG=true
```
