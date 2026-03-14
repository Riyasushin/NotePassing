# End-to-End Testing Guide

## Quick Start

```bash
# 1. Start the server
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Run E2E tests in another terminal
uv run python tests/e2e/e2e_test.py
```

## Manual Testing with curl

See full examples in the sections below.

## WebSocket Testing

### Using wscat

```bash
npm install -g wscat
wscat -c "ws://localhost:8000/api/v1/ws?device_id=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
> {"action": "ping"}
```

## Running Automated E2E Tests

```bash
uv run python tests/e2e/e2e_test.py --verbose
```
