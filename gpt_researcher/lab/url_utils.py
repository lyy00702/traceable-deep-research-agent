"""URL normalization and deterministic de-duplication helpers."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_QUERY_PREFIXES = (
    "utm_",
    "spm",
    "from",
    "source",
    "ref",
    "refer",
    "share",
)

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "yclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
}


def normalize_url(url: str) -> str:
    """Return a stable URL form for deduplication."""
    if not url or not isinstance(url, str):
        return ""

    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()

    if not parts.scheme or not parts.netloc:
        return url.strip()

    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    if not hostname:
        return url.strip()

    port = parts.port
    if port and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")

    query_items = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_QUERY_KEYS:
            continue
        if any(lowered.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
            continue
        query_items.append((key, value))

    query = urlencode(sorted(query_items), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def dedupe_urls(urls) -> list[str]:
    """Normalize URLs while preserving first-seen order."""
    seen: set[str] = set()
    deduped: list[str] = []

    for url in urls:
        normalized = normalize_url(url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)

    return deduped
