import re

_NOISE_PATTERNS = [
    re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)?\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE
    ),
    re.compile(r"\b\d+\s+(second|minute|hour|day|week|month|year)s?\s+ago\b", re.IGNORECASE),
]

_NOISE_LINE_KEYWORDS = [
    "cookie",
    "accept all",
    "we use cookies",
    "privacy preferences",
    "manage preferences",
    "subscribe to our newsletter",
    "sign up for updates",
]


def strip_noise(text: str) -> str:
    kept = []

    for line in text.splitlines():
        lowered = line.lower()

        if any(keyword in lowered for keyword in _NOISE_LINE_KEYWORDS):
            continue

        cleaned = line
        for pattern in _NOISE_PATTERNS:
            cleaned = pattern.sub("", cleaned)

        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if cleaned:
            kept.append(cleaned)

    return "\n".join(kept)
