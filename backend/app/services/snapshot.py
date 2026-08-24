import requests
from bs4 import BeautifulSoup

USER_AGENT = "CompetitiveIntelligenceMonitor/1.0"
REQUEST_TIMEOUT = 10


class FetchError(Exception):
    pass


def fetch_html(url: str) -> str:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"Failed to fetch {url}: {exc}") from exc

    return response.text


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "img", "iframe"]):
        tag.decompose()

    lines = [
        line.strip()
        for line in soup.get_text(separator="\n").splitlines()
    ]

    return "\n".join(line for line in lines if line)
