from urllib.parse import quote, urlparse
from fastapi import APIRouter, HTTPException, Query
from app.config import BASE_URL
from app.scraper.fetcher import fetch_html, SourceFetchError
from app.scraper.parser import (
    parse_archive, parse_home, parse_detail, parse_episode, parse_taxonomy_links
)

router = APIRouter(prefix="/api", tags=["PirateXPlay Anime"])

async def _get(path: str) -> str:
    try:
        return await fetch_html(path)
    except SourceFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

def _clean_slug(value: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        if parsed.hostname not in {"piratexplay.cc", "www.piratexplay.cc"}:
            raise HTTPException(status_code=400, detail="Only PirateXPlay URLs are accepted")
        value = parsed.path.rstrip("/").split("/")[-1]
    value = value.strip().strip("/")
    if not value or "/" in value or ".." in value:
        raise HTTPException(status_code=400, detail="Invalid slug")
    return value

@router.get("/home")
async def home():
    return parse_home(await _get("/home"))

@router.get("/anime")
async def anime(page: int = Query(1, ge=1, le=1000)):
    path = "/category/anime/" if page == 1 else f"/category/anime/page/{page}/"
    return parse_archive(await _get(path), f"{BASE_URL}{path}", page)

@router.get("/search")
async def search(keyword: str = Query(..., min_length=1, max_length=100),
                 page: int = Query(1, ge=1, le=1000)):
    path = f"/?s={quote(keyword)}"
    if page > 1:
        path = f"/page/{page}/?s={quote(keyword)}"
    result = parse_archive(await _get(path), f"{BASE_URL}{path}", page)
    result["keyword"] = keyword
    result["results"] = [x for x in result["results"] if "/series/" in x["url"]]
    result["count"] = len(result["results"])
    return result

@router.get("/trending")
async def trending(page: int = Query(1, ge=1, le=1000)):
    path = "/category/popular/" if page == 1 else f"/category/popular/page/{page}/"
    return parse_archive(await _get(path), f"{BASE_URL}{path}", page)

@router.get("/latest")
async def latest(page: int = Query(1, ge=1, le=1000)):
    path = "/category/ongoing/" if page == 1 else f"/category/ongoing/page/{page}/"
    return parse_archive(await _get(path), f"{BASE_URL}{path}", page)

@router.get("/genres")
async def genres():
    html = await _get("/home")
    return {"success": True, "results": parse_taxonomy_links(html, "a[href*='/genre/']")}

@router.get("/languages")
async def languages():
    html = await _get("/home")
    return {"success": True, "results": parse_taxonomy_links(html, "a[href*='/language/']")}

@router.get("/genre/{slug}")
async def genre(slug: str, page: int = Query(1, ge=1, le=1000)):
    slug = _clean_slug(slug)
    path = f"/genre/{slug}/" if page == 1 else f"/genre/{slug}/page/{page}/"
    return parse_archive(await _get(path), f"{BASE_URL}{path}", page)

@router.get("/language/{slug}")
async def language(slug: str, page: int = Query(1, ge=1, le=1000)):
    slug = _clean_slug(slug)
    path = f"/language/{slug}/" if page == 1 else f"/language/{slug}/page/{page}/"
    return parse_archive(await _get(path), f"{BASE_URL}{path}", page)

@router.get("/anime/{slug}")
async def anime_detail(slug: str):
    slug = _clean_slug(slug)
    path = f"/series/{slug}/"
    result = parse_detail(await _get(path), f"{BASE_URL}{path}")
    if not result.get("title"):
        raise HTTPException(status_code=404, detail="Anime series not found or page structure changed")
    return result

@router.get("/anime/{slug}/seasons")
async def anime_seasons(slug: str):
    """Discover sibling seasons and report the live episode count for each."""
    result = await anime_detail(slug)
    seasons = result.get("seasons", [])

    # Some season pages expose the season switcher; if so, prefer its complete list.
    enriched = []
    for season in seasons:
        try:
            html = await _get(season["url"])
            season_detail = parse_detail(html, season["url"])
            enriched.append({**season, "episode_count": season_detail["episode_count"]})
        except HTTPException:
            enriched.append({**season, "episode_count": None})

    return {
        "success": True,
        "anime": result["title"],
        "count": len(enriched),
        "results": enriched,
    }

@router.get("/anime/{slug}/episodes")
async def anime_episodes(slug: str, all_seasons: bool = Query(False)):
    """Return episodes for this season page, or aggregate every discovered season."""
    result = await anime_detail(slug)
    episodes = list(result.get("episodes", []))
    seasons = result.get("seasons", [])

    if all_seasons and seasons:
        episodes = []
        seen = set()
        for season in seasons:
            html = await _get(season["url"])
            season_episodes = parse_detail(html, season["url"]).get("episodes", [])
            for episode in season_episodes:
                if episode["url"] not in seen:
                    seen.add(episode["url"])
                    episodes.append(episode)

    return {
        "success": True,
        "anime": result["title"],
        "count": len(episodes),
        "seasons_count": len(seasons),
        "results": episodes,
    }

@router.get("/episode/{slug}")
async def episode_detail(slug: str):
    slug = _clean_slug(slug)
    path = f"/episode/{slug}/"
    result = parse_episode(await _get(path), f"{BASE_URL}{path}")
    if not result.get("title"):
        raise HTTPException(status_code=404, detail="Episode not found or page structure changed")
    return result

@router.get("/episode/{slug}/downloads")
async def episode_downloads(slug: str):
    """Return the source page's download table for one episode."""
    result = await episode_detail(slug)
    return {
        "success": True,
        "episode": result["title"],
        "episode_url": result["url"],
        "count": result["download_count"],
        "results": result["downloads"],
    }
