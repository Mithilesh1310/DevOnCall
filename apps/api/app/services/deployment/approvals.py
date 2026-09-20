import uuid
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.deployment import ProductionApprovalModel
from app.services.deployment.models import ApprovalType, ApprovalDecision, ProductionApprovalData
from app.services.deployment.security import DeploymentSecurityPolicy

logger = logging.getLogger("devoncall.deployment.approvals")

APPROVAL_TOKEN_EXPIRY_MINUTES = 10


class ProductionApprovalManager:
    """
    Manages human approvals for production release candidate transitions and rollbacks.
    Tokens are single-use, short-lived (10 min), authenticated, and tied to exact release candidate ID & commit SHA.
    """

    @staticmethod
    def generate_confirmation_token(release_candidate_id: str, commit_sha: str, approval_type: ApprovalType) -> Dict[str, Any]:
        raw_token = f"APP-{secrets.token_hex(4).upper()}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=APPROVAL_TOKEN_EXPIRY_MINUTES)
        return {
            "token": raw_token,
            "release_candidate_id": release_candidate_id,
            "commit_sha": commit_sha,
            "approval_type": approval_type.value if hasattr(approval_type, 'value') else approval_type,
            "expires_at": expires_at.isoformat()
        }

    @staticmethod
    async def record_approval(
        db: AsyncSession,
        release_candidate_id: str,
        approver_id: str,
        approval_type: ApprovalType,
        decision: ApprovalDecision,
        confirmation_id: str,
        reason: Optional[str] = None
    ) -> ProductionApprovalModel:
        approval_model = ProductionApprovalModel(
            release_candidate_id=release_candidate_id,
            approver_id=approver_id,
            approval_type=approval_type.value if hasattr(approval_type, 'value') else approval_type,
            decision=decision.value if hasattr(decision, 'value') else decision,
            reason=reason or "Explicit human approval granted",
            confirmation_id=confirmation_id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(approval_model)
        await db.commit()
        await db.refresh(approval_model)
        logger.info(f"Recorded production approval #{approval_model.id[:8]} [{approval_model.approval_type}] decision={approval_model.decision}")
        return approval_model

    @staticmethod
    async def verify_token_unused(db: AsyncSession, confirmation_id: str) -> bool:
        stmt = select(ProductionApprovalModel).where(ProductionApprovalModel.confirmation_id == confirmation_id)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        return existing is None
