from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def canonicalize_url(value: str | None) -> str | None:
    if not value:
        return None

    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None

    host = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port
    default_port = (parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443)
    if port and not default_port:
        netloc = f"{host}:{port}"
    else:
        netloc = host

    path = parsed.path or "/"
    query_pairs = sorted(parse_qsl(parsed.query, keep_blank_values=True))
    query = urlencode(query_pairs, doseq=True)

    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=netloc,
        path=path,
        params="",
        query=query,
        fragment="",
    )
    return urlunparse(normalized)


def is_same_origin(left: str, right: str) -> bool:
    l = urlparse(left)
    r = urlparse(right)

    l_port = l.port or (443 if l.scheme == "https" else 80)
    r_port = r.port or (443 if r.scheme == "https" else 80)

    l_host = (l.hostname or "").lower()
    r_host = (r.hostname or "").lower()
    if l_host.startswith("www."):
        l_host = l_host[4:]
    if r_host.startswith("www."):
        r_host = r_host[4:]

    return l.scheme == r.scheme and l_host == r_host and l_port == r_port


def _registrable_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    parts = [part for part in host.split(".") if part]
    if len(parts) < 2:
        return host
    return ".".join(parts[-2:])


def is_same_site(left: str, right: str) -> bool:
    return _registrable_domain(left) == _registrable_domain(right)


def scope_reason(*, root_url: str, candidate_url: str, same_origin_only: bool) -> str | None:
    if same_origin_only:
        if not is_same_origin(root_url, candidate_url):
            return "outside_origin"
        return None

    if not is_same_site(root_url, candidate_url):
        return "outside_site"
    return None
