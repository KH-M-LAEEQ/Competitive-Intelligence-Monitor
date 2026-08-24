import json
import re

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Error as PlaywrightError

from app.services.noise_filter import strip_noise

__all__ = ["capture_rendered_text", "find_category_listing_url", "RenderedContentError"]

_GOTO_TIMEOUT_MS = 15_000
_SETTLE_MS = 5_000

# Some storefronts hydrate their nav/category menu — and separately, their
# hero/promo banner tiles — from JSON data blobs embedded in a <script> tag,
# building the visible DOM only on user interaction (hover) or not as text
# at all (banner tiles are often rendered as an image with the JSON label
# used only for alt text/analytics). Either way, the label text never
# appears in rendered page text. Two distinct field-pair shapes have been
# seen in the wild: a "name" immediately followed by "handle" (category/menu
# nodes — see rendered_content_service tests), and a "label" immediately
# followed by "link" (promo/CTA banner tiles, e.g. "BAREEZE PRET SALE").
# Plain object keys or CSS elsewhere in the page won't have either pair
# side by side, so this stays reasonably well-scoped despite matching two
# key names. Quotes may be backslash-escaped (\") when the JSON is itself
# embedded as a string literal inside a larger hydration payload, hence the
# \\* before each quote below.
_MENU_NODE_RE = re.compile(
    r'\\*"(?:name|label)\\*"\s*:\s*\\*"((?:[^"\\]|\\.){1,60}?)\\*"\s*,\s*\\*"(?:handle|link)\\*"'
)
_MAX_EMBEDDED_NAMES = 200


class RenderedContentError(Exception):
    pass


def _extract_embedded_category_names(html: str) -> list[str]:
    names = []
    seen = set()
    for match in _MENU_NODE_RE.finditer(html):
        raw = match.group(1)
        name = raw.replace('\\"', '"').replace("\\\\", "\\").strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
            if len(names) >= _MAX_EMBEDDED_NAMES:
                break
    return names


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "img", "iframe"]):
        tag.decompose()

    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    text = "\n".join(line for line in lines if line)

    embedded_names = _extract_embedded_category_names(html)
    if embedded_names:
        text += "\n\nSite navigation menu data (from page structure):\n" + "\n".join(embedded_names)

    return text


def capture_rendered_text(url: str) -> str:
    """Fetches a URL with a real browser and reads the page after client-side
    JavaScript has had a chance to run — unlike snapshot_service.py's plain
    `requests.get()` (used for the cheap, frequent change-detection diff),
    this sees content that only appears post-render. Many storefronts (hero
    banners, sale badges, category navigation) render that way; a plain HTTP
    fetch of those pages captures little more than the loading skeleton.
    Reserved for on-demand site-summary generation, not the high-frequency
    diff pipeline, since launching a browser per call is much heavier than a
    plain GET.

    Waits for "domcontentloaded" plus a fixed settle delay, not
    "networkidle": many real storefronts keep at least one connection open
    indefinitely (chat widgets, analytics beacons, polling), so networkidle
    never resolves and the whole fetch times out and falls back to the
    pre-render HTML — the exact bug this feature exists to avoid.
    """

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=_GOTO_TIMEOUT_MS)
                page.wait_for_timeout(_SETTLE_MS)
                html = page.content()
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise RenderedContentError(f"Failed to render {url}: {exc}") from exc

    return strip_noise(_extract_text(html))


def find_category_listing_url(url: str, category: str) -> str | None:
    """Looks for a link on `url` whose visible text matches `category`, and
    returns its resolved href — a best-effort way to turn a category label
    (e.g. "Menswear") into an actual listing page to price-check, since
    nothing in this codebase otherwise associates a category string with any
    URL. Categories pulled from an embedded JSON menu rather than visible
    nav text (see _extract_embedded_category_names) won't have a matching
    link on the page at all; this returns None in that case rather than
    guessing a URL shape, since a wrong guess would silently show prices
    from the wrong page.

    Uses one batched `eval_on_selector_all` call to grab every link's text
    and resolved href in a single round trip, rather than iterating
    `Locator.all()` and calling `.inner_text()` per element — pages with
    hundreds of nav links (mega-menus) make the per-element version far too
    slow.
    """

    normalized = category.strip().lower()
    if not normalized:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=_GOTO_TIMEOUT_MS)
                page.wait_for_timeout(_SETTLE_MS)
                # innerText respects CSS visibility, so links inside a
                # currently-closed mega-menu/dropdown (display:none until
                # hovered) come back empty even though the link and its
                # label both exist in the DOM. Falling back to textContent
                # (which ignores visibility) catches those.
                pairs = page.eval_on_selector_all(
                    "a",
                    "els => els.map(el => [(el.innerText || el.textContent || '').trim(), el.href])"
                )
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise RenderedContentError(f"Failed to search {url} for a category link: {exc}") from exc

    exact_match = None
    partial_match = None
    for text, href in pairs:
        if not text or not href:
            continue
        lowered = text.strip().lower()
        if lowered == normalized and exact_match is None:
            exact_match = href
        elif partial_match is None and (normalized in lowered or lowered in normalized):
            partial_match = href

    return exact_match or partial_match
