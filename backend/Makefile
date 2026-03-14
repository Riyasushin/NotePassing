.PHONY: help install dev test test-unit test-integration test-e2e lint format check migrate run clean

# Default target
help:
	@echo "NotePassing Server - Available Commands:"
	@echo ""
	@echo "  make install       - Install dependencies with uv"
	@echo "  make dev           - Install dev dependencies"
	@echo "  make run           - Run the development server"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-e2e      - Run e2e tests only"
	@echo "  make coverage      - Run tests with coverage report"
	@echo "  make lint          - Run linters (ruff, mypy)"
	@echo "  make format        - Format code (black, isort)"
	@echo "  make check         - Run all checks (format, lint, test)"
	@echo "  make migrate       - Run database migrations"
	@echo "  make migrate-create - Create new migration"
	@echo "  make clean         - Clean cache and temp files"
	@echo ""

# Installation
install:
	uv sync

dev:
	uv sync --extra dev

# Development server
run:
	uv run python -m app.main

run-dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testing
test:
	uv run pytest

test-unit:
	uv run pytest -m unit -v

test-integration:
	uv run pytest -m integration -v

test-e2e:
	uv run pytest -m e2e -v

test-p0:
	uv run pytest -m p0 -v

coverage:
	uv run pytest --cov=app --cov-report=term-missing --cov-report=html

coverage-html:
	uv run pytest --cov=app --cov-report=html
	@echo "Coverage report: coverage_html/index.html"

# Code quality
lint:
	uv run ruff check app tests
	uv run mypy app

format:
	uv run black app tests
	uv run isort app tests

format-check:
	uv run black --check app tests
	uv run isort --check-only app tests

check: format-check lint test
	@echo "All checks passed!"

# Database
migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-create:
	@read -p "Enter migration message: " msg; \
	uv run alembic revision --autogenerate -m "$$msg"

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Cleaning
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf coverage_html .coverage 2>/dev/null || true
	@echo "Cleaned!"

# Setup
setup: install migrate
	@echo "Setup complete!"

# Full reset
reset: clean
	rm -rf .venv uv.lock
	@echo "Full reset complete. Run 'make install' to reinstall."
