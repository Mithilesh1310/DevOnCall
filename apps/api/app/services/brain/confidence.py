from app.services.brain.models import BrainConfidence, BrainSourceType


class BrainConfidenceEvaluator:
    """
    Evaluates and enforces confidence rules across Brain nodes and edges.
    Strictly distinguishes VERIFIED facts from INFERRED knowledge.
    """

    @staticmethod
    def determine_confidence(source_type: BrainSourceType, is_deterministic: bool = True) -> BrainConfidence:
        if source_type in [BrainSourceType.REPOSITORY_SCAN, BrainSourceType.HUMAN] and is_deterministic:
            return BrainConfidence.VERIFIED

        if source_type in [BrainSourceType.VALIDATION, BrainSourceType.STAGING]:
            return BrainConfidence.HIGH

        if source_type == BrainSourceType.INCIDENT:
            return BrainConfidence.HIGH if is_deterministic else BrainConfidence.MEDIUM

        return BrainConfidence.MEDIUM
