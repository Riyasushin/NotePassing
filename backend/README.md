# NotePassing Server

A proximity-based social network backend built with FastAPI.

## Features

- 🔐 **Device-based authentication** - No passwords, device ID is identity
- 📡 **BLE proximity discovery** - Find nearby users via Bluetooth
- 💬 **Proximity messaging** - Chat with nearby users (limited for strangers)
- 👥 **Friend system** - Add friends for unlimited messaging
- 🚀 **Boost notifications** - Get notified when friends are nearby
- 🔒 **Blocking system** - Block unwanted users
- ⚡ **WebSocket real-time** - Instant message delivery

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy (async)
- **Cache**: Redis
- **Migrations**: Alembic
- **Testing**: pytest
- **Package Manager**: uv

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- [uv](https://github.com/astral-sh/uv) installed

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd notepassing-server

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Set up environment variables
cp .env.example .env
# Edit .env with your settings

# Run database migrations
uv run alembic upgrade head

# Start the server
uv run python -m app.main
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test categories
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m e2e

# Run by priority
uv run pytest -m p0
```

### Code Quality

```bash
# Format code
uv run black app tests
uv run isort app tests

# Lint code
uv run ruff check app tests
uv run mypy app

# Run all checks
uv run black --check app tests
uv run ruff check app tests
uv run mypy app
```

### Database Migrations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"

# Run migrations
uv run alembic upgrade head

# Rollback migration
uv run alembic downgrade -1
```

## API Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings
│   ├── database.py          # DB connection
│   ├── exceptions.py        # Custom exceptions
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── routers/             # API routes
│   └── utils/               # Utilities
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── e2e/                 # E2E tests
├── alembic/                 # DB migrations
├── pyproject.toml           # Project config
└── README.md
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+asyncpg://postgres:postgres@localhost:5432/notepassing` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | Secret for token generation | Change in production |
| `DEBUG` | Debug mode | `False` |
| `PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |

## License

MIT
