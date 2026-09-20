import logging
from typing import Dict, Any, Tuple
from app.services.deployment.models import CanaryVerdict, CanaryPolicyConfig, CanaryVerificationData

logger = logging.getLogger("devoncall.deployment.decision_engine")


class CanaryDecisionEngine:
    """
    Evaluates canary deployment telemetry against configurable thresholds (CanaryPolicyConfig).
    Renders verdict: PASS, FAIL, INSUFFICIENT_DATA, HUMAN_REVIEW.
    Strictly forbids converting INSUFFICIENT_DATA into PASS.
    """

    @staticmethod
    def evaluate(
        verification_data: CanaryVerificationData,
        config: Optional[CanaryPolicyConfig] = None
    ) -> Tuple[CanaryVerdict, str]:
        cfg = config or CanaryPolicyConfig()

        # 1. Check observation count (Insufficient data check)
        if verification_data.observation_count < cfg.min_observation_count:
            logger.info(f"Canary observation count ({verification_data.observation_count}) < min threshold ({cfg.min_observation_count}). Rendering INSUFFICIENT_DATA.")
            return CanaryVerdict.INSUFFICIENT_DATA, f"Telemetry observation count ({verification_data.observation_count}) is below minimum required threshold ({cfg.min_observation_count}). Window must remain open."

        # 2. Check Critical Incidents
        if verification_data.new_critical_incidents > cfg.max_new_critical_incidents:
            return CanaryVerdict.FAIL, f"New critical incident count ({verification_data.new_critical_incidents}) exceeded maximum threshold ({cfg.max_new_critical_incidents})."

        # 3. Check Error Rate Threshold
        if verification_data.canary_error_rate > cfg.max_error_rate:
            return CanaryVerdict.FAIL, f"Canary error rate ({verification_data.canary_error_rate:.3f}) exceeded maximum threshold ({cfg.max_error_rate:.3f})."

        # 4. Check Latency Multiplier
        if verification_data.baseline_latency_ms > 0:
            latency_mult = verification_data.canary_latency_ms / verification_data.baseline_latency_ms
            if latency_mult > cfg.max_latency_multiplier:
                return CanaryVerdict.FAIL, f"Canary latency multiplier ({latency_mult:.2f}x) exceeded maximum threshold ({cfg.max_latency_multiplier:.2f}x)."

        # 5. Check if provider verdict was explicitly FAIL
        if verification_data.verdict == CanaryVerdict.FAIL:
            return CanaryVerdict.FAIL, verification_data.reason

        if verification_data.verdict == CanaryVerdict.HUMAN_REVIEW:
            return CanaryVerdict.HUMAN_REVIEW, verification_data.reason

        return CanaryVerdict.PASS, "Canary telemetry meets all verification thresholds."
