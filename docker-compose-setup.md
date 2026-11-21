# Docker Compose Setup Guide for PhotoParser API

## Overview

This document provides a comprehensive guide for setting up, running, and troubleshooting the PhotoParser API using Docker Compose. The setup includes PostgreSQL, Redis, and the FastAPI backend container.

---

## Quick Start

### Start All Services
```bash
cd /home/sabmodem/projects/services-photoparser
docker-compose up -d
```

### Check Status
```bash
docker-compose ps
```

### View Logs
```bash
docker-compose logs -f api
docker-compose logs -f db
docker-compose logs -f redis
```

### Stop Services
```bash
docker-compose down
```

### Stop and Remove Volumes (Clean Slate)
```bash
docker-compose down -v
```

---

## Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `photoparser_api` | `services-photoparser-api` | 8000 | FastAPI backend |
| `photoparser_db` | `postgres:16-alpine` | 5432 | PostgreSQL database |
| `photoparser_redis` | `redis:7-alpine` | 6379 | Redis cache |

---

## Database Configuration

### Connection Details
- **Host**: `db` (from within Docker network) or `localhost:5432` (from host)
- **Port**: 5432
- **Database**: `photoparser`
- **User**: `photoparserx`
- **Password**: `XtCBlt3QcJ?L\9`

### Connection Strings
```bash
# For the API (asyncpg driver)
DATABASE_URL=postgresql+asyncpg://photoparserx:XtCBlt3QcJ%3FL%5C9@db:5432/photoparser

# For migrations (pg8000 driver)
DATABASE_URL=postgresql+pg8000://photoparserx:XtCBlt3QcJ%3FL%5C9@db:5432/photoparser

# For local development (localhost)
DATABASE_URL=postgresql+asyncpg://photoparserx:XtCBlt3QcJ%3FL%5C9@localhost:5432/photoparser
```

---

## Migration Commands

### Apply Migrations
```bash
# From within container
docker-compose exec api alembic upgrade head

# View migration history
docker-compose exec api alembic history

# Check current version
docker-compose exec api alembic current
```

### Generate New Migration (Local Development)
```bash
# From host using nix-shell
nix develop -c "export DATABASE_URL='postgresql+pg8000://photoparserx:XtCBlt3QcJ%3FL%5C9@localhost:5432/photoparser' && \
  cd photoparser-api && \
  alembic revision --autogenerate -m 'add new table'"
```

---

## API Endpoints

### Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Health Check
```bash
curl http://localhost:8000/api/photoparser/health
```

### Main Endpoints
- `GET /search_query/` - List all search queries
- `POST /search_query/` - Create new search query
- `GET /search_query/{search_query_id}` - Get specific query
- `GET /search_query/{search_query_id}/status` - Get query status
- `GET /search_query/{search_query_id}/search_results` - Get query results
- `GET /search_results/` - List all search results
- `GET /search_results/{search_result_id}` - Get specific result

---

## Troubleshooting

### Issue: Container Won't Start
**Solution**: Check logs for errors
```bash
docker-compose logs api
```

### Issue: Database Connection Refused
**Solution**: Ensure database container is healthy
```bash
docker-compose ps  # Check if db shows "(healthy)"
docker-compose logs db  # Check for DB startup errors
```

### Issue: ModuleNotFoundError
**Common Causes**:
1. Missing dependencies in `requirements.txt`
2. Driver mismatch (asyncpg vs pg8000)

**Fix**: Update `requirements.txt` and rebuild
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue: Migration Fails with "Module not found"
**Cause**: Using wrong driver (psycopg2 vs pg8000)
**Fix**: Check `migrations/env.py` uses `pg8000`

### Issue: nix-shell: not found in Container
**Cause**: nix-shell is only available on host system
**Fix**: Use `alembic` from PATH (installed in Docker image)

### Issue: Database Tables Don't Exist
**Solution**: Run migrations
```bash
docker-compose exec api alembic upgrade head
```

### Issue: CORS Errors
**Solution**: Add CORS headers to API (configure in `main.py`)

---

## Development Workflow

### Option 1: Full Docker Stack (Recommended for Testing)
```bash
# Start services
docker-compose up -d

# Access API
curl http://localhost:8000/search_query/

# Run migrations if needed
docker-compose exec api alembic upgrade head
```

### Option 2: Nix Shell + Local Database (Recommended for Coding)
```bash
# Enter development shell
nix develop

# Run API server
cd photoparser-api && python run.sh

# Generate migrations
export DATABASE_URL='postgresql+pg8000://photoparserx:XtCBlt3QcJ%3FL%5C9@localhost:5432/photoparser'
alembic revision --autogenerate -m "description"
```

