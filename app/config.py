from urllib.parse import urljoin

BASE_URL = "https://piratexplay.cc"
TIMEOUT_SECONDS = 25
CACHE_TTL_SECONDS = 180
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

def absolute_url(value: str | None) -> str | None:
    if not value:
        return None
    return urljoin(BASE_URL, value.strip())
