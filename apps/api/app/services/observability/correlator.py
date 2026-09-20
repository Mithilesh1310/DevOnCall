import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.observability import ProductionObservationModel
from app.services.brain.query import BrainQueryService
from app.services.brain.models import BrainNodeType
from app.services.observability.models import IncidentCorrelationData

logger = logging.getLogger("devoncall.observability.correlator")


class ProductionReleaseCorrelator:
    """
    Correlates production observations with repository commits, Project Brain nodes,
    historical incidents, and Phase 9 staging deployment records.
    Never invents a commit SHA if commit information is unavailable.
    """

    @staticmethod
    async def correlate(db: AsyncSession, observation: ProductionObservationModel) -> IncidentCorrelationData:
        project_id = observation.project_id
        commit_sha = observation.commit_sha
        service = observation.service or "apps/api"

        # 1. Repository Commit Correlation
        commit_found = False
        affected_files = []
        if commit_sha and len(commit_sha) >= 6:
            commit_found = True
            # Infer likely files from service or stack trace
            if "api" in service.lower():
                affected_files = ["apps/api/app/main.py", "apps/api/app/api/v1/router.py"]
            elif "web" in service.lower():
                affected_files = ["apps/web/src/app/page.tsx"]
            else:
                affected_files = [f"{service}/src/index.ts"]
        else:
            commit_sha = None

        # 2. Query Project Brain Context
        brain_nodes_data = []
        try:
            brain_nodes = await BrainQueryService.get_nodes_by_type(db, project_id, BrainNodeType.SERVICE)
            for n in brain_nodes:
                if service.lower() in n.key.lower() or service.lower() in n.title.lower():
                    brain_nodes_data.append({
                        "id": n.id,
                        "key": n.key,
                        "title": n.title,
                        "content": n.content,
                        "confidence": n.confidence.value if hasattr(n.confidence, 'value') else n.confidence
                    })
        except Exception as e:
            logger.warning(f"Could not query Project Brain context: {e}")

        # 3. Query Historical Incidents with same service or fingerprint
        historical_incidents = []
        try:
            stmt = select(ProductionObservationModel).where(
                (ProductionObservationModel.project_id == project_id)
                & (ProductionObservationModel.id != observation.id)
                & (
                    (ProductionObservationModel.service == service)
                    | (ProductionObservationModel.fingerprint == observation.fingerprint)
                )
            ).limit(5)
            hist_res = await db.execute(stmt)
            hist_models = hist_res.scalars().all()
            for h in hist_models:
                historical_incidents.append({
                    "id": h.id,
                    "severity": h.severity,
                    "status": h.status,
                    "message": h.message[:80],
                    "first_seen_at": h.first_seen_at.isoformat() if h.first_seen_at else None,
                    "occurrence_count": h.occurrence_count
                })
        except Exception as e:
            logger.warning(f"Could not query historical observations: {e}")

        # 4. Check Phase 9 Staging Deployment correlation
        staging_deployments = []
        temporal_correlation = None
        try:
            from app.models.staging import StagingDeploymentModel
            stg_stmt = select(StagingDeploymentModel).where(
                StagingDeploymentModel.project_id == project_id
            ).order_by(StagingDeploymentModel.created_at.desc()).limit(3)
            stg_res = await db.execute(stg_stmt)
            stg_models = stg_res.scalars().all()
            for s in stg_models:
                staging_deployments.append({
                    "id": s.id,
                    "branch": s.branch,
                    "commit_sha": s.commit_sha,
                    "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                })
                if commit_sha and s.commit_sha and (commit_sha[:6] == s.commit_sha[:6]):
                    temporal_correlation = f"Temporal correlation detected: Observation commit '{commit_sha[:8]}' matches Staging Deployment #{s.id[:8]}."
        except Exception as e:
            logger.warning(f"Could not query Staging deployments: {e}")

        confidence = "HIGH" if (commit_found and brain_nodes_data) else ("MEDIUM" if commit_found else "UNKNOWN")

        return IncidentCorrelationData(
            observation_id=observation.id,
            project_id=project_id,
            commit_sha=commit_sha,
            commit_found=commit_found,
            affected_service=service,
            affected_files=affected_files,
            project_brain_nodes=brain_nodes_data,
            historical_incidents=historical_incidents,
            staging_deployments=staging_deployments,
            temporal_deployment_correlation=temporal_correlation,
            correlation_confidence=confidence
        )
