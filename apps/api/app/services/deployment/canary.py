import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.deployment import CanaryDeploymentModel, ReleaseCandidateModel
from app.services.deployment.models import CanaryDeploymentData, CanaryStatus
from app.services.deployment.security import DeploymentSecurityPolicy
from app.services.deployment.base import BaseDeploymentProvider

logger = logging.getLogger("devoncall.deployment.canary")


class CanaryManager:
    """
    Manages canary deployment execution and database record lifecycle.
    Strictly enforces canary traffic percentage bounds (1% to 10%).
    """

    @staticmethod
    async def deploy_canary(
        db: AsyncSession,
        candidate_model: ReleaseCandidateModel,
        provider: BaseDeploymentProvider,
        traffic_percentage: int = 5
    ) -> CanaryDeploymentModel:
        # Validate canary traffic
        is_ok, reason = DeploymentSecurityPolicy.validate_canary_traffic(traffic_percentage)
        if not is_ok:
            raise ValueError(reason)

        rc_data = candidate_model.to_domain() if hasattr(candidate_model, 'to_domain') else None
        if not rc_data:
            from app.services.deployment.models import ReleaseCandidateData
            rc_data = ReleaseCandidateData(
                id=candidate_model.id,
                project_id=candidate_model.project_id,
                source_branch=candidate_model.source_branch,
                commit_sha=candidate_model.commit_sha,
                pull_request_id=candidate_model.pull_request_id
            )

        # Provider deploys canary
        canary_data = provider.deploy_canary(rc_data, traffic_percentage=traffic_percentage)

        canary_model = CanaryDeploymentModel(
            release_candidate_id=candidate_model.id,
            commit_sha=candidate_model.commit_sha,
            provider=provider.provider_name,
            status=canary_data.status.value if hasattr(canary_data.status, 'value') else canary_data.status,
            traffic_percentage=traffic_percentage,
            deployment_url=canary_data.deployment_url,
            error=canary_data.error,
            metadata_payload=canary_data.metadata_payload
        )

        db.add(canary_model)
        await db.commit()
        await db.refresh(canary_model)
        logger.info(f"Deployed Canary #{canary_model.id[:8]} for Release Candidate #{candidate_model.id[:8]} (Traffic: {traffic_percentage}%)")
        return canary_model
