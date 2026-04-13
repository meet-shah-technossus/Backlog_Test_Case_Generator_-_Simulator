from __future__ import annotations

import re
from html.parser import HTMLParser


class _SnapshotParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_title = False
        self._skip_depth = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        lower = tag.lower()
        if lower in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if lower == "title":
            self._in_title = True

    def handle_endtag(self, tag: str):
        lower = tag.lower()
        if lower in {"script", "style", "noscript"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if lower == "title":
            self._in_title = False

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return
        text = (data or "").strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
            return
        self.text_parts.append(text)


def extract_page_snapshot(*, html: str, excerpt_chars: int = 500) -> dict:
    parser = _SnapshotParser()
    parser.feed(html or "")

    title = " ".join(parser.title_parts).strip()
    full_text = " ".join(parser.text_parts).strip()
    full_text = re.sub(r"\s+", " ", full_text)

    excerpt = full_text
    if excerpt_chars > 0 and len(excerpt) > excerpt_chars:
        excerpt = excerpt[:excerpt_chars].rstrip() + "..."

    return {
        "title": title,
        "text_excerpt": excerpt,
    }
