from __future__ import annotations

import logging
import random
import re
import time
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from models import ChapterPayload, Verse

logger = logging.getLogger(__name__)


DEFAULT_ENTRY_URL = "https://thekingsbible.com/Bible/1/1"
DEFAULT_THEKINGSBIBLE_KJV_BASE_URL = "https://thekingsbible.com/Bible"
DEFAULT_BSKOREA_NKRV_ENTRY_URL = (
    "https://www.bskorea.or.kr/bible/korbibReadpage.php"
    "?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
)
# 1-based chapter counts for Genesis..Revelation (66 books).
KJV_CHAPTER_COUNTS: tuple[int, ...] = (
    50, 40, 27, 36, 34, 24, 21, 4, 31, 24, 22, 25, 29, 36, 10, 13, 10, 42, 150,
    31, 12, 8, 66, 52, 5, 48, 12, 14, 3, 9, 1, 4, 7, 3, 3, 3, 2, 14, 4, 28, 16,
    24, 21, 28, 16, 16, 13, 6, 6, 4, 4, 5, 3, 6, 4, 3, 1, 13, 5, 5, 3, 5, 1, 1,
    1, 22,
)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)
MIN_VERSE_NUMBER = 1
MAX_VERSE_NUMBER = 200
BSKOREA_BOOK_CODES: tuple[str, ...] = (
    "gen", "exo", "lev", "num", "deu", "jos", "jdg", "rut", "1sa", "2sa", "1ki", "2ki",
    "1ch", "2ch", "ezr", "neh", "est", "job", "psa", "pro", "ecc", "sng", "isa", "jer",
    "lam", "ezk", "dan", "hos", "jol", "amo", "oba", "jon", "mic", "nam", "hab", "zep",
    "hag", "zec", "mal", "mat", "mrk", "luk", "jhn", "act", "rom", "1co", "2co", "gal",
    "eph", "php", "col", "1th", "2th", "1ti", "2ti", "tit", "phm", "heb", "jas", "1pe",
    "2pe", "1jn", "2jn", "3jn", "jud", "rev",
)


class RetryableHttpError(RuntimeError):
    """Raised for retryable HTTP status (e.g., 502/503)."""


@dataclass(slots=True)
class NavigationTemplate:
    sample_url: str
    book_param: str
    chapter_param: str


