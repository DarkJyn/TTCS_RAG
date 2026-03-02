#!/usr/bin/env python
import argparse
import re
import time
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


DEFAULT_START_URL = "https://thuvienphapluat.vn/"
USER_AGENT = "RAGResearchBot/1.0 (+https://thuvienphapluat.vn/)"


def normalize_filename(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:120] or "document"


def is_valid_domain(url: str, base_domain: str) -> bool:
    try:
        return urlparse(url).netloc.endswith(base_domain)
    except Exception:
        return False


def extract_links(html: str, base_url: str) -> Iterable[str]:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        yield urljoin(base_url, href)


def extract_text(html: str) -> Tuple[str, Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")

    title = None
    title_tag = soup.find("h1")
    if title_tag:
        title = title_tag.get_text(strip=True)

    content = None
    selectors = [
        "#content", "#divContent", ".content", ".article-content", ".main-content",
    ]
    for sel in selectors:
        node = soup.select_one(sel)
        if node:
            content = node
            break

    if content is None:
        content = soup.body

    text = content.get_text("\n", strip=True) if content else ""
    return text, title


def should_save(url: str) -> bool:
    return "/van-ban/" in url or "/vanban/" in url


def fetch(url: str, session: requests.Session, timeout: int) -> Optional[str]:
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code != 200:
            return None
        return resp.text
    except requests.RequestException:
        return None


def crawl(
    start_url: str,
    output_dir: Path,
    max_pages: int,
    delay: float,
    timeout: int,
) -> None:
    base_domain = urlparse(start_url).netloc
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    visited: Set[str] = set()
    queue: List[str] = [start_url]
    saved = 0

    while queue and saved < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        if not is_valid_domain(url, base_domain):
            continue

        html = fetch(url, session, timeout)
        if not html:
            continue

        if should_save(url):
            text, title = extract_text(html)
            if text:
                name_base = normalize_filename(title or urlparse(url).path)
                output_path = output_dir / f"{name_base}.txt"
                output_path.write_text(text, encoding="utf-8")
                saved += 1

        for link in extract_links(html, url):
            if link not in visited and is_valid_domain(link, base_domain):
                queue.append(link)

        time.sleep(delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl legal texts from thuvienphapluat.vn")
    parser.add_argument("--start-url", default=DEFAULT_START_URL)
    parser.add_argument("--output-dir", default="input_docs")
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    crawl(
        start_url=args.start_url,
        output_dir=output_dir,
        max_pages=args.max_pages,
        delay=args.delay,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
