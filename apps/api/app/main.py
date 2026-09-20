import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.v1.router import api_router
from app.api.v1.endpoints.health import router as health_router
from app.db.base import Base
from app.db.session import engine
from app.services.redis import redis_service

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("devoncall.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing DevOnCall API application services...")
    # Initialize database tables for local execution/testing if Alembic hasn't run
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized.")
    except Exception as e:
        logger.warning(f"Database schema initialization deferred/skipped: {e}")

    yield

    logger.info("Shutting down DevOnCall API services...")
    await redis_service.close()
    await engine.dispose()
    logger.info("Shutdown complete.")

app = FastAPI(
    title="DevOnCall API",
    description="AI Production Software Engineer - Foundation API",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "service": settings.SERVICE_NAME}
    )

# Root Health Check endpoint GET /health
app.include_router(health_router)

# Include v1 API Router (/api/v1/...)
app.include_router(api_router)
