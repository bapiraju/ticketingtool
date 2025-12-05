FROM python:3.12-slim

# Set labels for container metadata
LABEL maintainer="Your Name" \
      description="Ticketing Tool - A ticketing system built on FastAPI" \
      version="0.1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO

# Install uv for faster dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create application working directory
WORKDIR /app

# Copy only dependency files first (for better layer caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies in a virtual environment
RUN uv sync --frozen --no-cache

# Copy application code
COPY app/ ./app/
COPY serve.py .
COPY .env.example .env

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["/app/.venv/bin/python", "serve.py"]