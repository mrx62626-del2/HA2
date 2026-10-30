import re
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup, Tag
from app.config import BASE_URL, absolute_url

def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")

def _text(node: Tag | None) -> str | None:
    if not node:
        return None
    value = " ".join(node.get_text(" ", strip=True).split())
    return value or None

def _is_series_url(url: str | None) -> bool:
    return bool(url and urlparse(url).path.startswith("/series/"))

def _slug_from_url(url: str) -> str:
    return urlparse(url).path.rstrip("/").split("/")[-1]

def parse_card(card: Tag) -> dict | None:
    link = card.select_one("a.lnk-blk[href], a[href*='/series/']")
    href = absolute_url(link.get("href")) if link else None
    if not _is_series_url(href):
        return None

    title_node = card.select_one(".entry-title, h2, h3, .title")
    image = card.select_one(".post-thumbnail img, img")
    rating_node = card.select_one(".entry-meta .vote, .vote")
    title = _text(title_node) or (image.get("alt", "").replace("Image ", "") if image else None)
    if not title:
        return None

    rating_text = _text(rating_node)
    rating = None
    if rating_text:
        match = re.search(r"(\d+(?:\.\d+)?)", rating_text)
        rating = float(match.group(1)) if match else None

    poster = None
    if image:
        poster = image.get("data-src") or image.get("data-lazy-src") or image.get("src")
        poster = absolute_url(poster)

    return {
        "title": title,
        "slug": _slug_from_url(href),
        "url": href,
        "poster": poster,
        "rating": rating,
        "type": "series",
    }

def parse_archive(html: str, source_url: str, page: int = 1) -> dict:
    soup = soup_of(html)
    cards = []
    seen = set()

    for card in soup.select("article.post, article, .post"):
        item = parse_card(card)
        if item and item["url"] not in seen:
            seen.add(item["url"])
            cards.append(item)

    heading = soup.select_one("h1, .archive-title, .page-title")
    title = _text(heading) or "Anime"

    pagination = []
    for anchor in soup.select(".pagination a[href], .nav-links a[href], a.page-numbers[href]"):
        href = absolute_url(anchor.get("href"))
        label = _text(anchor)
        if href and label and not any(p["url"] == href for p in pagination):
            pagination.append({"label": label, "url": href})

    total_text = None
    body_text = _text(soup.select_one("main")) or _text(soup.select_one("#aa-wp"))
    if body_text:
        match = re.search(r"([\d,]+)\s+Results", body_text, re.I)
        total_text = match.group(1) if match else None

    return {
        "success": True,
        "source": source_url,
        "title": title,
        "page": page,
        "total_results": int(total_text.replace(",", "")) if total_text else None,
        "count": len(cards),
        "results": cards,
        "pagination": pagination,
    }

def parse_home(html: str) -> dict:
    soup = soup_of(html)
    sections = []
    # Home page sections have headings followed by article.post cards.
    for section in soup.select("section, .section, .widget, .block"):
        heading = section.select_one("h2, h3, .section-title, .title")
        cards = []
        seen = set()
        for card in section.select("article.post, article, .post"):
            item = parse_card(card)
            if item and item["url"] not in seen:
                seen.add(item["url"])
                cards.append(item)
        if cards:
            sections.append({
                "title": _text(heading) or "Anime",
                "count": len(cards),
                "results": cards,
            })

    # Fallback: capture all series cards if the theme's sections are not semantic.
    if not sections:
        archive = parse_archive(html, f"{BASE_URL}/home")
        if archive["results"]:
            sections.append({"title": "Anime", "count": archive["count"], "results": archive["results"]})

    return {"success": True, "source": f"{BASE_URL}/home", "sections": sections}

