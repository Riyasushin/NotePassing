#!/bin/bash
set -e

echo "🚀 Setting up NotePassing Server..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "✅ uv is installed"

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Create .env if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
fi

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d postgres redis || echo "⚠️  Docker services not started. Please start them manually."

# Wait for services
sleep 3

# Run migrations
echo "🗄️  Running database migrations..."
uv run alembic upgrade head || echo "⚠️  Migrations failed. Please check your database connection."

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your configuration"
echo "  2. Run 'make run' to start the server"
echo "  3. Run 'make test' to run tests"
