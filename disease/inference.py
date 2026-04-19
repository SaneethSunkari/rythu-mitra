"""Disease inference threshold helpers."""

KVK_CONTACT_NUMBER = "08462-226360"
DEFINITIVE_THRESHOLD = 0.80
CAVEAT_THRESHOLD = 0.60


def interpret_confidence(score: float) -> str:
    """Map a model confidence score to a response tier."""

    if score >= DEFINITIVE_THRESHOLD:
        return "definitive"
    if score >= CAVEAT_THRESHOLD:
        return "caveat"
    return "refer_to_kvk"
