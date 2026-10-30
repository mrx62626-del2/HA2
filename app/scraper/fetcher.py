import httpx
from cachetools import TTLCache
from app.config import BASE_URL, TIMEOUT_SECONDS, USER_AGENT, CACHE_TTL_SECONDS

_cache = TTLCache(maxsize=256, ttl=CACHE_TTL_SECONDS)

class SourceFetchError(Exception):
    pass

async def fetch_html(path_or_url: str) -> str:
    url = path_or_url if path_or_url.startswith("http") else f"{BASE_URL}{path_or_url}"
    if url in _cache:
        return _cache[url]

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"{BASE_URL}/home",
    }
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type.lower():
                raise SourceFetchError(f"Unexpected content type from source: {content_type}")
            html = response.text
            _cache[url] = html
            return html
    except (httpx.HTTPError, SourceFetchError) as exc:
        raise SourceFetchError(f"Could not fetch PirateXPlay page {url}: {exc}") from exc
