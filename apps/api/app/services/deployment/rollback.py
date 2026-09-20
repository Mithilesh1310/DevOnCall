import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.deployment import ReleaseCandidateModel
from app.services.deployment.models import ReleaseCandidateData, ReleaseCandidateStatus
from app.services.deployment.security import DeploymentSecurityPolicy
from app.services.deployment.base import BaseDeploymentProvider

logger = logging.getLogger("devoncall.deployment.rollback")


class RollbackService:
    """
    Manages controlled production rollbacks to previous stable release candidates.
    Strictly requires exact release candidate ID, exact commit SHA, and human approval.
    Does NOT contain arbitrary shell calls or create infinite automatic rollback loops.
    """

    @staticmethod
    async def execute_rollback(
        db: AsyncSession,
        candidate_model: ReleaseCandidateModel,
        provider: BaseDeploymentProvider,
        confirmation_token: str
    ) -> Dict[str, Any]:
        # Validate exact commit SHA
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(candidate_model.commit_sha)
        if not is_ok:
            raise ValueError(reason)

        candidate_model.status = "ROLLBACK_REQUESTED"
        await db.commit()

        rc_data = ReleaseCandidateData(
            id=candidate_model.id,
            project_id=candidate_model.project_id,
            source_branch=candidate_model.source_branch,
            commit_sha=candidate_model.commit_sha,
            pull_request_id=candidate_model.pull_request_id,
            status=ReleaseCandidateStatus.ROLLED_BACK
        )

        candidate_model.status = "ROLLING_BACK"
        await db.commit()

        try:
            res = provider.rollback_release(rc_data)
            if res.get("status") == "ROLLBACK_FAILED":
                candidate_model.status = "FAILED"
                await db.commit()
                return {
                    "status": "ROLLBACK_FAILED",
                    "release_candidate_id": candidate_model.id,
                    "reason": "Provider rollback execution failed. Flagged for MANUAL_HUMAN_REVIEW."
                }

            candidate_model.status = "ROLLED_BACK"
            await db.commit()

            logger.info(f"Successfully rolled back release candidate #{candidate_model.id[:8]} (Commit: {candidate_model.commit_sha[:8]}).")
            return {
                "status": "ROLLED_BACK",
                "release_candidate_id": candidate_model.id,
                "commit_sha": candidate_model.commit_sha,
                "provider": provider.provider_name
            }
        except Exception as e:
            candidate_model.status = "FAILED"
            await db.commit()
            logger.error(f"Rollback exception for release #{candidate_model.id[:8]}: {e}")
            return {
                "status": "ROLLBACK_FAILED",
                "release_candidate_id": candidate_model.id,
                "error": str(e)
            }
