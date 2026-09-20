import pytest
from fastapi import HTTPException
from app.services.staging.policies import StagingSecurityPolicy


def test_production_environment_strictly_rejected():
    # 1. Environment 'production' MUST be rejected
    is_valid, reason = StagingSecurityPolicy.validate_environment("production")
    assert is_valid is False
    assert "ENVIRONMENT_REJECTED" in reason
    assert "BLOCKED" in reason

    is_valid_prod_cap, _ = StagingSecurityPolicy.validate_environment("PRODUCTION")
    assert is_valid_prod_cap is False

    is_valid_live, _ = StagingSecurityPolicy.validate_environment("live")
    assert is_valid_live is False

    # 2. Only 'STAGING' is valid
    is_valid_staging, _ = StagingSecurityPolicy.validate_environment("STAGING")
    assert is_valid_staging is True


def test_commit_alias_rejection():
    # 'latest', 'main', 'master' without exact commit SHA must be rejected
    is_valid_latest, reason = StagingSecurityPolicy.validate_commit("latest", "devoncall/agent/fix-1")
    assert is_valid_latest is False
    assert "INVALID_COMMIT" in reason

    is_valid_main, _ = StagingSecurityPolicy.validate_commit("main", "devoncall/agent/fix-1")
    assert is_valid_main is False

    # Valid SHA
    is_valid_sha, _ = StagingSecurityPolicy.validate_commit("a1b2c3d4e5f6", "devoncall/agent/fix-1")
    assert is_valid_sha is True


def test_container_mount_security_rejection():
    # Prohibited mounts
    is_valid_sock, reason = StagingSecurityPolicy.validate_container_security(["/var/run/docker.sock:/var/run/docker.sock"])
    assert is_valid_sock is False
    assert "DOCKER_SECURITY_REJECTION" in reason

    is_valid_shadow, _ = StagingSecurityPolicy.validate_container_security(["/etc/shadow:/etc/shadow"])
    assert is_valid_shadow is False

    # Safe mount
    is_valid_safe, _ = StagingSecurityPolicy.validate_container_security(["/tmp/workspace:/app/workspace"])
    assert is_valid_safe is True


def test_staging_secrets_isolation():
    # Env var referencing production DB must be rejected
    bad_env = {"DATABASE_URL": "postgresql://user:pass@production-db:5432/prod"}
    is_valid_secret, reason = StagingSecurityPolicy.validate_staging_secrets(bad_env)
    assert is_valid_secret is False
    assert "SECRET_ISOLATION_REJECTION" in reason

    # Clean staging env
    clean_env = {"DATABASE_URL_STAGING": "postgresql://postgres:postgres@localhost:5432/devoncall_staging"}
    is_valid_clean, _ = StagingSecurityPolicy.validate_staging_secrets(clean_env)
    assert is_valid_clean is True
