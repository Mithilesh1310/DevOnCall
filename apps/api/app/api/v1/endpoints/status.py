from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.config import settings
from app.db.session import get_db
from app.services.redis import redis_service
from app.schemas.status import SystemStatusResponse, DatabaseStatus, RedisStatus

router = APIRouter()

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(db: AsyncSession = Depends(get_db)):
    # Check Database connection
    db_connected = False
    db_details = ""
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_connected = True
            db_details = "PostgreSQL database connection verified (SELECT 1 succeeded)"
        else:
            db_details = "PostgreSQL database returned unexpected result"
    except Exception as e:
        db_details = f"PostgreSQL database connection error: {str(e)}"

    # Check Redis connection
    redis_connected, redis_details = await redis_service.check_connection()

    overall_status = "ok" if (db_connected and redis_connected) else "degraded"

    return SystemStatusResponse(
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        status=overall_status,
        database=DatabaseStatus(connected=db_connected, details=db_details),
        redis=RedisStatus(connected=redis_connected, details=redis_details)
    )
