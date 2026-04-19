"""Post-harvest drying alert scaffold."""


class DryingAlertService:
    """Placeholder for 6am, 3-hour, and urgent rain risk alerts."""

    def evaluate(self, farmer_id: str) -> list[dict]:
        raise NotImplementedError(
            "Implement drying-phase rain risk monitoring and urgent alerts."
        )
