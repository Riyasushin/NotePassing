# NotePassing Server - Quick Start Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

## 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 2. Setup Project

```bash
cd notepassing-server

# Run setup script
./scripts/setup.sh

# Or manually:
uv sync                    # Install dependencies
uv sync --extra dev        # Install with dev dependencies
cp .env.example .env       # Create env file
```

## 3. Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Or use Make
make docker-up
```

## 4. Run Migrations

```bash
# Create initial migration
uv run alembic revision --autogenerate -m "Initial migration"

# Run migrations
uv run alembic upgrade head

# Or use Make
make migrate
```

## 5. Start Server

```bash
# Development with auto-reload
uv run uvicorn app.main:app --reload

# Or use Make
make run-dev
```

Server will be available at: http://localhost:8000

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 6. Run Tests

```bash
# All tests
uv run pytest

# Specific categories
uv run pytest -m unit              # Unit tests
uv run pytest -m integration       # Integration tests
uv run pytest -m e2e               # E2E tests
uv run pytest -m p0                # P0 priority tests

# With coverage
uv run pytest --cov=app --cov-report=html

# Or use Make
make test
make test-unit
make coverage
```

## Common Commands

```bash
# Code formatting
make format              # Format all code
make lint                # Run linters
make check               # Run all checks

# Database
make migrate             # Run migrations
make migrate-create      # Create new migration

# Docker
make docker-up           # Start services
make docker-down         # Stop services
make docker-logs         # View logs

# Cleaning
make clean               # Clean cache files
make reset               # Full reset
```

## Environment Variables

Edit `.env` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/notepassing

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here

# Debug
DEBUG=true
```

## Project Structure

```
.
├── app/                    # Main application
│   ├── main.py            # FastAPI entry
│   ├── config.py          # Settings
│   ├── database.py        # DB connection
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── routers/           # API routes
│   └── utils/             # Utilities
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # E2E tests
├── alembic/                # DB migrations
├── scripts/                # Helper scripts
├── pyproject.toml          # Project config
├── Makefile               # Common commands
└── docker-compose.yml     # Services config
```

## Troubleshooting

### Port already in use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uv run uvicorn app.main:app --port 8001
```

### Database connection failed

```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart services
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Import errors

```bash
# Ensure you're in the backend directory
cd notepassing-server

# Reinstall dependencies
uv sync --extra dev
```

## Next Steps

1. Read [API Documentation](http://localhost:8000/docs)
2. Check [Test README](tests/README.md)
3. Review [Implementation Plan](../documents/second_design/server_implementation_plan.md)

## Support

For issues or questions, please refer to:
- API Contract: `unified_api_contract_v2.md`
- MVP Design: `MVP_V2_0314.md`
- Test List: `server_test_list.md`
