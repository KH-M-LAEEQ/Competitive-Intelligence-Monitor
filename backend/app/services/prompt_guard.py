import re

_MARKERS = [
    re.compile(r"ignore (all |any )?(previous|prior|above) instructions", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"disregard (the )?(system|previous) prompt", re.IGNORECASE),
    re.compile(r"^\s*(system|assistant)\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"###\s*(instruction|system)", re.IGNORECASE),
]


def scan_for_injection_markers(text: str) -> list[str]:
    """Heuristic, log-only scan of scraped content for prompt-injection
    phrasing. Never used to block a check — false positives on legitimate
    competitor copy would silently suppress real detections, and the LLM
    call itself has no tool access regardless, so this exists purely for
    visibility (surfaced in the audit trail once it exists, Phase 7).
    """

    return [m.group(0) for pattern in _MARKERS if (m := pattern.search(text))]
