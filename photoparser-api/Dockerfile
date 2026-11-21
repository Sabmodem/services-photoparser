# ============================================
# Stage 1: Build stage
# ============================================
FROM python:3.11-slim as builder

WORKDIR /build

# Copy only requirements first for better layer caching
COPY requirements.txt .
# Install runtime dependencies + migration dependencies (pg8000 for sync DB access)
RUN pip install --no-cache-dir --user -r requirements.txt && \
    pip install --no-cache-dir --user pg8000

# ============================================
# Stage 2: Production stage
# ============================================
FROM python:3.11-slim

LABEL maintainer="PhotoParser Team"
LABEL description="PhotoParser API Service"

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appgroup . /app

# Set PATH to include user-local packages
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/photoparser/docs')" || exit 1

# Run entrypoint
CMD ["/bin/sh", "./run.sh"]