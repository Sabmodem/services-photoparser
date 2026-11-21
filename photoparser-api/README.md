# PhotoParser API

FastAPI backend service for PhotoParser.

## Quick Start

### Development

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or using direct python run
cd photoparser-api
python run.sh
```

### Database Migrations

The API uses **Alembic** for database migrations.

#### Using the migration script (recommended):

```bash
# Navigate to API directory
cd photoparser-api

# Upgrade to latest migration
./scripts/migrate.sh upgrade

# Check current migration status
./scripts/migrate.sh current

# View migration history
./scripts/migrate.sh history

# Generate new migration (requires DATABASE_URL set)
# This will automatically detect changes in models.py
export DATABASE_URL="postgresql+pg8000://photoparserx:yourpassword@localhost:5432/photoparser"
./scripts/migrate.sh generate "add user preferences table"
```

#### Using Alembic directly:

```bash
# Using nix-shell
nix-shell -p python3Packages.alembic python3Packages.sqlalchemy python3Packages.psycopg2 \
  --run "cd photoparser-api && alembic upgrade head"

# Or set DATABASE_URL and use autogenerate
export DATABASE_URL="postgresql+pg8000://photoparserx:yourpassword@localhost:5432/photoparser"
alembic revision --autogenerate -m "your migration message"
```

#### Common migration commands:

| Command | Description |
|---------|-------------|
| `./scripts/migrate.sh upgrade` | Upgrade to latest migration |
| `./scripts/migrate.sh upgrade <revision>` | Upgrade to specific revision |
| `./scripts/migrate.sh downgrade` | Revert last migration |
| `./scripts/migrate.sh downgrade <n>` | Revert last n migrations |
| `./scripts/migrate.sh current` | Show current revision |
| `./scripts/migrate.sh history` | Show migration history |
| `./scripts/migrate.sh generate "message"` | Generate new migration |

## Database Setup

### Environment Variables

```bash
# PostgreSQL connection (used by both app and migrations)
DATABASE_URL=postgresql+pg8000://photoparserx:yourpassword@localhost:5432/photoparser

# Redis connection (for RQ job queue)
REDIS_URL=redis://localhost:6379/0
```

### Creating the database

```bash
# Create database (if not using Docker Compose)
createdb -U photoparserx photoparser

# Or with Docker Compose
docker-compose up -d db
./scripts/migrate.sh upgrade
```

## Architecture

### Components

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM with async support
- **asyncpg** - Async PostgreSQL driver (for app)
- **pg8000** - Sync PostgreSQL driver (for migrations)
- **RQ + Redis** - Background job queue
- **Alembic** - Database migrations

### Directory Structure

```
photoparser-api/
├── main.py              # FastAPI application
├── database.py          # Database connection setup
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── crud.py              # CRUD operations
├── search.py            # Search background tasks
├── alembic.ini          # Alembic configuration
├── migrations/          # Migration scripts
│   ├── env.py          # Alembic environment
│   ├── script.py.mako  # Migration template
│   └── versions/       # Migration files
├── scripts/
│   └── migrate.sh      # Migration helper script
├── Dockerfile          # Production container
├── run.sh              # Development entrypoint
└── pyproject.toml      # Python dependencies
```

## Development Guidelines

### Adding a new model

1. Add model to `models.py`
2. Generate migration:
   ```bash
   export DATABASE_URL="postgresql+pg8000://..."
   ./scripts/migrate.sh generate "add user model"
   ```
3. Review the generated migration in `migrations/versions/`
4. Update migration if needed
5. Apply migration:
   ```bash
   ./scripts/migrate.sh upgrade
   ```

### Adding a new API endpoint

1. Create Pydantic schemas in `schemas.py`
2. Add CRUD operations in `crud.py`
3. Define routes in `main.py`
4. Test with `curl` or browser at `http://localhost:8000/api/photoparser/docs`

## Troubleshooting

### Migration fails with "connection timed out"

- Ensure PostgreSQL is running: `docker-compose up -d db`
- Check connection string in `database.py` or `DATABASE_URL`
- Verify firewall allows connection to port 5432

### "No module named asyncpg"

- Install dependencies: `pip install -r requirements.txt`
- Or use nix-shell: `nix-shell --run "cd photoparser-api && python run.sh"`

### Migration autogenerate not detecting changes

- Ensure `DATABASE_URL` is set
- Models must be importable from `migrations/env.py`
- Check `database.py` is in the same directory as `env.py`
