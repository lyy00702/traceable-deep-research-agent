"""360 Search retriever for Chinese web search."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from ..base import BaseRetriever


class SoCNSearch(BaseRetriever):
    """Search 360 China without requiring a paid API key."""

    requires_scraping = True

    BASE_URL = "https://www.so.com/s"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )

    def __init__(self, query: str, query_domains=None):
        self.query = query
        self.query_domains = query_domains or None
        self.logger = logging.getLogger(__name__)

    def _build_query(self) -> str:
        if not self.query_domains:
            return self.query

        domains = [
            domain.strip()
            for domain in self.query_domains
            if isinstance(domain, str) and domain.strip()
        ]
        if not domains:
            return self.query

        site_filter = " OR ".join(f"site:{domain}" for domain in domains)
        return f"{self.query} ({site_filter})"

    @staticmethod
    def _is_valid_result(url: str) -> bool:
        if not url:
            return False

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False

        hostname = parsed.hostname.lower() if parsed.hostname else ""
        blocked_hosts = {
            "so.com",
            "www.so.com",
            "image.so.com",
            "ai.so.com",
            "tv.360kan.com",
            "www.360kan.com",
        }
        return hostname not in blocked_hosts

    def search(self, max_results: int = 7) -> list[dict[str, Any]]:
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        }

        try:
            response = requests.get(
                self.BASE_URL,
                params={"q": self._build_query()},
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
        except requests.RequestException as exc:
            self.logger.error("360 search failed for %r: %s", self.query, exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for item in soup.select("li.res-list"):
            title_link = item.select_one("h3 a")
            if title_link is None:
                continue

            url = (
                title_link.get("data-mdurl")
                or title_link.get("data-cache")
                or title_link.get("href")
                or ""
            ).strip()
            if not self._is_valid_result(url) or url in seen_urls:
                continue

            snippet_node = item.select_one(".res-desc") or item.select_one("p")
            snippet = (
                snippet_node.get_text(" ", strip=True)
                if snippet_node is not None
                else ""
            )

            seen_urls.add(url)
            results.append(
                {
                    "title": title_link.get_text(" ", strip=True),
                    "href": url,
                    "body": snippet,
                }
            )
            if len(results) >= max_results:
                break

        if not results:
            self.logger.warning("No 360 results found for query: %s", self.query)

        return results
