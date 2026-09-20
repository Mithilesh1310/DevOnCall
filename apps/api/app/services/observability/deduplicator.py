import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.observability import ProductionObservationModel
from app.services.observability.models import ProductionObservationData

logger = logging.getLogger("devoncall.observability.deduplicator")


class ObservabilityDeduplicator:
    """
    Deduplicates incoming production observations based on stable fingerprints.
    Increments occurrence count and updates last_seen_at while preserving first_seen_at.
    """

    @staticmethod
    async def process_observation(db: AsyncSession, observation: ProductionObservationData) -> Tuple[ProductionObservationModel, bool]:
        """
        Deduplicates observation by fingerprint and project_id.
        Returns (model, is_new).
        """
        stmt = select(ProductionObservationModel).where(
            (ProductionObservationModel.project_id == observation.project_id)
            & (ProductionObservationModel.fingerprint == observation.fingerprint)
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        now_dt = datetime.now(timezone.utc)

        if existing:
            # Duplicate event detected -> update occurrence count and last_seen_at
            existing.occurrence_count += observation.occurrence_count
            existing.last_seen_at = now_dt
            if existing.status == "RESOLVED":
                existing.status = "OPEN"  # Reopen if recurring
            await db.commit()
            await db.refresh(existing)
            logger.info(f"Deduplicated existing observation #{existing.id[:8]} (Fingerprint: {existing.fingerprint[:10]}, Occurrences: {existing.occurrence_count})")
            return existing, False
        else:
            # New event -> create new observation model
            new_model = ProductionObservationModel(
                project_id=observation.project_id,
                provider=observation.provider.value if hasattr(observation.provider, 'value') else observation.provider,
                external_event_id=observation.external_event_id,
                fingerprint=observation.fingerprint,
                event_type=observation.event_type,
                severity=observation.severity.value if hasattr(observation.severity, 'value') else observation.severity,
                status=observation.status.value if hasattr(observation.status, 'value') else observation.status,
                environment="PRODUCTION",
                service=observation.service,
                release=observation.release,
                commit_sha=observation.commit_sha,
                message=observation.message,
                stack_trace=observation.stack_trace,
                endpoint=observation.endpoint,
                request_method=observation.request_method,
                source_url=observation.source_url,
                first_seen_at=now_dt,
                last_seen_at=now_dt,
                occurrence_count=max(1, observation.occurrence_count),
                metadata_payload=observation.metadata_payload,
            )
            db.add(new_model)
            await db.commit()
            await db.refresh(new_model)
            logger.info(f"Ingested new production observation #{new_model.id[:8]} (Fingerprint: {new_model.fingerprint[:10]})")
            return new_model, True
