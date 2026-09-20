import pytest
from app.services.deployment.manager import DeploymentManager
from app.services.deployment.models import (
    ReleaseCandidateStatus,
    ApprovalType,
    ApprovalDecision,
    CanaryStatus,
    CanaryVerdict,
    RollbackStatus,
)


def test_full_release_candidate_happy_path():
    manager = DeploymentManager()
    sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"

    # 1. Create Release Candidate
    rc = manager.create_release_candidate("proj-1", commit_sha=sha, staging_deployment_id="stg-1")
    assert rc.status == ReleaseCandidateStatus.STAGING_PASSED

    # 2. Gate 1 Approval (Canary)
    appr1, err1 = manager.request_approval(rc.id, ApprovalType.CANARY_RELEASE, "approver-1", decision=ApprovalDecision.APPROVED)
    assert err1 is None
    assert appr1.decision == ApprovalDecision.APPROVED

    # 3. Start Canary (5% traffic)
    canary, err2 = manager.start_canary(rc.id, traffic_percent=5.0, mock_scenario="HEALTHY")
    assert err2 is None
    assert canary.status == CanaryStatus.PROMOTED
    assert canary.traffic_percent == 5.0

    # 4. Telemetry Verification
    verif = manager.verify_canary(canary.id, scenario="HEALTHY")
    assert verif.verdict == CanaryVerdict.PASS

    # 5. Gate 2 Approval (Production)
    appr2, err3 = manager.request_approval(rc.id, ApprovalType.FULL_PRODUCTION, "approver-2", decision=ApprovalDecision.APPROVED)
    assert err3 is None
    assert appr2.decision == ApprovalDecision.APPROVED

    # 6. Deploy Production
    prod, err4 = manager.deploy_production(rc.id, mock_scenario="SUCCESS")
    assert err4 is None
    assert prod.status == "SUCCESS"

    # Verify final status
    rc_final = manager.get_release_candidate(rc.id)
    assert rc_final.status == ReleaseCandidateStatus.DEPLOYED


def test_canary_failure_and_rollback():
    manager = DeploymentManager()
    sha = "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3"

    rc = manager.create_release_candidate("proj-2", commit_sha=sha)
    manager.request_approval(rc.id, ApprovalType.CANARY_RELEASE, "appr-1", decision=ApprovalDecision.APPROVED)
    canary, _ = manager.start_canary(rc.id, traffic_percent=5.0, mock_scenario="HIGH_ERROR_RATE")

    verif = manager.verify_canary(canary.id, scenario="HIGH_ERROR_RATE")
    assert verif.verdict == CanaryVerdict.FAIL

    target_sha = "f0e9d8c7b6a5f0e9d8c7b6a5f0e9d8c7b6a5f0e9"
    roll, err = manager.rollback(rc.id, target_commit_sha=target_sha, reason="High error rate in canary", initiated_by="auto-safety")
    assert err is None
    assert roll.status == RollbackStatus.COMPLETED

    rc_final = manager.get_release_candidate(rc.id)
    assert rc_final.status == ReleaseCandidateStatus.ROLLED_BACK


def test_audit_logs_recorded():
    manager = DeploymentManager()
    sha = "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    rc = manager.create_release_candidate("proj-3", commit_sha=sha)

    logs = manager.get_audit_logs(rc.id)
    assert len(logs) >= 1
    assert logs[0]["event_type"] == "RELEASE_CANDIDATE_CREATED"
