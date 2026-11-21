#!/bin/bash
set -e

# Ensure DATABASE_URL is set (use pg8000 driver for migrations)
export DATABASE_URL="${DATABASE_URL:-postgresql+pg8000://photoparserx:XtCBlt3QcJ%3FL%5C9@db:5432/photoparser}"

# Run migrations before starting the server
if [ -d "migrations" ] && [ -f "migrations/env.py" ]; then
    echo "🔧 Running database migrations..."
    
    # Use alembic from PATH (installed in Docker builder stage)
    if command -v alembic &> /dev/null; then
        cd /app && alembic upgrade head
    else
        echo "⚠️  alembic not found, skipping migrations"
    fi
    echo "✅ Database migrations completed"
fi

# Start the server
echo "🚀 Starting PhotoParser API server..."
uvicorn --host 0.0.0.0 --port 8000 main:app --root-path /api/photoparser --reload