### Option 3: Hybrid Approach
- **Database**: Use Docker Compose PostgreSQL
- **API**: Run locally with nix-shell
- **Redis**: Use Docker Compose Redis

```bash
# Start DB and Redis
docker-compose up -d db redis

# Run API locally
nix develop -c cd photoparser-api && python run.sh
```

---

## File Structure

```
photoparser-api/
├── Dockerfile              # Multi-stage build (builder + production)
├── docker-compose.yml      # Service definitions
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic configuration
├── .env.example            # Environment variable template
├── database.py             # Database connection setup
├── models.py               # SQLAlchemy models
├── crud.py                 # Database operations
├── run.sh                  # Startup script (runs migrations)
├── migrations/
│   ├── env.py              # Migration environment
│   └── versions/           # Migration scripts
└── main.py                 # FastAPI application entry point
```

---

## Dockerfile Best Practices

### Multi-Stage Build
1. **Builder Stage**: Install dependencies
2. **Production Stage**: Copy only necessary files, create non-root user

### Security
- Runs as non-root user (`appuser`)
- No shell tools in production image
- Minimal base image (`python:3.11-slim`)

### Optimization
- Separate `requirements.txt` copy for layer caching
- Copy installed packages from builder stage
- Health check included

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Local container URL |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `ENV` | Environment mode | `development` |

---

## Git Workflow

### Branch Management
```bash
# Create feature branch
git checkout -b feature/new-feature

# Commit changes
git add . && git commit -m "feat: add new feature"

# Push and merge
git push origin feature/new-feature
```

### Commit Message Convention
```
feat: New feature
fix: Bug fix
docs: Documentation
chore: Maintenance
```

---

## Common Pitfalls

### 1. Using Wrong Database URL
```python
# ❌ WRONG: Hardcoded remote database
SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://user:pass@remote:5432/db"

# ✅ CORRECT: Use environment variable
import os
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://photoparserx:pass@db:5432/photoparser"
)
```

### 2. Missing Driver for Migrations
```python
# ❌ WRONG: Using psycopg2 for migrations
# (asyncpg driver not available for sync SQLAlchemy)

# ✅ CORRECT: Use pg8000 for migrations
sync_url = url.replace("postgresql+asyncpg", "postgresql+pg8000")
```

### 3. Trying to Use nix-shell in Container
```bash
# ❌ WRONG: nix-shell not available in Docker
docker-compose exec api nix-shell -p alembic

# ✅ CORRECT: alembic installed in image
docker-compose exec api alembic upgrade head
```

### 4. Database Tables Not Created
```bash
# ❌ WRONG: Assuming create_all() creates tables

# ✅ CORRECT: Run migrations
docker-compose exec api alembic upgrade head
```

---

## Dependencies

### Runtime Dependencies (`requirements.txt`)
```
fastapi
sqlalchemy[asyncio]  # Includes asyncio support
uvicorn[standard]    # Includes reload support
redis
rq
asyncpg              # PostgreSQL async driver
httpx
alembic
greenlet             # Required for SQLAlchemy asyncio
pg8000               # PostgreSQL sync driver (for migrations)
```

### Development Dependencies (nix-shell)
```nix
python3Packages.alembic
python3Packages.sqlalchemy
python3Packages.asyncpg
python3Packages.pg8000
python3Packages.redis
python3Packages.rq
```

---

## Performance Tips

1. **Use `--no-cache-dir`** in pip install for smaller images
2. **Multi-stage builds** for faster layer caching
3. **`.dockerignore`** to exclude unnecessary files
4. **Health checks** for automatic restart on failure
5. **Volume mounting** for development: `-v ./photoparser-api:/app`

---

## Production Considerations

### Environment-Specific Configuration
```bash
# Production .env
DATABASE_URL=postgresql+asyncpg://prod_user:prod_pass@prod-db:5432/photoparser
REDIS_URL=rediss://prod-redis:6379/0
```

### Security Checklist
- [x] Non-root user in container
- [x] No sensitive data in image
- [x] Environment variables for secrets
- [x] HTTPS in production (nginx reverse proxy)
- [x] Health check enabled
- [ ] Rate limiting configured
- [ ] CORS properly configured

---

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy AsyncIO](https://docs.sqlalchemy.org/en/20/orm/alembic.html)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Redis Docker Image](https://hub.docker.com/_/redis)

---

## Last Updated
2024-11-20

---

## Quick Reference Card

```bash
# START
docker-compose up -d

# STATUS
docker-compose ps

# LOGS
docker-compose logs -f api

# MIGRATIONS
docker-compose exec api alembic upgrade head

# API TEST
curl http://localhost:8000/search_query/

# DOCS
open http://localhost:8000/docs

# STOP
docker-compose down

# CLEAN SLATE
docker-compose down -v && docker-compose up -d
```
