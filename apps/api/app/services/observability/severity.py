from app.services.observability.models import ObservabilitySeverity


class ObservabilitySeverityClassifier:
    """
    Classifies raw event metadata or Sentry levels into standardized ObservabilitySeverity enum.
    """

    @staticmethod
    def classify(raw_level: str) -> ObservabilitySeverity:
        lvl = (raw_level or "").lower().strip()
        if lvl in ["fatal", "critical", "emergency"]:
            return ObservabilitySeverity.CRITICAL
        elif lvl in ["error", "err", "exception", "unhandled"]:
            return ObservabilitySeverity.ERROR
        elif lvl in ["warning", "warn"]:
            return ObservabilitySeverity.WARNING
        elif lvl in ["info", "information", "debug"]:
            return ObservabilitySeverity.INFO
        return ObservabilitySeverity.ERROR
