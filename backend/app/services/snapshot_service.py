from app.services.snapshot import fetch_html, extract_text, FetchError
from app.services.noise_filter import strip_noise

__all__ = ["capture_clean_snapshot", "FetchError"]


def capture_clean_snapshot(url: str) -> str:
    html = fetch_html(url)
    text = extract_text(html)
    return strip_noise(text)
