"""Government scheme scaffold for Rythu Mitra."""

SCHEMES: dict[str, dict] = {}


def get_scheme(name: str) -> dict | None:
    """Return a scheme by name when present."""

    return SCHEMES.get(name)
