import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.deployment import CanaryDeploymentModel, CanaryVerificationRecordModel
from app.services.deployment.models import CanaryVerificationData, CanaryVerdict, CanaryPolicyConfig
from app.services.deployment.decision_engine import CanaryDecisionEngine

logger = logging.getLogger("devoncall.deployment.verification")


class CanaryVerificationService:
    """
    Service responsible for querying Phase 11 observability telemetry, comparing baseline
    performance against canary performance, and rendering an auditable CanaryVerdict.
    """

    @staticmethod
    async def run_verification(
        db: AsyncSession,
        canary_model: CanaryDeploymentModel,
        provider_verification_data: CanaryVerificationData,
        config: Optional[CanaryPolicyConfig] = None
    ) -> CanaryVerificationRecordModel:
        verdict, reason = CanaryDecisionEngine.evaluate(provider_verification_data, config=config)

        ver_model = CanaryVerificationRecordModel(
            canary_id=canary_model.id,
            verdict=verdict.value if hasattr(verdict, 'value') else verdict,
            metrics={
                "baseline_error_rate": provider_verification_data.baseline_error_rate,
                "canary_error_rate": provider_verification_data.canary_error_rate,
                "baseline_latency_ms": provider_verification_data.baseline_latency_ms,
                "canary_latency_ms": provider_verification_data.canary_latency_ms,
                "new_critical_incidents": provider_verification_data.new_critical_incidents,
                "observation_count": provider_verification_data.observation_count,
            },
            insufficient_data_reasons={"reason": reason} if verdict in [CanaryVerdict.HUMAN_REVIEW, CanaryVerdict.INSUFFICIENT_DATA] else None,
        )
        db.add(ver_model)
        await db.commit()
        await db.refresh(ver_model)

        logger.info(f"Canary verification completed for #{canary_model.id[:8]}: Verdict={verdict.value}, Reason={reason}")
        return ver_model