class HolyBibleScraper:
    """Scraper that discovers source navigation and parses chapter/verse content."""

    def __init__(
        self,
        entry_url: str = DEFAULT_ENTRY_URL,
        timeout: int = 20,
        sleep_min: float = 0.3,
        sleep_max: float = 1.0,
        max_discovery_pages: int = 40,
    ) -> None:
        self.entry_url = entry_url
        self.timeout = timeout
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
        self.max_discovery_pages = max_discovery_pages
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
        self._throttle_multiplier = 1.0

        self._navigation_template: NavigationTemplate | None = None
        self._chapter_cache: dict[tuple[int, int], ChapterPayload] = {}
        self._chapter_url_cache: dict[int, dict[int, str]] = {}

    def close(self) -> None:
        self.session.close()

    def get_source_name(self) -> str:
        if self._is_thekingsbible_source():
            return "thekingsbible"
        if self._is_bskorea_source():
            return "bskorea"
        return "generic"

    def parse_verses_from_html(self, html: str) -> list[Verse]:
        soup = BeautifulSoup(html, "html.parser")
        return self._sanitize_verses(self._extract_verses(soup))

    @retry(
        retry=retry_if_exception_type((RetryableHttpError, requests.RequestException)),
        wait=wait_random_exponential(multiplier=1, max=30),
        stop=stop_after_attempt(7),
        reraise=True,
    )
    def _request_html(self, url: str) -> str:
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code == 429:
            retry_after = self._parse_retry_after_seconds(response.headers.get("Retry-After"))
            cooldown = retry_after if retry_after is not None else 8
            self._throttle_multiplier = min(6.0, self._throttle_multiplier * 1.5)
            logger.warning(
                "429 Too Many Requests for %s; waiting %ss before retry (throttle x%.2f)",
                url,
                cooldown,
                self._throttle_multiplier,
            )
            time.sleep(cooldown)
            raise RetryableHttpError(f"Retryable status=429 url={url}")

        if response.status_code in (502, 503, 504):
            raise RetryableHttpError(f"Retryable status={response.status_code} url={url}")
        response.raise_for_status()
        html = response.text

        # Some providers return HTTP 200 with a rate-limit/error body.
        if self._looks_like_rate_limited_html(html):
            cooldown = 8
            self._throttle_multiplier = min(6.0, self._throttle_multiplier * 1.5)
            logger.warning(
                "Rate-limit/error page detected for %s; waiting %ss before retry (throttle x%.2f)",
                url,
                cooldown,
                self._throttle_multiplier,
            )
            time.sleep(cooldown)
            raise RetryableHttpError(f"Retryable body indicates rate limit/error url={url}")

        # Polite crawling delay to reduce blocking risk.
        delay = random.uniform(self.sleep_min, self.sleep_max) * self._throttle_multiplier
        time.sleep(delay)
        # Gradually decay throttle after successful requests.
        self._throttle_multiplier = max(1.0, self._throttle_multiplier * 0.95)
        return html

    @staticmethod
    def _parse_retry_after_seconds(value: str | None) -> int | None:
        if not value:
            return None

        raw = value.strip()
        if not raw:
            return None

        if raw.isdigit():
            return max(1, int(raw))

        try:
            dt = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None

        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        seconds = int((dt - datetime.now(timezone.utc)).total_seconds())
        return max(1, seconds)

    @staticmethod
    def _looks_like_rate_limited_html(html: str) -> bool:
        sample = html.lower()
        return (
            ("too many requests" in sample)
            or ("error 429" in sample)
            or ("429 error" in sample)
            or ("status code: 429" in sample)
            or ("rate limit" in sample)
        )

    def _fetch_soup(self, url: str) -> BeautifulSoup:
        html = self._request_html(url)
        return BeautifulSoup(html, "html.parser")

    def _collect_candidate_urls(self) -> set[str]:
        """Crawl a small graph from entry URL and collect candidate scripture links."""
        visited: set[str] = set()
        discovered: set[str] = set()
        queue: deque[str] = deque([self.entry_url])
        base_domain = urlparse(self.entry_url).netloc

        while queue and len(visited) < self.max_discovery_pages:
            url = queue.popleft()
            if url in visited:
                continue

            visited.add(url)
            try:
                soup = self._fetch_soup(url)
            except Exception:
                continue

            if self._url_has_digit_query_param(url):
                discovered.add(url)

            for anchor in soup.find_all("a", href=True):
                href = anchor.get("href", "").strip()
                if not href:
                    continue
                if href.startswith(("javascript:", "mailto:", "tel:")):
                    continue

                absolute = urljoin(url, href)
                parsed = urlparse(absolute)
                if parsed.netloc and parsed.netloc != base_domain:
                    continue
                if parsed.scheme and parsed.scheme not in ("http", "https"):
                    continue
                absolute = absolute.split("#", 1)[0]

                if (
                    absolute not in visited
                    and absolute not in queue
                    and len(visited) + len(queue) < self.max_discovery_pages
                ):
                    queue.append(absolute)

                if self._looks_like_scripture_link(absolute, anchor.get_text(" ", strip=True)):
                    discovered.add(absolute)
                    continue
                if self._url_has_digit_query_param(absolute):
                    discovered.add(absolute)

        discovered.add(self.entry_url)
        return discovered

    @staticmethod
    def _url_has_digit_query_param(url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.query:
            return False
        for _, value in parse_qsl(parsed.query, keep_blank_values=True):
            if value.isdigit():
                return True
        return False

    @staticmethod
    def _looks_like_scripture_link(url: str, text: str) -> bool:
        u = url.lower()
        t = text.lower()
        keywords = (
            "kjv",
            "bible",
            "holy",
            "thekingsbible",
            "book",
            "chapter",
            "verse",
            "genesis",
            "revelation",
        )
        if any(k in u for k in keywords) or any(k in t for k in keywords):
            return True

        parsed = urlparse(url)
        if parsed.query:
            for _, value in parse_qsl(parsed.query, keep_blank_values=True):
                if value.isdigit():
                    return True
        return False

    @staticmethod
    def _infer_navigation_templates(urls: Iterable[str]) -> list[NavigationTemplate]:
        param_values: dict[str, set[int]] = {}
        parsed_urls: list[tuple[str, dict[str, int]]] = []

        for url in urls:
            params = {}
            for key, value in parse_qsl(urlparse(url).query, keep_blank_values=True):
                if value.isdigit():
                    params[key] = int(value)
                    param_values.setdefault(key, set()).add(int(value))
            if params:
                parsed_urls.append((url, params))

        if not param_values:
            return []

        candidates: list[tuple[tuple[int, int, int, int, int, int], NavigationTemplate]] = []

        for book_param, book_values in param_values.items():
            if max(book_values) > 200:
                continue
            for chapter_param, chapter_values in param_values.items():
                if chapter_param == book_param:
                    continue
                if max(chapter_values) > 200:
                    continue

                sample_url = None
                for url, params in parsed_urls:
                    if book_param in params and chapter_param in params:
                        sample_url = url
                        break
                if sample_url is None:
                    continue

                score = (
                    0 if max(book_values) <= 66 else 1,
                    abs(len(book_values) - 66),
                    0 if max(chapter_values) >= 20 else 1,
                    -len(chapter_values),
                    -max(chapter_values),
                    0 if len(book_values) >= 2 else 1,
                )
                candidates.append(
                    (
                        score,
                        NavigationTemplate(
                            sample_url=sample_url,
                            book_param=book_param,
                            chapter_param=chapter_param,
                        ),
                    )
                )

        candidates.sort(key=lambda item: item[0])
        templates: list[NavigationTemplate] = []
        seen_pairs: set[tuple[str, str]] = set()
        for _, template in candidates:
            pair = (template.book_param, template.chapter_param)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            templates.append(template)
        return templates

    def _build_chapter_url_from_template(
        self,
        template: NavigationTemplate,
        book_order: int,
        chapter_number: int,
    ) -> str:
        url = template.sample_url
        url = self._replace_query_param(url, template.book_param, book_order)
        url = self._replace_query_param(url, template.chapter_param, chapter_number)
        return url

    def _validate_navigation_template(self, template: NavigationTemplate) -> bool:
        # Check a few canonical points to avoid selecting wrong numeric params.
        probes = ((1, 1), (1, 2), (2, 1))
        success_count = 0
        for book_order, chapter_number in probes:
            try:
                url = self._build_chapter_url_from_template(template, book_order, chapter_number)
                soup = self._fetch_soup(url)
                verses = self._extract_verses(soup)
            except Exception:
                continue
            if verses:
                success_count += 1
            if success_count >= 2:
                return True
        return False

    def _ensure_navigation_template(self) -> NavigationTemplate:
        if self._navigation_template is not None:
            return self._navigation_template

        urls = self._collect_candidate_urls()
        templates = self._infer_navigation_templates(urls)
        if not templates:
            raise RuntimeError(
                "Could not infer book/chapter query parameters from entry page. "
                "Set a more specific --entry-url (KJV first page)."
            )

        for template in templates[:8]:
            if self._validate_navigation_template(template):
                self._navigation_template = template
                return template

        # Keep progress by using best-ranked candidate even when validation is inconclusive.
        fallback = templates[0]
        logger.warning(
            "Using unvalidated navigation template fallback (book_param=%s, chapter_param=%s)",
            fallback.book_param,
            fallback.chapter_param,
        )
        self._navigation_template = fallback
        return fallback

    def _is_thekingsbible_source(self) -> bool:
        host = urlparse(self.entry_url).netloc.lower()
        return "thekingsbible.com" in host

    def _is_bskorea_source(self) -> bool:
        parsed = urlparse(self.entry_url)
        host = parsed.netloc.lower()
        return ("bskorea.or.kr" in host) or parsed.path.endswith("korbibReadpage.php")

    def _build_thekingsbible_url(self, book_order: int, chapter_number: int) -> str:
        # thekingsbible KJV rule:
        # Genesis 1 -> /Bible/1/1, Exodus 1 -> /Bible/2/1 ...
        return f"{DEFAULT_THEKINGSBIBLE_KJV_BASE_URL}/{book_order}/{chapter_number}"

    @staticmethod
    def _get_bskorea_book_code(book_order: int) -> str | None:
        if 1 <= book_order <= len(BSKOREA_BOOK_CODES):
            return BSKOREA_BOOK_CODES[book_order - 1]
        return None

    def _build_bskorea_url(
        self,
        book_order: int,
        chapter_number: int,
        book_code: str | None = None,
    ) -> str:
        book_code = (book_code or self._get_bskorea_book_code(book_order))
        if book_code is None:
            raise ValueError(f"Invalid bskorea book order: {book_order}")

        parsed = urlparse(self.entry_url or DEFAULT_BSKOREA_NKRV_ENTRY_URL)
        path = parsed.path or "/bible/korbibReadpage.php"
        base_url = urlunparse(parsed._replace(path=path, params="", query="", fragment=""))

        entry_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query_params = {
            "version": entry_params.get("version", "GAE"),
            "book": book_code,
            "chap": str(chapter_number),
            "sec": "1",
            "cVersion": entry_params.get("cVersion", ""),
            "fontSize": entry_params.get("fontSize", "15px"),
            "fontWeight": entry_params.get("fontWeight", "normal"),
        }

        return f"{base_url}?{urlencode(query_params, doseq=True)}"

    @staticmethod
    def _get_kjv_chapter_count(book_order: int) -> int | None:
        if 1 <= book_order <= len(KJV_CHAPTER_COUNTS):
            return KJV_CHAPTER_COUNTS[book_order - 1]
        return None

    @staticmethod
    def _replace_query_param(url: str, key: str, value: str | int) -> str:
        parsed = urlparse(url)
        qsl = parse_qsl(parsed.query, keep_blank_values=True)
        new_qsl = []
        replaced = False

        for q_key, q_val in qsl:
            if q_key == key:
                new_qsl.append((q_key, str(value)))
                replaced = True
            else:
                new_qsl.append((q_key, q_val))

        if not replaced:
            new_qsl.append((key, str(value)))

        updated = parsed._replace(query=urlencode(new_qsl, doseq=True))
        return urlunparse(updated)

    def _build_chapter_url(
        self,
        book_order: int,
        chapter_number: int,
        book_code: str | None = None,
    ) -> str:
        if self._is_thekingsbible_source():
            return self._build_thekingsbible_url(book_order, chapter_number)
        if self._is_bskorea_source():
            return self._build_bskorea_url(book_order, chapter_number, book_code=book_code)
        template = self._ensure_navigation_template()
        return self._build_chapter_url_from_template(template, book_order, chapter_number)

    def _extract_chapter_links_from_soup(self, soup: BeautifulSoup, book_order: int) -> dict[int, str]:
        links: dict[int, str] = {}
        template = self._ensure_navigation_template()

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "").strip()
            if not href:
                continue

            url = urljoin(self.entry_url, href)
            params = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
            book_raw = params.get(template.book_param)
            chapter_raw = params.get(template.chapter_param)

            if not (book_raw and book_raw.isdigit() and chapter_raw and chapter_raw.isdigit()):
                continue

            if int(book_raw) != book_order:
                continue

            chapter_num = int(chapter_raw)
            if not (1 <= chapter_num <= 200):
                continue

            links[chapter_num] = url

        return dict(sorted(links.items()))

    def discover_chapter_urls_for_book(
        self,
        book_order: int,
        book_code: str | None = None,
    ) -> dict[int, str]:
        if book_order in self._chapter_url_cache:
            return self._chapter_url_cache[book_order]

        if self._is_thekingsbible_source():
            chapter_urls = self._discover_chapter_urls_for_thekingsbible(book_order)
            self._chapter_url_cache[book_order] = chapter_urls
            return chapter_urls
        if self._is_bskorea_source():
            chapter_urls = self._discover_chapter_urls_for_bskorea(book_order, book_code=book_code)
            self._chapter_url_cache[book_order] = chapter_urls
            return chapter_urls

        chapter_urls: dict[int, str] = {}
        first_url = self._build_chapter_url(book_order, 1, book_code=book_code)
        first_soup = self._fetch_soup(first_url)

        first_verses = self._extract_verses(first_soup)
        if first_verses:
            self._chapter_cache[(book_order, 1)] = ChapterPayload(
                book_order=book_order,
                chapter_number=1,
                source_url=first_url,
                verses=first_verses,
            )
            chapter_urls[1] = first_url

        chapter_links_from_page = self._extract_chapter_links_from_soup(first_soup, book_order)
        chapter_urls.update(chapter_links_from_page)
        if 1 not in chapter_urls:
            chapter_urls[1] = first_url

        # Fallback: when chapter links are not visible in HTML, probe chapter URLs sequentially.
        if len(chapter_urls) <= 1:
            consecutive_miss = 0
            found_any = bool(first_verses)
            for chapter_num in range(1, 201):
                if chapter_num == 1:
                    if first_verses:
                        consecutive_miss = 0
                    else:
                        consecutive_miss = 1
                    continue

                url = self._build_chapter_url(book_order, chapter_num, book_code=book_code)
                payload = self.fetch_chapter_payload(book_order, chapter_num, url, book_code=book_code)
                if payload.verses:
                    chapter_urls[chapter_num] = url
                    consecutive_miss = 0
                    found_any = True
                else:
                    consecutive_miss += 1

                if found_any and consecutive_miss >= 2:
                    break
                if not found_any and consecutive_miss >= 8:
                    break

        chapter_urls = dict(sorted(chapter_urls.items()))
        self._chapter_url_cache[book_order] = chapter_urls
        return chapter_urls

    def _discover_chapter_urls_for_thekingsbible(self, book_order: int) -> dict[int, str]:
        """
        Discover chapters using thekingsbible KJV path rule.
        Uses canonical chapter counts for deterministic discovery.
        """
        chapter_count = self._get_kjv_chapter_count(book_order)
        if chapter_count is None:
            return {}

        chapter_urls = {
            chapter_num: self._build_thekingsbible_url(book_order, chapter_num)
            for chapter_num in range(1, chapter_count + 1)
        }
        return chapter_urls

    def _discover_chapter_urls_for_bskorea(
        self,
        book_order: int,
        book_code: str | None = None,
    ) -> dict[int, str]:
        chapter_count = self._get_kjv_chapter_count(book_order)
        if chapter_count is None:
            return {}

        return {
            chapter_num: self._build_bskorea_url(book_order, chapter_num, book_code=book_code)
            for chapter_num in range(1, chapter_count + 1)
        }

    def fetch_chapter_payload(
        self,
        book_order: int,
        chapter_number: int,
        chapter_url: str | None = None,
        book_code: str | None = None,
    ) -> ChapterPayload:
        cache_key = (book_order, chapter_number)
        if cache_key in self._chapter_cache:
            return self._chapter_cache[cache_key]

        url = chapter_url or self._build_chapter_url(book_order, chapter_number, book_code=book_code)
        soup = self._fetch_soup(url)
        verses = self._sanitize_verses(self._extract_verses(soup))

        payload = ChapterPayload(
            book_order=book_order,
            chapter_number=chapter_number,
            source_url=url,
            verses=verses,
        )
        self._chapter_cache[cache_key] = payload
        return payload

    def _extract_verses(self, soup: BeautifulSoup) -> list[Verse]:
        bskorea_verses = self._extract_verses_from_bskorea_read_page(soup)
        if bskorea_verses:
            return bskorea_verses

        bibletable_verses = self._extract_verses_from_bibletable(soup)
        if bibletable_verses:
            return bibletable_verses

        chapter_prefixed = self._extract_verses_from_chapter_prefixed_lines(soup)
        if chapter_prefixed:
            return chapter_prefixed

        ordered_list_verses = self._extract_verses_from_ordered_list(soup)
        if ordered_list_verses:
            return ordered_list_verses

        structured = self._extract_verses_from_structured_nodes(soup)
        if structured:
            return structured

        return self._extract_verses_with_regex_fallback(soup)

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _sanitize_verses(self, verses: list[Verse]) -> list[Verse]:
        cleaned: list[Verse] = []
        seen_numbers: set[int] = set()

        for verse in sorted(verses, key=lambda v: v.verse_number):
            if verse.verse_number < MIN_VERSE_NUMBER or verse.verse_number > MAX_VERSE_NUMBER:
                continue
            text = self._normalize_text(verse.text)
            if not text:
                continue
            if verse.verse_number in seen_numbers:
                continue

            # Guard against parsed error pages (e.g., "429 Error").
            lowered = text.lower()
            if lowered in {"error", "too many requests"}:
                continue

            seen_numbers.add(verse.verse_number)
            cleaned.append(Verse(verse_number=verse.verse_number, text=text))

        return cleaned

    def _get_bskorea_content_root(self, soup: BeautifulSoup) -> Tag | None:
        root = soup.select_one("#tdBible1.bible_read")
        if root is not None:
            return root

        candidates = soup.select("div.bible_read")
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _extract_verses_from_bskorea_read_page(self, soup: BeautifulSoup) -> list[Verse]:
        container = self._get_bskorea_content_root(soup)
        if container is None:
            return []

        verses: list[Verse] = []
        for verse_node in container.find_all("span", recursive=False):
            number_node = verse_node.find("span", class_="number")
            if number_node is None:
                continue

            number_match = re.search(r"(\d{1,3})", number_node.get_text(" ", strip=True))
            if not number_match:
                continue
            verse_number = int(number_match.group(1))

            verse_clone_soup = BeautifulSoup(str(verse_node), "html.parser")
            verse_clone = verse_clone_soup.find("span")
            if verse_clone is None:
                continue

            for removable in verse_clone.select("span.number, a.comment, div.D2"):
                removable.decompose()

            for hidden in verse_clone.find_all(style=True):
                style = hidden.get("style", "")
                if isinstance(style, str) and "display:none" in style.lower().replace(" ", ""):
                    hidden.decompose()

            # Preserve source whitespace between inline nodes so Korean particles
            # like "모세가" are not split into "모세 가" by an artificial separator.
            verse_text = self._normalize_text(verse_clone.get_text("", strip=False))
            if not verse_text:
                continue

            verses.append(Verse(verse_number=verse_number, text=verse_text))

        verses.sort(key=lambda verse: verse.verse_number)
        return verses

    def _extract_verses_from_bibletable(self, soup: BeautifulSoup) -> list[Verse]:
        """
        Parse thekingsbible table rows:
          <table class="bibletable">
            <tr><td class="ref">1:1</td><td>Verse text...</td>...</tr>
          </table>
        """
        verses: list[Verse] = []

        for table in soup.select("table.bibletable"):
            row_data: list[tuple[int, int, str]] = []

            for row in table.select("tr"):
                ref_cell = row.find("td", class_="ref")
                if ref_cell is None:
                    continue

                ref_text = self._normalize_text(ref_cell.get_text(" ", strip=True))
                match = re.match(r"^(\d{1,3})\s*:\s*(\d{1,3})$", ref_text)
                if not match:
                    continue

                chapter_num = int(match.group(1))
                verse_num = int(match.group(2))

                verse_text = ""
                for cell in row.find_all("td"):
                    if cell is ref_cell:
                        continue
                    classes = cell.get("class", [])
                    if isinstance(classes, str):
                        classes = [classes]
                    if "ref" in classes or "glyph" in classes:
                        continue

                    text = self._normalize_text(cell.get_text(" ", strip=True))
                    if text:
                        verse_text = text
                        break

                if not verse_text:
                    continue

                row_data.append((chapter_num, verse_num, verse_text))

            if not row_data:
                continue

            # Keep dominant chapter on this table.
            dominant_chapter = Counter(ch for ch, _, _ in row_data).most_common(1)[0][0]
            seen_numbers: set[int] = set()

            for chapter_num, verse_num, verse_text in row_data:
                if chapter_num != dominant_chapter:
                    continue
                if verse_num in seen_numbers:
                    continue
                seen_numbers.add(verse_num)
                verses.append(Verse(verse_number=verse_num, text=verse_text))

        verses.sort(key=lambda v: v.verse_number)
        return verses if len(verses) >= 2 else []

    def _extract_verses_from_chapter_prefixed_lines(self, soup: BeautifulSoup) -> list[Verse]:
        """
        Parse lines like:
          1:1 In the beginning...
          1:2 And the earth...
        where the first number is chapter and second number is verse.
        """
        text = soup.get_text("\n", strip=True)
        if not text:
            return []

        pattern = re.compile(r"^\s*(\d{1,3})\s*:\s*(\d{1,3})\s+(.+)$")
        parsed: list[tuple[int, int, str]] = []

        for raw_line in text.split("\n"):
            line = self._normalize_text(raw_line)
            if not line:
                continue
            match = pattern.match(line)
            if not match:
                continue

            chapter_num = int(match.group(1))
            verse_num = int(match.group(2))
            verse_text = self._normalize_text(match.group(3))
            if not verse_text:
                continue
            parsed.append((chapter_num, verse_num, verse_text))

        if not parsed:
            return []

        # Select dominant chapter on page to filter out unrelated references.
        target_chapter = Counter(ch for ch, _, _ in parsed).most_common(1)[0][0]
        verses: list[Verse] = []
        seen_numbers: set[int] = set()
        for chapter_num, verse_num, verse_text in parsed:
            if chapter_num != target_chapter:
                continue
            if verse_num in seen_numbers:
                continue
            seen_numbers.add(verse_num)
            verses.append(Verse(verse_number=verse_num, text=verse_text))

        verses.sort(key=lambda v: v.verse_number)
        return verses if len(verses) >= 2 else []

    def _extract_verses_from_ordered_list(self, soup: BeautifulSoup) -> list[Verse]:
        verses: list[Verse] = []

        for ordered in soup.find_all("ol"):
            list_items = ordered.find_all("li", recursive=False)
            if not list_items:
                continue

            # In some source pages, verse numbers are implicit in <ol start="001">.
            start_raw = ordered.get("start")
            start_num = 1
            if isinstance(start_raw, str) and start_raw.strip().isdigit():
                start_num = int(start_raw.strip())

            current_num = start_num
            local_verses: list[Verse] = []
            for li in list_items:
                text = self._normalize_text(li.get_text(" ", strip=True))
                if not text:
                    current_num += 1
                    continue
                local_verses.append(Verse(verse_number=current_num, text=text))
                current_num += 1

            # Ignore tiny ordered lists that are likely navigation noise.
            if len(local_verses) >= 3:
                verses.extend(local_verses)

        if verses:
            verses.sort(key=lambda v: v.verse_number)
        return verses

    def _extract_verses_from_structured_nodes(self, soup: BeautifulSoup) -> list[Verse]:
        verse_pattern = re.compile(r"^\s*(\d{1,3})\s*(?:[.:)\-])?\s+(.+)$")
        verses: list[Verse] = []
        seen_numbers: set[int] = set()

        for node in soup.select("span, p, li, div, td"):
            text = node.get_text(" ", strip=True)
            if not text:
                continue

            normalized = self._normalize_text(text)
            match = verse_pattern.match(normalized)
            if not match:
                continue

            number = int(match.group(1))
            verse_text = self._normalize_text(match.group(2))
            if not verse_text or number in seen_numbers:
                continue

            seen_numbers.add(number)
            verses.append(Verse(verse_number=number, text=verse_text))

        # A tiny set is often noise from menus; use regex fallback then.
        if len(verses) < 3:
            return []

        verses.sort(key=lambda v: v.verse_number)
        return verses

    def _extract_verses_with_regex_fallback(self, soup: BeautifulSoup) -> list[Verse]:
        soup_copy = BeautifulSoup(str(soup), "html.parser")
        for br in soup_copy.find_all("br"):
            br.replace_with("\n")

        block_candidates = []
        for selector in ("article", "main", "section", "div", "td", "p"):
            block_candidates.extend(soup_copy.select(selector))

        # Prefer blocks that contain multiple line-start verse-number patterns.
        line_verse_pattern = re.compile(r"(?m)^\s*(\d{1,3})\s+(?=\S)")
        best_text = ""
        best_score = -1

        for block in block_candidates:
            text = block.get_text("\n", strip=True)
            score = len(line_verse_pattern.findall(text))
            if score > best_score:
                best_score = score
                best_text = text

        if best_score <= 0:
            best_text = soup_copy.get_text("\n", strip=True)

        text = best_text.replace("\r", "")
        text = re.sub(r"\n{2,}", "\n", text)

        verses: list[Verse] = []
        seen_numbers: set[int] = set()

        # First pass: strict line-based extraction.
        for line in text.split("\n"):
            line = self._normalize_text(line)
            match = re.match(r"^(\d{1,3})\s*(?:[.:)\-])?\s+(.+)$", line)
            if not match:
                continue

            number = int(match.group(1))
            verse_text = self._normalize_text(match.group(2))
            if not verse_text or number in seen_numbers:
                continue

            seen_numbers.add(number)
            verses.append(Verse(verse_number=number, text=verse_text))

        if verses:
            verses.sort(key=lambda v: v.verse_number)
            return verses

        # Second pass: inline block extraction when verses are not line-separated.
        inline_pattern = re.compile(
            r"(?:^|\s)(\d{1,3})\s+(.+?)(?=(?:\s\d{1,3}\s+)|$)",
            re.DOTALL,
        )
        for match in inline_pattern.finditer(text):
            number = int(match.group(1))
            verse_text = self._normalize_text(match.group(2))
            if not verse_text or number in seen_numbers:
                continue
            seen_numbers.add(number)
            verses.append(Verse(verse_number=number, text=verse_text))

        verses.sort(key=lambda v: v.verse_number)
        return verses
