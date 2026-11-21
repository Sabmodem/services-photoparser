FROM python:3.11-slim

LABEL maintainer="PhotoParser Team"
LABEL description="PhotoParser API Service"

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Install uv for fast pip-compatible installs
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /usr/local/bin/uv

# Install dependencies using uv pip (fast, lockfile-compatible)
COPY pyproject.toml uv.lock ./
RUN uv export --no-dev --no-hashes --output-file requirements.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir alembic

# Copy application code
COPY --chown=appuser:appgroup . /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/photoparser/docs')" || exit 1

# Start the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--root-path", "/api/photoparser"]
