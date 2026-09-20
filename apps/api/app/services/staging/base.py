from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.services.staging.models import StagingDeployment, StagingCheckResult


class BaseStagingProvider(ABC):
    """
    Abstract Base Class for Staging Deployment Providers.
    Isolated execution contracts for staging deployment, health check, and teardown.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the staging provider (e.g. MOCK_STAGING, DOCKER_STAGING)."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider runtime engine is available."""
        pass

    @abstractmethod
    async def deploy_staging(self, deployment: StagingDeployment) -> StagingDeployment:
        """Builds and deploys the staging environment."""
        pass

    @abstractmethod
    async def health_check(self, deployment: StagingDeployment) -> StagingCheckResult:
        """Performs health check on the deployed staging instance."""
        pass

    @abstractmethod
    async def teardown_staging(self, deployment_id: str) -> bool:
        """Tears down containers, networks, and resources allocated for staging."""
        pass
