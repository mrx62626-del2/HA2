# PirateXPlay Anime API

Anime-catalog metadata API built with FastAPI. It reads public catalog pages from PirateXPlay and returns structured JSON.

## Scope
- Anime catalog, homepage anime sections, search, genre and language archives
- Anime series details, season links and episode metadata
- Pagination and in-memory response caching
- Does not download or proxy file contents. It returns the download-link entries published in the episode's Download Links table, including the source-provided link URL.

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

## Render
This repository includes `render.yaml`. Create a new Web Service from the repository; Render uses the build and start commands in that file.

## Endpoints
| Endpoint | Purpose |
|---|---|
| `/health` | Health check |
| `/api/home` | Homepage anime sections |
| `/api/anime?page=1` | Anime archive |
| `/api/search?keyword=naruto&page=1` | Search anime |
| `/api/trending?page=1` | Popular anime archive |
| `/api/latest?page=1` | Latest/ongoing anime archive |
| `/api/genres` | Genre links discovered from navigation |
| `/api/languages` | Language links discovered from navigation |
| `/api/genre/{slug}?page=1` | Genre archive |
| `/api/language/{slug}?page=1` | Language archive |
| `/api/anime/{slug}` | Series details and seasons |
| `/api/anime/{slug}/seasons` | Season list |
| `/api/anime/{slug}/episodes` | Episode list |
| `/api/episode/{slug}` | Episode metadata, seasons and download links |\n| `/api/episode/{slug}/downloads` | Download table: server, quality, audio and URL |

Use slugs or full PirateXPlay URLs for detail/episode lookup, for example:
`/api/anime/one-piece-season-1-37854`
`/api/episode/one-piece-season-1-37854-1x1`

## Important implementation notes
- Selectors are based on a live inspection of the site's `/home`, `/category/anime/`, series and episode pages on 2026-10-30.
- PirateXPlay can change its HTML, pagination, access rules or routes at any time. This is a scraper, not a guaranteed stable upstream API.
- Some homepage blocks mix content types. The parser keeps `/series/` links and excludes `/movies/` links; archive endpoints use `/category/anime/` as their source.
- Search results are filtered to series links, but if PirateXPlay mixes non-anime series into its global search results, verify the result category before using it in production.
- The API respects public page responses and does not attempt to defeat login, anti-bot, DRM, or other access controls. Follow the source site's terms and applicable law.
