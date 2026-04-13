from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin


class _AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value.strip())
                break


def extract_links_from_html(*, base_url: str, html: str) -> list[str]:
    parser = _AnchorParser()
    parser.feed(html or "")
    links: list[str] = []
    for href in parser.hrefs:
        links.append(urljoin(base_url, href))
    return links
