"""Proactive crop monitoring scaffold."""


class ProactiveMonitor:
    """Placeholder for disease-risk alerts before visible symptoms."""

    def evaluate(self, farmer_id: str) -> list[dict]:
        raise NotImplementedError(
            "Implement crop-stage, weather, and district disease calendar alerts."
        )
