import logging
from typing import Dict, Any, Optional
from app.services.staging.base import BaseStagingProvider
from app.services.staging.docker_provider import DockerStagingProvider

logger = logging.getLogger("devoncall.staging.cleanup")

STAGING_RETENTION_MINUTES = 60


class StagingCleanupManager:
    """
    Manages cleanup of staging deployment containers, networks, and resources.
    Prevents orphaned containers and enforces retention bounds.
    """

    def __init__(self, provider: Optional[BaseStagingProvider] = None):
        self.provider = provider or DockerStagingProvider()

    async def cleanup_deployment(self, deployment_id: str) -> bool:
        if not deployment_id:
            return False

        logger.info(f"Cleaning up staging deployment '{deployment_id}'...")
        try:
            success = await self.provider.teardown_staging(deployment_id)
            if success:
                logger.info(f"Staging deployment '{deployment_id}' cleaned up successfully.")
            return success
        except Exception as e:
            logger.error(f"Failed to cleanup staging deployment '{deployment_id}': {e}")
            return False
