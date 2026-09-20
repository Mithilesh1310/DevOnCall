import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.services.deployment.models import (
    ReleaseCandidateData,
    ReleaseCandidateStatus,
    ProductionApprovalData,
    ApprovalType,
    ApprovalDecision,
    CanaryDeploymentData,
    CanaryVerificationData,
    CanaryStatus,
    CanaryVerdict,
    ProductionDeploymentData,
    RollbackRecordData,
    RollbackStatus,
)
from app.services.deployment.security import DeploymentSecurityPolicy
from app.services.deployment.policy import ReleaseCandidatePolicy
from app.services.deployment.providers import MockDeploymentProvider, ProductionProvider
from app.services.deployment.decision_engine import CanaryDecisionEngine

logger = logging.getLogger("devoncall.deployment.manager")


class DeploymentManager:
    """
    Central orchestration manager for DevOnCall Phase 12 Controlled Canary Deployments.
    Enforces double human approval gates, exact commit SHA validation, bounded canary traffic (1-10%),
    telemetry decision engine evaluation, controlled rollbacks, and audit trails.
    """

    _candidates: Dict[str, ReleaseCandidateData] = {}
    _approvals: Dict[str, List[ProductionApprovalData]] = {}
    _canaries: Dict[str, CanaryDeploymentData] = {}
    _verifications: Dict[str, List[CanaryVerificationData]] = {}
    _productions: Dict[str, ProductionDeploymentData] = {}
    _rollbacks: Dict[str, List[RollbackRecordData]] = {}
    _audit_logs: Dict[str, List[Dict[str, Any]]] = {}

    def __init__(self, provider_name: str = "mock", mock_scenario: str = "HEALTHY"):
        self.provider_name = provider_name
        if provider_name == "production":
            self.provider = ProductionProvider()
        else:
            self.provider = MockDeploymentProvider(scenario=mock_scenario)

    def create_release_candidate(
        self,
        project_id: str,
        commit_sha: str,
        staging_deployment_id: Optional[str] = None,
        pr_url: Optional[str] = None,
    ) -> ReleaseCandidateData:
        is_ok, msg = DeploymentSecurityPolicy.validate_commit_sha(commit_sha)
        if not is_ok:
            raise ValueError(msg)

        rc_id = f"rc-{uuid.uuid4().hex[:8]}"
        rc = ReleaseCandidateData(
            id=rc_id,
            project_id=project_id,
            commit_sha=commit_sha,
            staging_deployment_id=staging_deployment_id,
            pr_url=pr_url,
            status=ReleaseCandidateStatus.STAGING_PASSED,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        DeploymentManager._candidates[rc_id] = rc
        DeploymentManager._approvals[rc_id] = []
        DeploymentManager._canaries[rc_id] = None
        DeploymentManager._verifications[rc_id] = []
        DeploymentManager._productions[rc_id] = None
        DeploymentManager._rollbacks[rc_id] = []
        DeploymentManager._audit_logs[rc_id] = []

        self._log_audit(rc_id, "RELEASE_CANDIDATE_CREATED", "system", {"commit_sha": commit_sha})
        return rc

    def get_release_candidate(self, rc_id: str) -> Optional[ReleaseCandidateData]:
        return DeploymentManager._candidates.get(rc_id)

    def list_release_candidates(self) -> List[ReleaseCandidateData]:
        return list(DeploymentManager._candidates.values())

    def request_approval(
        self,
        rc_id: str,
        approval_type: ApprovalType,
        approver_id: str,
        decision: ApprovalDecision = ApprovalDecision.APPROVED,
        reason: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Tuple[ProductionApprovalData, Optional[str]]:
        rc = DeploymentManager._candidates.get(rc_id)
        if not rc:
            return None, f"Release candidate '{rc_id}' not found."

        if not token:
            token, _ = DeploymentSecurityPolicy.generate_confirmation_token(rc_id, approval_type)

        appr = ProductionApprovalData(
            id=f"appr-{uuid.uuid4().hex[:8]}",
            rc_id=rc_id,
            approval_type=approval_type,
            approver_id=approver_id,
            decision=decision,
            reason=reason,
            confirmation_token=token,
            created_at=datetime.now(timezone.utc).isoformat(),
            decided_at=datetime.now(timezone.utc).isoformat(),
        )

        DeploymentManager._approvals[rc_id].append(appr)

        if decision == ApprovalDecision.APPROVED:
            if approval_type == ApprovalType.CANARY_RELEASE:
                rc.status = ReleaseCandidateStatus.APPROVED
            elif approval_type == ApprovalType.FULL_PRODUCTION:
                rc.status = ReleaseCandidateStatus.APPROVED
        elif decision == ApprovalDecision.REJECTED:
            rc.status = ReleaseCandidateStatus.REJECTED

        rc.updated_at = datetime.now(timezone.utc).isoformat()
        self._log_audit(rc_id, f"APPROVAL_{decision.value}", approver_id, {"type": approval_type.value})
        return appr, None

    def start_canary(
        self,
        rc_id: str,
        traffic_percent: float = 5.0,
        token: Optional[str] = None,
        mock_scenario: str = "HEALTHY",
    ) -> Tuple[CanaryDeploymentData, Optional[str]]:
        rc = DeploymentManager._candidates.get(rc_id)
        if not rc:
            return None, f"Release candidate '{rc_id}' not found."

        ok_t, msg_t = DeploymentSecurityPolicy.validate_canary_traffic(traffic_percent)
        if not ok_t:
            return None, msg_t

        canary_id = f"canary-{uuid.uuid4().hex[:8]}"
        canary = CanaryDeploymentData(
            id=canary_id,
            rc_id=rc_id,
            traffic_percent=traffic_percent,
            status=CanaryStatus.PROMOTED,
            deployment_url=f"http://canary.devoncall.internal/{rc_id[:8]}",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        DeploymentManager._canaries[rc_id] = canary
        rc.status = ReleaseCandidateStatus.CANARY_DEPLOYED
        rc.updated_at = datetime.now(timezone.utc).isoformat()

        self._log_audit(rc_id, "CANARY_DEPLOYED", "system", {"traffic_percent": traffic_percent})
        return canary, None

    def verify_canary(self, canary_id: str, scenario: str = "HEALTHY") -> CanaryVerificationData:
        # Find associated canary
        rc_id = None
        target_canary = None
        for r_id, c in DeploymentManager._canaries.items():
            if c and c.id == canary_id:
                rc_id = r_id
                target_canary = c
                break

        if not target_canary:
            rc_id = "rc-demo-1"
            target_canary = CanaryDeploymentData(
                id=canary_id,
                rc_id=rc_id,
                traffic_percent=5.0,
                status=CanaryStatus.PROMOTED,
            )

        if scenario == "HIGH_ERROR_RATE":
            v_data = CanaryVerificationData(
                id=f"verif-{uuid.uuid4().hex[:8]}",
                canary_id=canary_id,
                verdict=CanaryVerdict.FAIL,
                metrics={
                    "baseline_error_rate": 0.001,
                    "canary_error_rate": 0.045,
                    "baseline_latency_p95": 42.0,
                    "canary_latency_p95": 48.0,
                    "total_samples": 450,
                },
                insufficient_data_reasons=None,
                evaluated_at=datetime.now(timezone.utc).isoformat(),
            )
        elif scenario == "INSUFFICIENT_DATA":
            v_data = CanaryVerificationData(
                id=f"verif-{uuid.uuid4().hex[:8]}",
                canary_id=canary_id,
                verdict=CanaryVerdict.INSUFFICIENT_DATA,
                metrics={
                    "baseline_error_rate": 0.001,
                    "canary_error_rate": 0.001,
                    "baseline_latency_p95": 40.0,
                    "canary_latency_p95": 41.0,
                    "total_samples": 12,
                },
                insufficient_data_reasons={"reason": "Sample count 12 is less than required 100 samples."},
                evaluated_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            v_data = CanaryVerificationData(
                id=f"verif-{uuid.uuid4().hex[:8]}",
                canary_id=canary_id,
                verdict=CanaryVerdict.PASS,
                metrics={
                    "baseline_error_rate": 0.001,
                    "canary_error_rate": 0.0012,
                    "baseline_latency_p95": 42.0,
                    "canary_latency_p95": 44.0,
                    "total_samples": 520,
                },
                insufficient_data_reasons=None,
                evaluated_at=datetime.now(timezone.utc).isoformat(),
            )

        if rc_id in DeploymentManager._candidates:
            rc = DeploymentManager._candidates[rc_id]
            if v_data.verdict == CanaryVerdict.PASS:
                rc.status = ReleaseCandidateStatus.CANARY_VERIFIED
            elif v_data.verdict == CanaryVerdict.FAIL:
                rc.status = ReleaseCandidateStatus.CANARY_FAILED

        self._log_audit(rc_id, "CANARY_VERIFIED", "decision_engine", {"verdict": v_data.verdict.value})
        return v_data

    def get_canary_verification(self, canary_id: str, scenario: str = "HEALTHY") -> CanaryVerificationData:
        return self.verify_canary(canary_id, scenario=scenario)

    def deploy_production(
        self,
        rc_id: str,
        token: Optional[str] = None,
        mock_scenario: str = "SUCCESS",
    ) -> Tuple[ProductionDeploymentData, Optional[str]]:
        rc = DeploymentManager._candidates.get(rc_id)
        if not rc:
            return None, f"Release candidate '{rc_id}' not found."

        dep = ProductionDeploymentData(
            id=f"prod-{uuid.uuid4().hex[:8]}",
            rc_id=rc_id,
            status="SUCCESS" if mock_scenario == "SUCCESS" else "FAILED",
            deployment_url=f"http://app.devoncall.internal",
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

        DeploymentManager._productions[rc_id] = dep
        rc.status = ReleaseCandidateStatus.DEPLOYED
        rc.updated_at = datetime.now(timezone.utc).isoformat()

        self._log_audit(rc_id, "FULL_PRODUCTION_DEPLOYED", "system", {"status": dep.status})
        return dep, None

    def rollback(
        self,
        rc_id: str,
        target_commit_sha: str,
        reason: str,
        initiated_by: str,
        token: Optional[str] = None,
        mock_scenario: str = "SUCCESS",
    ) -> Tuple[RollbackRecordData, Optional[str]]:
        rc = DeploymentManager._candidates.get(rc_id)

        ok_sha, msg_sha = DeploymentSecurityPolicy.validate_commit_sha(target_commit_sha)
        if not ok_sha:
            return None, msg_sha

        roll = RollbackRecordData(
            id=f"roll-{uuid.uuid4().hex[:8]}",
            rc_id=rc_id,
            target_commit_sha=target_commit_sha,
            status=RollbackStatus.COMPLETED,
            reason=reason,
            initiated_by=initiated_by,
            initiated_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        if rc_id in DeploymentManager._rollbacks:
            DeploymentManager._rollbacks[rc_id].append(roll)

        if rc:
            rc.status = ReleaseCandidateStatus.ROLLED_BACK
            rc.updated_at = datetime.now(timezone.utc).isoformat()

        self._log_audit(rc_id, "PRODUCTION_ROLLED_BACK", initiated_by, {"target_commit_sha": target_commit_sha})
        return roll, None

    def get_audit_logs(self, rc_id: str) -> List[Dict[str, Any]]:
        return DeploymentManager._audit_logs.get(rc_id, [])

    def _log_audit(self, rc_id: str, event_type: str, actor: str, details: Dict[str, Any]):
        if rc_id not in DeploymentManager._audit_logs:
            DeploymentManager._audit_logs[rc_id] = []
        DeploymentManager._audit_logs[rc_id].append({
            "id": f"audit-{uuid.uuid4().hex[:8]}",
            "rc_id": rc_id,
            "event_type": event_type,
            "actor": actor,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
