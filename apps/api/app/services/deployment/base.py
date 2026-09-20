from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.services.deployment.models import (
    ReleaseCandidateData,
    CanaryDeploymentData,
    CanaryVerificationData,
    ProductionDeploymentData,
)


class BaseDeploymentProvider(ABC):
    """
    Abstract base class for deployment providers (Mock, Production).
    Strictly forbids arbitrary shell execution or direct credential exposure.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier name of the deployment provider."""
        pass

    @abstractmethod
    def create_release_candidate(self, candidate_data: ReleaseCandidateData) -> Dict[str, Any]:
        """Prepares release candidate metadata and verifies provider readiness."""
        pass

    @abstractmethod
    def deploy_canary(self, candidate: ReleaseCandidateData, traffic_percentage: int = 5) -> CanaryDeploymentData:
        """Deploys canary instance with traffic percentage (1-10%)."""
        pass

    @abstractmethod
    def verify_canary(self, canary_id: str) -> CanaryVerificationData:
        """Evaluates canary telemetry against baseline performance."""
        pass

    @abstractmethod
    def promote_full(self, candidate: ReleaseCandidateData) -> ProductionDeploymentData:
        """Promotes canary to 100% full production deployment via controlled adapter."""
        pass

    @abstractmethod
    def rollback_release(self, candidate: ReleaseCandidateData) -> Dict[str, Any]:
        """Rolls back production deployment to previous verified release candidate."""
        pass

    @abstractmethod
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Retrieves active deployment status."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Health status check for deployment provider connection."""
        pass