def parse_detail(html: str, url: str) -> dict:
    soup = soup_of(html)
    title_node = soup.select_one("h1.entry-title, h1, .entry-title")
    overview_node = soup.select_one(".entry-content, .description, .entry-summary")
    overview = _text(overview_node)

    genres = []
    languages = []
    meta = soup.select("ul li")
    for li in meta:
        label = _text(li.select_one("span, strong, b"))
        links = [{"name": _text(a), "url": absolute_url(a.get("href"))}
                 for a in li.select("a[href]") if _text(a)]
        if label and "genre" in label.lower():
            genres.extend(links)
        elif label and "language" in label.lower():
            languages.extend(links)

    seasons = []
    for a in soup.select("a.season-btn[href], a.season-btn[data-slug]"):
        href = absolute_url(a.get("href")) if a.get("href") else None
        slug = a.get("data-slug")
        if not href and slug:
            href = f"{BASE_URL}/series/{slug}/"
        name = _text(a)
        if href and name and not any(x["url"] == href for x in seasons):
            num = re.search(r"(\d+)", name)
            seasons.append({"name": name, "season": int(num.group(1)) if num else None,
                            "slug": _slug_from_url(href), "url": href})

    episodes = []
    for a in soup.select("a[href*='/episode/']"):
        href = absolute_url(a.get("href"))
        name = _text(a)
        if href and name and not any(x["url"] == href for x in episodes):
            match = re.search(r"(?:episode\s*)?(\d+)", name, re.I)
            episodes.append({"title": name, "episode": int(match.group(1)) if match else None,
                             "slug": _slug_from_url(href), "url": href})

    poster_node = soup.select_one(".post-thumbnail img, .entry-content img, img.wp-post-image")
    poster = None
    if poster_node:
        poster = absolute_url(poster_node.get("data-src") or poster_node.get("src"))

    return {
        "success": True,
        "title": _text(title_node),
        "slug": _slug_from_url(url),
        "url": url,
        "poster": poster,
        "overview": overview,
        "genres": genres,
        "languages": languages,
        "seasons": seasons,
        "episodes": episodes,
        "episode_count": len(episodes),
    }

def parse_downloads(soup: BeautifulSoup) -> list[dict]:
    """Parse the public Download Links modal; retain the source-provided link."""
    downloads = []
    for row in soup.select("#mdl-download .download-links tbody tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 4:
            continue

        server_cell = cells[0]
        number_node = server_cell.select_one(".num")
        number = _text(number_node)
        server_name = _text(server_cell)
        if number and server_name.startswith(number):
            server_name = server_name[len(number):].strip()

        link_node = cells[3].select_one("a[href]")
        download_url = absolute_url(link_node.get("href")) if link_node else None
        if not download_url:
            continue

        downloads.append({
            "number": number,
            "server": server_name,
            "quality": _text(cells[1]),
            "audio": _text(cells[2]),
            "url": download_url,
            "label": _text(link_node) or "Download",
        })
    return downloads


def parse_episode(html: str, url: str) -> dict:
    soup = soup_of(html)
    title = _text(soup.select_one("h1.entry-title, h1, .entry-title"))
    poster_node = soup.select_one(".post-thumbnail img, img.wp-post-image")
    poster = absolute_url(poster_node.get("src")) if poster_node else None
    parent = soup.select_one("a[href*='/series/']")
    season_links = []
    for a in soup.select("a.season-btn[href], a.season-btn[data-slug]"):
        href = absolute_url(a.get("href")) if a.get("href") else None
        if not href and a.get("data-slug"):
            href = f"{BASE_URL}/series/{a['data-slug']}/"
        if href:
            season_links.append({"name": _text(a), "url": href})

    downloads = parse_downloads(soup)
    return {
        "success": True,
        "title": title,
        "slug": _slug_from_url(url),
        "url": url,
        "poster": poster,
        "series_url": absolute_url(parent.get("href")) if parent else None,
        "seasons": season_links,
        "download_count": len(downloads),
        "downloads": downloads,
    }

def parse_taxonomy_links(html: str, selector: str) -> list[dict]:
    soup = soup_of(html)
    results, seen = [], set()
    for a in soup.select(selector):
        href = absolute_url(a.get("href"))
        name = _text(a)
        if href and name and href not in seen:
            seen.add(href)
            results.append({"name": name, "slug": urlparse(href).path.rstrip("/").split("/")[-1], "url": href})
    return results
