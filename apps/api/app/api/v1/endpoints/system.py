import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.services.integrations.registry import IntegrationRegistry, IntegrationStatus

logger = logging.getLogger("devoncall.endpoints.system")
router = APIRouter()


@router.get("/integrations")
async def get_system_integrations() -> Dict[str, Any]:
    """
    Audits all 10 core DevOnCall system integrations against real external infrastructure.
    Truthfully reports REAL, NOT_CONFIGURED, BLOCKED, or ERROR status.
    NEVER fakes integration status.
    """
    return await IntegrationRegistry.check_all()


@router.post("/integrations/{name}/test")
async def test_single_integration(name: str) -> Dict[str, Any]:
    """
    Executes a real connection test for a specific integration by name.
    """
    target = name.upper().strip()

    check_map = {
        "GITHUB": IntegrationRegistry.check_github,
        "POSTGRESQL": IntegrationRegistry.check_postgresql,
        "REDIS": IntegrationRegistry.check_redis,
        "DOCKER": IntegrationRegistry.check_docker,
        "PLAYWRIGHT": IntegrationRegistry.check_playwright,
        "SENTRY": IntegrationRegistry.check_sentry,
        "WHATSAPP": IntegrationRegistry.check_whatsapp,
        "STAGING_DEPLOYMENT": IntegrationRegistry.check_staging_deployment,
        "OBSERVABILITY": IntegrationRegistry.check_observability,
        "PRODUCTION_DEPLOYMENT": IntegrationRegistry.check_production_deployment,
    }

    if target not in check_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{name}' not found. Supported integrations: {list(check_map.keys())}",
        )

    res = await check_map[target]()
    return res.to_dict()
