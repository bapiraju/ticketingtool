# ticketingtool
A ticketing tool for personal use built on FastAPI and hopefully with a Good UI with JS

## Directory Organization

```
ticketingtool/
├── app/                          # Main application package
│   ├── core/                     # Core application utilities
│   │   ├── __init__.py          # Exports core modules
│   │   ├── config.py            # Configuration management (LogLevel, LogConfig, AppConfig)
│   │   └── logging.py           # Logging setup (Loguru + stdlib interception)
│   │
│   ├── api/                      # API and routes
│   │   ├── __init__.py          # Exports api_router
│   │   └── routes/              # Route modules (grouped by functionality)
│   │       ├── __init__.py      # Combines all routers
│   │       ├── health.py        # Health check endpoints
│   │       └── items.py         # Item management endpoints
│   │
│   ├── models/                   # Database models (ORM, SQLAlchemy, etc.)
│   │   └── __init__.py
│   │
│   ├── schemas/                  # Pydantic schemas for request/response validation
│   │   └── __init__.py
│   │
│   ├── __init__.py              # App package init
│   └── main.py                  # FastAPI application factory
│
├── logs/                         # Application logs (generated at runtime)
│
├── serve.py                      # Server entry point (run with: python serve.py)
├── pyproject.toml               # Project dependencies
├── .env                         # Environment variables (create from .env.example)
├── .env.example                 # Example environment file
└── README.md                    # Project documentation
```

## Module Breakdown

### `app/core/` - Core Application
- **Purpose**: Centralized configuration and logging
- **config.py**: 
  - `LogLevel` enum: Type-safe logging levels
  - `LogConfig`: Logging configuration from environment
  - `AppConfig`: Application configuration from environment
- **logging.py**:
  - `InterceptHandler`: Routes stdlib logging to Loguru
  - `setup_logging()`: Initializes the logging system

### `app/api/` - API Routes
- **Purpose**: All HTTP endpoints organized by functionality
- **routes/health.py**: Health check endpoints (`/health/`, `/health/live`, `/health/ready`)
- **routes/items.py**: Item management endpoints (`/items/`, `/items/{item_id}`)
- **routes/__init__.py**: Combines all route modules into a single `api_router`

### `app/models/` - Database Models
- **Purpose**: ORM models (SQLAlchemy, Tortoise-ORM, etc.)
- Ready for future database integration

### `app/schemas/` - Pydantic Schemas
- **Purpose**: Request/response validation schemas
- Separate from models for better organization
- Example: `ItemCreate`, `ItemResponse`, `UserUpdate`

## Adding New Routes

To add a new route group (e.g., for Users):

1. **Create a new route file** `app/api/routes/users.py`:
```python
from fastapi import APIRouter
from loguru import logger

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
def list_users():
    logger.info("GET /users - Listing all users")
    return {"users": []}
```

2. **Import it** in `app/api/routes/__init__.py`:
```python
from app.api.routes import health, items, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(items.router)
api_router.include_router(users.router)  # Add this
```

## Logging Configuration

All logging is controlled via `.env`:

```env
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE_PATH=logs/application.log
LOG_FILE_ROTATION=500 MB           # Rotate when file reaches 500MB
LOG_FILE_RETENTION=7 days          # Keep logs for 7 days
LOG_FILE_COMPRESSION=zip           # Compress rotated logs
```

### Using Logger in Code

```python
from loguru import logger

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Error with traceback")
```
## Environment Variables

Configure via `.env` file or docker-compose environment:

```env
# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE_PATH=logs/application.log
LOG_FILE_ROTATION=500 MB
LOG_FILE_RETENTION=7 days
LOG_FILE_COMPRESSION=zip

# Application
HOST=0.0.0.0
PORT=8000
RELOAD=True                       # False in production
```

## Running the Application

```bash
# Start the server
python serve.py

# The server runs on http://0.0.0.0:8000
# Uvicorn logs are captured by our logging system
# All logs appear in both console and logs/application.log
```

### Docker Setup Guide

#### Files Overview

- **Dockerfile**: Development image with reload enabled
- **Dockerfile.prod**: Production-optimized multi-stage build
- **docker-compose.yml**: Development environment setup
- **docker-compose.prod.yml**: Production environment setup
- **.dockerignore**: Excludes unnecessary files from Docker build context

#### Quick Start - Development
```bash
# Start the application in development mode
docker-compose up

# Build fresh image and run
docker-compose up --build

# Run in background
docker-compose up -d

# Stop the application
docker-compose down

# View logs
docker-compose logs -f app
```

The app will be available at `http://localhost:8000`

### Build and Run Manually

```bash
# Build the development image
docker build -t ticketingtool:dev .

# Run the container
docker run -p 8000:8000 \
  -e LOG_LEVEL=DEBUG \
  -v $(pwd):/app \
  --name ticketingtool-dev \
  ticketingtool:dev

# Run in background
docker run -d -p 8000:8000 \
  -e LOG_LEVEL=DEBUG \
  -v $(pwd):/app \
  --name ticketingtool-dev \
  ticketingtool:dev
```

### Production Build

#### Build and Run Production Image

```bash
# Build the production image
docker build -t ticketingtool:prod -f Dockerfile.prod .

# Run the production container
docker run -d -p 8000:8000 \
  -e LOG_LEVEL=INFO \
  -v ticketingtool_logs:/app/logs \
  --restart always \
  --name ticketingtool-prod \
  ticketingtool:prod
```

#### Using Production Docker Compose

```bash
# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f app

# Stop production stack
docker-compose -f docker-compose.prod.yml down
```
### Pushing to Registry

```bash
# Tag for registry
docker tag ticketingtool:prod bapiraju/ticketingtool:0.1.0

# Push to registry
docker push bapiraju/ticketingtool:0.1.0
```


### View Logs

```bash
# Development
docker-compose logs -f app

# Production
docker-compose -f docker-compose.prod.yml logs -f app

# Specific container
docker logs -f ticketingtool-dev
```

## Health Check

Extend live and ready probes to meet the latency requirements:
- Health should return if the application is alive.
- Ready should return if the application is ready to serve traffic.

```bash
# Manual health check
curl http://localhost:8000/health
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

## Troubleshooting

### Check if port is already in use
```
lsof -i :8000  # On Unix/Mac
netstat -ano | findstr :8000  # On Windows
```

## Best Practices

✅ **Development**: Use `docker-compose up` for quick iteration  
✅ **Production**: Use `Dockerfile.prod` multi-stage build for smaller images  
✅ **Health Checks**: Always include health endpoints for container orchestration  
✅ **Non-root User**: Production image runs as `appuser` for security  
✅ **Environment Variables**: Configure via .env, not hardcoded  
✅ **Logging**: All logs appear in both console and persistent logs/ directory  
✅ **Volume Mounts**: Development mounts app code for hot-reload  
✅ **Resource Limits**: Add `deploy` section to docker-compose for limits  
Edit `docker-compose.yml` to add resource constraints:

```yaml
services:
  app:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```
