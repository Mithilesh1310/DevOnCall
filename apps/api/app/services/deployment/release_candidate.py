import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.deployment import ReleaseCandidateModel
from app.services.deployment.models import ReleaseCandidateData, ReleaseCandidateStatus
from app.services.deployment.security import DeploymentSecurityPolicy
from app.services.deployment.policy import ReleaseCandidatePolicy

logger = logging.getLogger("devoncall.deployment.release_candidate")


class ReleaseCandidateManager:
    """
    Manages release candidate database persistence and state machine transitions.
    Enforces exact 40-character commit SHA validation and staging/PR prerequisites.
    """

    @staticmethod
    async def create_candidate(db: AsyncSession, data: ReleaseCandidateData) -> ReleaseCandidateModel:
        # Exact commit SHA validation
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(data.commit_sha)
        if not is_ok:
            raise ValueError(reason)

        model = ReleaseCandidateModel(
            project_id=data.project_id,
            source_branch=data.source_branch,
            commit_sha=data.commit_sha,
            pull_request_id=data.pull_request_id,
            staging_deployment_id=data.staging_deployment_id,
            staging_verification_status=data.staging_verification_status,
            browser_verification_status=data.browser_verification_status,
            created_by=data.created_by,
            status=ReleaseCandidateStatus.STAGING_PASSED.value if data.staging_verification_status == "PASSED" else ReleaseCandidateStatus.CREATED.value,
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
        logger.info(f"Created Release Candidate #{model.id[:8]} (Commit: {model.commit_sha[:8]}, Status: {model.status})")
        return model

    @staticmethod
    async def get_candidate(db: AsyncSession, candidate_id: str) -> Optional[ReleaseCandidateModel]:
        stmt = select(ReleaseCandidateModel).where(ReleaseCandidateModel.id == candidate_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def update_status(db: AsyncSession, candidate_id: str, new_status: ReleaseCandidateStatus) -> ReleaseCandidateModel:
        model = await ReleaseCandidateManager.get_candidate(db, candidate_id)
        if not model:
            raise ValueError(f"Release candidate '{candidate_id}' not found.")

        model.status = new_status.value if hasattr(new_status, 'value') else new_status
        await db.commit()
        await db.refresh(model)
        logger.info(f"Release Candidate #{model.id[:8]} status updated to {model.status}")
        return model
