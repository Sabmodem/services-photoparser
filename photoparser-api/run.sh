#!/bin/bash
set -e

# Ensure DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    # Try to load from .env if exists
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    else
        echo "⚠️  DATABASE_URL not set. Using default from database.py"
    fi
fi

# Run migrations before starting the server
if [ -d "migrations" ] && [ -f "migrations/env.py" ]; then
    echo "🔧 Running database migrations..."
    
    # Check if running in Docker (use python directly)
    if [ -n "$DOCKER_ENV" ]; then
        # Inside Docker, run migrations via nix-shell
        nix-shell -p python3Packages.alembic \
          python3Packages.sqlalchemy \
          python3Packages.pg8000 \
          python3Packages.psycopg2 \
          --run "cd $(dirname $0) && alembic upgrade head"
    else
        # Local development with nix-shell
        nix-shell -p python3Packages.alembic \
          python3Packages.sqlalchemy \
          python3Packages.pg8000 \
          python3Packages.psycopg2 \
          --run "cd $(dirname $0) && alembic upgrade head"
    fi
    echo "✅ Database migrations completed"
fi

# Start the server
echo "🚀 Starting PhotoParser API server..."
uvicorn --host 0.0.0.0 --port 8000 main:app --root-path /api/photoparser --reload