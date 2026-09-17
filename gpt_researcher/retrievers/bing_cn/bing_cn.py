"""Bing China web search retriever.

This retriever uses the public Bing China search page instead of a paid search
API. It returns result URLs that still need to be scraped by GPT Researcher.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from ..base import BaseRetriever


class BingCNSearch(BaseRetriever):
    """Search Bing China web results without requiring an API key."""

    requires_scraping = True

    BASE_URL = "https://cn.bing.com/search"
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

        blocked_domains = {
            "bing.com",
            "cn.bing.com",
            "www.bing.com",
            "youtube.com",
            "www.youtube.com",
        }
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        blocked = any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in blocked_domains
        )
        if blocked:
            return False

        bad_markers = (
            "mail.",
            "filehelper.weixin.qq.com",
            "/login",
            "/signin",
            "/feedback",
        )
        return not any(marker in url.lower() for marker in bad_markers)

    @staticmethod
    def _query_terms(text: str) -> set[str]:
        lowered = (text or "").lower()
        terms = set(re.findall(r"[a-z0-9]{2,}", lowered))
        terms.update(re.findall(r"[\u4e00-\u9fff]{2,8}", lowered))
        return {term for term in terms if term}

    @classmethod
    def _is_relevant(cls, query: str, title: str, snippet: str) -> bool:
        query_terms = cls._query_terms(query)
        if not query_terms:
            return True

        haystack = f"{title} {snippet}".lower()
        return any(term in haystack for term in query_terms)

    def search(self, max_results: int = 7) -> list[dict[str, Any]]:
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        }
        results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        first = 1
        page_count = 0

        try:
            while len(results) < max_results and page_count < 3:
                page_count += 1
                new_results = 0
                response = requests.get(
                    self.BASE_URL,
                    params={
                        "q": self._build_query(),
                        "first": first,
                        "mkt": "zh-CN",
                        "setlang": "zh-hans",
                    },
                    headers=headers,
                    timeout=12,
                )
                response.raise_for_status()
                response.encoding = response.apparent_encoding or "utf-8"
                soup = BeautifulSoup(response.text, "html.parser")

                page_items = soup.select("li.b_algo")
                if not page_items:
                    break

                for item in page_items:
                    title_link = item.select_one("h2 a")
                    if title_link is None:
                        continue

                    url = (title_link.get("href") or "").strip()
                    if not self._is_valid_result(url) or url in seen_urls:
                        continue

                    snippet_node = (
                        item.select_one(".b_caption p")
                        or item.select_one(".b_snippet")
                        or item.select_one("p")
                    )
                    snippet = (
                        snippet_node.get_text(" ", strip=True)
                        if snippet_node is not None
                        else ""
                    )
                    title = title_link.get_text(" ", strip=True)
                    if not self._is_relevant(self.query, title, snippet):
                        continue

                    seen_urls.add(url)
                    new_results += 1
                    results.append(
                        {
                            "title": title,
                            "href": url,
                            "body": snippet,
                        }
                    )
                    if len(results) >= max_results:
                        break

                if new_results == 0:
                    break
                first += len(page_items)

        except requests.RequestException as exc:
            self.logger.error("Bing China search failed for %r: %s", self.query, exc)
            return results

        if not results:
            self.logger.warning("No Bing China results found for query: %s", self.query)

        return results
