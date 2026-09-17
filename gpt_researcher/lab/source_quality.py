"""Explainable source quality scoring for research workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse


HIGH_TRUST_SUFFIXES = (
    ".gov.cn",
    ".edu.cn",
    ".ac.cn",
    ".gov",
    ".edu",
)

HIGH_TRUST_DOMAINS = {
    "github.com",
    "arxiv.org",
    "openai.com",
    "nature.com",
    "science.org",
    "ieee.org",
    "acm.org",
}

LOW_TRUST_DOMAINS = {
    "zhihu.com",
    "baidu.com",
    "baijiahao.baidu.com",
    "csdn.net",
    "sohu.com",
    "36kr.com",
}


def _domain_trust(url: str) -> tuple[float, str]:
    hostname = (urlparse(url).hostname or "").lower()
    if not hostname:
        return 0.0, "invalid-domain"

    if hostname in HIGH_TRUST_DOMAINS or hostname.endswith(HIGH_TRUST_SUFFIXES):
        return 1.0, "authoritative-domain"

    if any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in LOW_TRUST_DOMAINS
    ):
        return 0.35, "user-generated-or-commercial"

    return 0.55, "general-web"


def _completeness(title: str, content: str) -> tuple[float, str]:
    title_length = len((title or "").strip())
    content_length = len((content or "").strip())

    if title_length >= 8 and content_length >= 2000:
        return 1.0, "substantial-content"
    if title_length >= 4 and content_length >= 500:
        return 0.7, "moderate-content"
    return 0.3, "thin-content"


def _recency(published_at: str | None) -> tuple[float, str]:
    if not published_at:
        return 0.5, "unknown-date"

    try:
        normalized = published_at.replace("Z", "+00:00")
        published = datetime.fromisoformat(normalized)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        age_days = max(
            0,
            (datetime.now(timezone.utc) - published.astimezone(timezone.utc)).days,
        )
    except (TypeError, ValueError):
        return 0.5, "unknown-date"

    if age_days <= 365:
        return 1.0, "recent"
    if age_days <= 365 * 3:
        return 0.75, "current"
    return 0.45, "older"


def score_source(
    url: str,
    *,
    title: str = "",
    content: str = "",
    published_at: str | None = None,
) -> dict:
    """Return a transparent source score and its component reasons."""
    trust, trust_reason = _domain_trust(url)
    completeness, completeness_reason = _completeness(title, content)
    recency, recency_reason = _recency(published_at)

    score = round(
        0.45 * trust + 0.35 * completeness + 0.20 * recency,
        4,
    )

    return {
        "url": url,
        "score": score,
        "components": {
            "domain_trust": trust,
            "completeness": completeness,
            "recency": recency,
        },
        "reasons": [
            trust_reason,
            completeness_reason,
            recency_reason,
        ],
    }
