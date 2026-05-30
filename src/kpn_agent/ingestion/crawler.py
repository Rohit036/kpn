import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from kpn_agent.common.hash_utils import sha1_hex
from kpn_agent.common.text_utils import normalize_whitespace
from kpn_agent.config import CrawlConfig


def _is_allowed(url: str, allowed_domain: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    return allowed_domain in parsed.netloc


def _should_keep_link(url: str) -> bool:
    lowered = url.lower()
    keywords = ["nieuws", "news", "press", "article", "bericht"]
    return any(word in lowered for word in keywords)


def _extract_text_and_title(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "footer", "nav"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = normalize_whitespace(soup.title.string)

    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = normalize_whitespace(main.get_text(" ", strip=True))
    return title, text


def _discover_links(base_url: str, html: str, allowed_domain: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for anchor in soup.select("a[href]"):
        url = urljoin(base_url, anchor["href"]).split("#")[0]
        if _is_allowed(url, allowed_domain) and _should_keep_link(url):
            links.append(url)
    return list(dict.fromkeys(links))


def crawl_news(config: CrawlConfig) -> List[Dict[str, Any]]:
    session = requests.Session()
    session.headers.update({"User-Agent": config.user_agent})

    visited = set()
    queue = deque([(config.seed_url, 0, "")])
    rows: List[Dict[str, Any]] = []

    while queue and len(visited) < config.max_pages:
        url, depth, parent_url = queue.popleft()
        if url in visited or depth > config.max_depth:
            continue

        visited.add(url)
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            html = response.text
        except Exception:
            continue

        title, text = _extract_text_and_title(html)
        if len(text) >= config.min_text_length:
            now = datetime.now(timezone.utc)
            rows.append(
                {
                    "doc_id": sha1_hex(url),
                    "url": url,
                    "parent_url": parent_url,
                    "title": title,
                    "text": text,
                    "source_type": "kpn_news",
                    "crawl_depth": depth,
                    "crawl_timestamp_utc": now.isoformat(),
                    "crawl_timestamp_epoch": int(now.timestamp()),
                    "status_code": int(response.status_code),
                    "text_char_len": len(text),
                    "content_hash": sha1_hex(text),
                }
            )

        if depth < config.max_depth:
            for next_url in _discover_links(url, html, config.allowed_domain):
                if next_url not in visited:
                    queue.append((next_url, depth + 1, url))

        time.sleep(config.request_delay_sec)

    return rows
