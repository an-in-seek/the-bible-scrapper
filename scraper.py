from __future__ import annotations

import logging
import random
import re
import time
import unicodedata
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, NavigableString, PageElement, Tag
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from models import ChapterPayload, Verse

logger = logging.getLogger(__name__)


DEFAULT_ENTRY_URL = "https://thekingsbible.com/Bible/1/1"
DEFAULT_THEKINGSBIBLE_KJV_BASE_URL = "https://thekingsbible.com/Bible"
DEFAULT_BSKOREA_NKRV_ENTRY_URL = (
    "https://www.bskorea.or.kr/bible/korbibReadpage.php"
    "?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
)
DEFAULT_BIBLEGATEWAY_WEB_ENTRY_URL = (
    "https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB"
)
DEFAULT_BIBLEGATEWAY_BASE_URL = "https://www.biblegateway.com/passage/"
DEFAULT_BIBLEGATEWAY_VERSION = "WEB"
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
# USFM book codes, shared by bskorea (lowercase) and ebible.org (uppercase).
USFM_BOOK_CODES: tuple[str, ...] = (
    "gen", "exo", "lev", "num", "deu", "jos", "jdg", "rut", "1sa", "2sa", "1ki", "2ki",
    "1ch", "2ch", "ezr", "neh", "est", "job", "psa", "pro", "ecc", "sng", "isa", "jer",
    "lam", "ezk", "dan", "hos", "jol", "amo", "oba", "jon", "mic", "nam", "hab", "zep",
    "hag", "zec", "mal", "mat", "mrk", "luk", "jhn", "act", "rom", "1co", "2co", "gal",
    "eph", "php", "col", "1th", "2th", "1ti", "2ti", "tit", "phm", "heb", "jas", "1pe",
    "2pe", "1jn", "2jn", "3jn", "jud", "rev",
)
# Book names accepted by the BibleGateway `search` query parameter.
BIBLEGATEWAY_BOOK_NAMES: tuple[str, ...] = (
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges",
    "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles",
    "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", "Matthew",
    "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude",
    "Revelation",
)
# biblegateway.com/robots.txt declares "Crawl-delay: 15" for all user agents.
# Enforced as a floor in __init__ so it cannot be lowered by mistake.
BIBLEGATEWAY_CRAWL_DELAY_SECONDS = 15.0
# Verse spans carry an "OSIS-chapter-verse" class token, e.g. "Gen-1-1", "1Sam-1-23".
# The book abbreviation differs from the search name, so only the numbers are used.
BIBLEGATEWAY_VERSE_CLASS_PATTERN = re.compile(r"^[A-Za-z0-9]+-(\d{1,3})-(\d{1,3})$")
# Dropped from the container before verse extraction. `h4.psalm-title` matters most:
# BibleGateway tags the psalm superscription with the verse-1 class, so keeping it
# would prepend "A Psalm by David." to Psalms 23:1.
BIBLEGATEWAY_CONTAINER_REMOVABLE_SELECTOR = (
    "div.footnotes, div.crossrefs, h4.psalm-title, p.psalm-title, h3, "
    "p.translation-note, a.full-chap-link, div.passage-other-trans"
)
# Dropped from each verse span. Kept separate from the container pass so a span can
# still be inspected for the footnote marker that flags an untranslated verse.
BIBLEGATEWAY_INLINE_REMOVABLE_SELECTOR = (
    "span.chapternum, sup.versenum, sup.footnote, sup.crossreference"
)
# WEB leaves a few verses untranslated (Luke 17:36, Acts 8:37, 15:34, 24:7): the span
# exists but holds only a footnote marker. Recorded explicitly so a gap in the stored
# verse numbers always means a scrape failure, never a translation choice. Mirrors the
# "(없음)" convention Korean editions use for the same verses.
OMITTED_VERSE_TEXT = "(omitted)"
BIBLEGATEWAY_OMITTED_VERSE_TEXT = OMITTED_VERSE_TEXT
DEFAULT_EBIBLE_RV1909_ENTRY_URL = "https://ebible.org/spaRV1909/GEN01.htm"
DEFAULT_EBIBLE_SBLM_ENTRY_URL = "https://ebible.org/spablm/GEN01.htm"
DEFAULT_EBIBLE_JPNMEB_ENTRY_URL = "https://ebible.org/jpnm/GEN01.htm"
DEFAULT_EBIBLE_LSG1910_ENTRY_URL = "https://ebible.org/fraLSG/GEN01.htm"
DEFAULT_EBIBLE_TRANSLATION_CODE = "spaRV1909"
# Verse markers are `<span class="verse" id="V12">`; the chapter label uses V0.
EBIBLE_VERSE_ID_PATTERN = re.compile(r"^V(\d{1,3})$")
# Everything in div.main that is not scripture. `ul.tnav` matters most: it holds the
# book name and prev/next links. The USFM heading/note classes were not observed in
# RV1909 but are emitted by the same renderer for other translations.
EBIBLE_REMOVABLE_SELECTOR = (
    "ul.tnav, div.mt, div.mt1, div.mt2, div.mt3, "
    # fraLSG puts a second-level major heading between Genesis 11:9 and 11:10; without
    # div.ms2 it lands on 11:9 as "… toute la terre. DEPUIS ABRAHAM JUSQU’À JOSEPH".
    "div.ms, div.ms1, div.ms2, div.ms3, div.s, div.s1, div.s2, div.sr, div.mr, div.r, "
    # Headings that appear BETWEEN verses: a psalm/acrostic title (div.d, div.qa) or a
    # speaker label (div.sp). They carry no verse marker, so the accumulator folds them
    # into the surrounding verse (spablm Psalms 119 leaks 21, Song of Songs 1 leaks 8).
    "div.d, div.qa, div.qd, div.sp, "
    "div.chapterlabel, div.footnote, div.copyright, div.navbar"
)
# Removed in a second pass, after omitted verses are detected: an empty verse is only
# recognisable while its footnote marker is still in the tree. The marker nests the note
# body in span.popup, inside the verse text, so both go together.
EBIBLE_FOOTNOTE_SELECTOR = "a.notemark, span.notemark, span.footnote, span.crossref"
EBIBLE_BLOCK_TAGS = frozenset({"div", "p", "li", "table", "tr", "blockquote"})
# ebible.org declares no Crawl-delay, so this is a self-imposed politeness floor for a
# nonprofit static host rather than a site requirement. A full 66-book load stays well
# under an hour at this rate.
EBIBLE_MIN_DELAY_SECONDS = 1.0
# --- jpn.bible (口語訳聖書 1954/1955) -----------------------------------------
DEFAULT_JPNBIBLE_KOUGO_ENTRY_URL = "https://jpn.bible/kougo/gen#1"
DEFAULT_JPNBIBLE_TRANSLATION_CODE = "kougo"
# jpn.bible serves one page per BOOK and has no per-chapter URL (/kougo/ps/3,
# /kougo/ps3 and /kougo/ps.3 are all 404), so the chapter travels in the fragment and
# the page is split once per book. Refetching per chapter would pull 1.8MB x 150 for
# Psalms alone.
JPNBIBLE_BOOK_SLUGS: tuple[str, ...] = (
    "gen", "exod", "lev", "num", "deut", "josh", "judg", "ruth", "1sam", "2sam",
    "1kgs", "2kgs", "1chr", "2chr", "ezra", "neh", "esth", "job", "ps", "prov",
    "eccl", "song", "isa", "jer", "lam", "ezek", "dan", "hos", "joel", "amos",
    "obad", "jonah", "mic", "nah", "hab", "zeph", "hag", "zech", "mal", "matt",
    "mark", "luke", "john", "acts", "rom", "1cor", "2cor", "gal", "eph", "phil",
    "col", "1thess", "2thess", "1tim", "2tim", "titus", "phlm", "heb", "jas",
    "1pet", "2pet", "1john", "2john", "3john", "jude", "rev",
)
# "3:16" starts a verse and "22:3!a" is one half of a split verse. A merged range lists
# every covered verse as an extra OSIS token: id="132:3 Ps.132.4 Ps.132.5". Reading only
# the first extra token loses Psalms 132:5.
JPNBIBLE_VERSE_ID_PATTERN = re.compile(r"^(\d{1,3}):(\d{1,3})(?:!([ab]))?$")
JPNBIBLE_OSIS_REF_PATTERN = re.compile(r"^[A-Za-z0-9]+\.(\d{1,3})\.(\d{1,3})$")
# A range wider than this is a malformed id rather than real versification; duplicating
# a verse across dozens of numbers is worse than ignoring the range.
JPNBIBLE_MAX_RANGE_WIDTH = 10
# rt/rp carry the furigana readings. bs4 keeps them out of get_text(), but RubyTextString
# and RubyParenthesisString subclass NavigableString, so the descendants walk below would
# otherwise fold 神（かみ） into the verse text - and get_text() would still look clean.
# h1/h2 are the book and chapter headings; <title type="psalm"> is a psalm superscription,
# which none of the other translations here store.
JPNBIBLE_REMOVABLE_SELECTOR = "rt, rp, h1, h2, title"
JPNBIBLE_BLOCK_TAGS = frozenset({"div", "p", "li", "br", "blockquote"})
# The printed edition opens a bracket before the verse NUMBER of a disputed passage, so
# the markup leaves it at the end of the previous verse (19 verses). Moving it to the
# head of the next verse balances both and matches the second witness.
JPNBIBLE_OPENING_BRACKETS = "〔（"
# No Crawl-delay is declared; this is the same self-imposed floor used for ebible.org.
JPNBIBLE_MIN_DELAY_SECONDS = 1.0
# --- zh.wikisource 聖經 (和合本) 1919 -------------------------------------------
DEFAULT_WIKISOURCE_CUV_ENTRY_URL = (
    "https://zh.wikisource.org/zh-hant/%E8%81%96%E7%B6%93_(%E5%92%8C%E5%90%88%E6%9C%AC)"
    "/%E5%89%B5%E4%B8%96%E8%A8%98#1"
)
DEFAULT_WIKISOURCE_VARIANT = "zh-hant"
WIKISOURCE_PAGE_PREFIX = "聖經_(和合本)"
# Book pages are titled in traditional script even when the text is requested in
# simplified: /zh-hans/ converts the body, not the path.
WIKISOURCE_BOOK_TITLES: tuple[str, ...] = (
    "創世記", "出埃及記", "利未記", "民數記", "申命記", "約書亞記", "士師記", "路得記", "撒母耳記上", "撒母耳記下", "列王紀上",
    "列王紀下", "歷代志上", "歷代志下", "以斯拉記", "尼希米記", "以斯帖記", "約伯記", "詩篇", "箴言", "傳道書", "雅歌", "以賽亞書",
    "耶利米書", "耶利米哀歌", "以西結書", "但以理書", "何西阿書", "約珥書", "阿摩司書", "俄巴底亞書", "約拿書", "彌迦書", "那鴻書",
    "哈巴谷書", "西番雅書", "哈該書", "撒迦利亞書", "瑪拉基書", "馬太福音", "馬可福音", "路加福音", "約翰福音", "使徒行傳", "羅馬書",
    "哥林多前書", "哥林多後書", "加拉太書", "以弗所書", "腓立比書", "歌羅西書", "帖撒羅尼迦前書", "帖撒羅尼迦後書", "提摩太前書", "提摩太後書",
    "提多書", "腓利門書", "希伯來書", "雅各書", "彼得前書", "彼得後書", "約翰一書", "約翰二書", "約翰三書", "猶大書", "啟示錄",
)
# Chapter headings are the only chapter boundary. Psalms uses 篇, everything else 章,
# and the five 詩篇卷N section titles do not match this form, so they are skipped.
WIKISOURCE_CHAPTER_PATTERN = re.compile(r"^第([一二三四五六七八九十百零〇\d]+)[章篇]$")
# The 「編輯」 links and the table of contents are chrome; sup.reference is a wiki
# footnote marker, absent today but cheap to guard against.
WIKISOURCE_REMOVABLE_SELECTOR = "span.mw-editsection, table, style, sup.reference"
# A psalm superscription sits inside verse 1, wrapped in <small>, e.g.
# <sup>1</sup><small>大衞的詩。</small>耶和華是我的牧者…  Every other translation here
# drops superscriptions; RVR1909 keeps them only because its source cannot separate
# them. This one can, so it does not store them. The note test matters: outside Psalms
# a leading <small> is a translator's note (창 4:1 〈就是得的意思〉), which is kept.
WIKISOURCE_PSALM_BOOK_ORDER = 19
WIKISOURCE_NOTE_OPENING_BRACKET = "〈"
WIKISOURCE_VERSE_ID_PATTERN = re.compile(r"^(\d{1,3}):\d{1,3}$")
WIKISOURCE_MIN_DELAY_SECONDS = 1.0
# --- studybible.info Nestle 1904 Greek New Testament ----------------------------
DEFAULT_STUDYBIBLE_N1904_ENTRY_URL = "https://studybible.info/Nestle/Matthew%201"
DEFAULT_STUDYBIBLE_VERSION = "Nestle"
# Nestle 1904 is a New Testament edition. An Old Testament or out-of-range chapter URL
# answers 200 with an empty passage box rather than 404, and the generic chain then reads
# that page as two plausible verses starting at 1, so nothing downstream would catch it.
STUDYBIBLE_FIRST_NT_BOOK_ORDER = 40
# Verse markers carry "Matthew 1:1 Nestle" in the title. The chapter half is what makes
# the marker worth reading: the displayed number matches it in all 7,942 places.
STUDYBIBLE_REF_PATTERN = re.compile(r"^(?P<book>.+?)\s(?P<chapter>\d{1,3}):(?P<verse>\d{1,3})$")
# No Crawl-delay is declared for a generic agent; same self-imposed floor as ebible.org.
STUDYBIBLE_MIN_DELAY_SECONDS = 1.0
# Japanese and Chinese put no spaces between words, so the separator that joins a verse
# split across blocks - required for Spanish and English - corrupts CJK text instead.
# Hangul (U+AC00-D7A3) is deliberately excluded: Korean does space its words, and
# collapsing there would repeat the bskorea particle-splitting bug in reverse.
CJK_RANGES = "　-〿぀-ヿ㐀-䶿一-鿿＀-￯"
# ASCII whitespace only. U+3000 sits inside CJK_RANGES and is content rather than a
# separator; _normalize_text() has already folded it to a plain space by this point, so
# widening this to \s would only make the loss harder to trace.
CJK_JOIN_PATTERN = re.compile(rf"(?<=[{CJK_RANGES}])[ \t\r\n]+(?=[{CJK_RANGES}])")


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

        # Honor the source's declared crawl delay regardless of caller-supplied values.
        if self._is_biblegateway_source():
            self.sleep_min = max(self.sleep_min, BIBLEGATEWAY_CRAWL_DELAY_SECONDS)
            self.sleep_max = max(self.sleep_max, BIBLEGATEWAY_CRAWL_DELAY_SECONDS + 3.0)
        elif self._is_ebible_source():
            self.sleep_min = max(self.sleep_min, EBIBLE_MIN_DELAY_SECONDS)
            self.sleep_max = max(self.sleep_max, EBIBLE_MIN_DELAY_SECONDS + 1.0)
        elif self._is_jpnbible_source():
            self.sleep_min = max(self.sleep_min, JPNBIBLE_MIN_DELAY_SECONDS)
            self.sleep_max = max(self.sleep_max, JPNBIBLE_MIN_DELAY_SECONDS + 1.0)
        elif self._is_wikisource_source():
            self.sleep_min = max(self.sleep_min, WIKISOURCE_MIN_DELAY_SECONDS)
            self.sleep_max = max(self.sleep_max, WIKISOURCE_MIN_DELAY_SECONDS + 1.0)
        elif self._is_studybible_source():
            self.sleep_min = max(self.sleep_min, STUDYBIBLE_MIN_DELAY_SECONDS)
            self.sleep_max = max(self.sleep_max, STUDYBIBLE_MIN_DELAY_SECONDS + 1.0)

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
        self._throttle_multiplier = 1.0

        self._navigation_template: NavigationTemplate | None = None
        self._chapter_cache: dict[tuple[int, int], ChapterPayload] = {}
        self._chapter_url_cache: dict[int, dict[int, str]] = {}
        # Only the book page being processed is kept, so the loop stays at one entry.
        # Shared by every source whose pages are per-book (jpn.bible, wikisource).
        self._book_page_url: str | None = None
        self._book_page_chapters: dict[str, str] = {}

    def close(self) -> None:
        self.session.close()

    def get_source_name(self) -> str:
        if self._is_thekingsbible_source():
            return "thekingsbible"
        if self._is_bskorea_source():
            return "bskorea"
        if self._is_biblegateway_source():
            return "biblegateway"
        if self._is_ebible_source():
            return "ebible"
        if self._is_jpnbible_source():
            return "jpnbible"
        if self._is_wikisource_source():
            return "wikisource"
        if self._is_studybible_source():
            return "studybible"
        return "generic"

    def get_source_version(self) -> str | None:
        """
        Version token identifying which translation this entry URL selects.

        BibleGateway puts it in the query string (?version=WEB), but eBible puts it in
        the path (/spaRV1909/, /spablm/). Reading only the query string would leave both
        eBible translations indistinguishable, which silently defeats the source/
        translation compatibility check once one source serves more than one translation.
        """
        if self._is_ebible_source():
            return self._get_ebible_translation_code()
        if self._is_jpnbible_source():
            return self._get_jpnbible_translation_code()
        if self._is_wikisource_source():
            return self._get_wikisource_variant()
        if self._is_studybible_source():
            return self._get_studybible_version()
        query = dict(parse_qsl(urlparse(self.entry_url or "").query, keep_blank_values=True))
        return query.get("version")

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

        # requests falls back to ISO-8859-1 when Content-Type carries no charset,
        # which mojibakes UTF-8 pages that declare the encoding only in a <meta>
        # tag (ebible.org does exactly that). Sources that send a charset are
        # left untouched.
        if "charset=" not in (response.headers.get("Content-Type") or "").lower():
            response.encoding = response.apparent_encoding or "utf-8"

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
        if self._is_jpnbible_source():
            return self._fetch_book_page_chapter_soup(url, self._split_jpnbible_book)
        if self._is_wikisource_source():
            return self._fetch_book_page_chapter_soup(url, self._split_wikisource_book)
        html = self._request_html(url)
        return BeautifulSoup(html, "html.parser")

    def _fetch_book_page_chapter_soup(self, url: str, split) -> BeautifulSoup:
        """
        One HTTP request per book, then serve each chapter from the split page.

        The fragment carries the chapter number, so the cache is keyed by the page URL
        without it. Only the current book is kept: the loader is book-major, so the hit
        rate is 100% and at most one page (1.8MB for Psalms) stays resident.

        `split` returns {chapter key as a string: chapter HTML}, keyed to match the
        fragment. An int key would make every lookup miss and every chapter come back
        empty, which surfaces only as "book yielded no verses" once per book.
        """
        page_url, _, fragment = url.partition("#")
        if self._book_page_url != page_url:
            self._book_page_chapters = split(self._request_html(page_url))
            self._book_page_url = page_url

        return BeautifulSoup(self._book_page_chapters.get(fragment, ""), "html.parser")

    @staticmethod
    def _parse_chinese_numeral(value: str) -> int | None:
        """
        Chapter headings are written in Chinese numerals: 第三章, 第一百零一篇.

        The source is not consistent about the tens digit above one hundred - 110 is
        一百一十 while 111 is 一百十一 - so this only reads, never writes. Reading 零 as
        nothing (100 instead of 101) silently merges nine Psalms into their neighbours.
        """
        if not value:
            return None
        if value.isdigit():
            return int(value)

        digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                  "六": 6, "七": 7, "八": 8, "九": 9}
        total = 0
        rest = value
        if "百" in rest:
            head, rest = rest.split("百", 1)
            total += (digits.get(head, 1) if head else 1) * 100
            rest = rest.lstrip("零〇")
            if not rest:
                return total
        if "十" in rest:
            head, tail = rest.split("十", 1)
            total += (digits.get(head, 1) if head else 1) * 10
            return total + (digits.get(tail, 0) if tail else 0)
        return total + digits.get(rest, 0)

    @classmethod
    def _split_wikisource_book(cls, html: str) -> dict[str, str]:
        """Split a book page into {chapter number as a string: chapter HTML}."""
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one("div.mw-parser-output")
        if container is None:
            logger.warning("wikisource page has no div.mw-parser-output; chapter split is empty")
            return {}

        chapters: dict[str, str] = {}
        current: str | None = None
        parts: list[str] = []
        for node in container.find_all(["h2", "h3", "p", "dl"], recursive=True):
            if node.name in ("h2", "h3"):
                match = WIKISOURCE_CHAPTER_PATTERN.match(node.get_text("", strip=True))
                if match is None:
                    # 詩篇卷N and other section titles are not chapters; the paragraphs
                    # that follow still belong to the chapter already open.
                    continue
                if current is not None:
                    chapters[current] = "".join(parts)
                number = cls._parse_chinese_numeral(match.group(1))
                current = str(number) if number else None
                # The heading travels with the slice: 篇 marks Psalms, which is the only
                # book whose verse 1 opens with a superscription.
                parts = [str(node)]
                continue
            if current is not None:
                parts.append(str(node))
        if current is not None:
            chapters[current] = "".join(parts)
        return chapters

    @staticmethod
    def _split_jpnbible_book(html: str) -> dict[str, str]:
        """Split a book page into {chapter id: chapter HTML}."""
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one("main.book")
        if container is None:
            # Every chapter of this book will now parse to nothing and the book fails
            # its empty-data guard. That is the right outcome, but it is only traceable
            # to the page structure if it is said here.
            logger.warning("jpn.bible page has no main.book container; chapter split is empty")
            return {}

        chapters: dict[str, str] = {}
        for node in container.find_all("div", recursive=False):
            chapter_id = (node.get("id") or "").strip()
            if chapter_id.isdigit():
                chapters[chapter_id] = str(node)
        return chapters

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

    def _is_biblegateway_source(self) -> bool:
        parsed = urlparse(self.entry_url or "")
        host = parsed.netloc.lower()
        return ("biblegateway.com" in host) or parsed.path.rstrip("/").endswith("/passage")

    def _build_thekingsbible_url(self, book_order: int, chapter_number: int) -> str:
        # thekingsbible KJV rule:
        # Genesis 1 -> /Bible/1/1, Exodus 1 -> /Bible/2/1 ...
        return f"{DEFAULT_THEKINGSBIBLE_KJV_BASE_URL}/{book_order}/{chapter_number}"

    @staticmethod
    def _get_bskorea_book_code(book_order: int) -> str | None:
        if 1 <= book_order <= len(USFM_BOOK_CODES):
            return USFM_BOOK_CODES[book_order - 1]
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
    def _get_biblegateway_book_name(book_order: int) -> str | None:
        if 1 <= book_order <= len(BIBLEGATEWAY_BOOK_NAMES):
            return BIBLEGATEWAY_BOOK_NAMES[book_order - 1]
        return None

    def _build_biblegateway_url(
        self,
        book_order: int,
        chapter_number: int,
        book_code: str | None = None,
    ) -> str:
        book_name = book_code or self._get_biblegateway_book_name(book_order)
        if book_name is None:
            raise ValueError(f"Invalid biblegateway book order: {book_order}")

        parsed = urlparse(self.entry_url or DEFAULT_BIBLEGATEWAY_WEB_ENTRY_URL)
        path = parsed.path or "/passage/"
        base_url = urlunparse(parsed._replace(path=path, params="", query="", fragment=""))

        entry_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        version = entry_params.get("version") or DEFAULT_BIBLEGATEWAY_VERSION

        # quote() keeps the observed "%20" form; urlencode() would emit "+".
        search = quote(f"{book_name} {chapter_number}")
        return f"{base_url}?search={search}&version={quote(version)}"

    def _is_ebible_source(self) -> bool:
        return "ebible.org" in urlparse(self.entry_url or "").netloc.lower()

    def _get_ebible_translation_code(self) -> str:
        """First path segment of the entry URL, e.g. ".../spaRV1909/GEN01.htm"."""
        segments = [part for part in urlparse(self.entry_url or "").path.split("/") if part]
        return segments[0] if segments else DEFAULT_EBIBLE_TRANSLATION_CODE

    def _is_jpnbible_source(self) -> bool:
        return "jpn.bible" in urlparse(self.entry_url or "").netloc.lower()

    def _get_jpnbible_translation_code(self) -> str:
        """First path segment of the entry URL, e.g. ".../kougo/gen"."""
        segments = [part for part in urlparse(self.entry_url or "").path.split("/") if part]
        return segments[0] if segments else DEFAULT_JPNBIBLE_TRANSLATION_CODE

    def _build_jpnbible_url(self, book_order: int, chapter_number: int) -> str:
        if not 1 <= book_order <= len(JPNBIBLE_BOOK_SLUGS):
            raise ValueError(f"Invalid jpn.bible book order: {book_order}")

        parsed = urlparse(self.entry_url or DEFAULT_JPNBIBLE_KOUGO_ENTRY_URL)
        base_url = urlunparse(parsed._replace(path="", params="", query="", fragment=""))
        slug = JPNBIBLE_BOOK_SLUGS[book_order - 1]
        # The fragment is the chapter; _fetch_soup slices the cached book page with it.
        return f"{base_url}/{self._get_jpnbible_translation_code()}/{slug}#{chapter_number}"

    def _is_wikisource_source(self) -> bool:
        return "wikisource.org" in urlparse(self.entry_url or "").netloc.lower()

    def _get_wikisource_variant(self) -> str:
        """First path segment: the script variant, e.g. ".../zh-hant/..."."""
        segments = [part for part in urlparse(self.entry_url or "").path.split("/") if part]
        return segments[0] if segments else DEFAULT_WIKISOURCE_VARIANT

    def _build_wikisource_url(self, book_order: int, chapter_number: int) -> str:
        if not 1 <= book_order <= len(WIKISOURCE_BOOK_TITLES):
            raise ValueError(f"Invalid wikisource book order: {book_order}")

        parsed = urlparse(self.entry_url or DEFAULT_WIKISOURCE_CUV_ENTRY_URL)
        base_url = urlunparse(parsed._replace(path="", params="", query="", fragment=""))
        title = quote(f"{WIKISOURCE_PAGE_PREFIX}/{WIKISOURCE_BOOK_TITLES[book_order - 1]}")
        # The fragment is the arabic chapter number, not the page anchor: the heading
        # numerals are irregular (110 is 一百一十 but 111 is 一百十一), so they cannot be
        # generated from an int. _split_wikisource_book keys the cache the same way.
        return f"{base_url}/{self._get_wikisource_variant()}/{title}#{chapter_number}"

    def _is_studybible_source(self) -> bool:
        return "studybible.info" in urlparse(self.entry_url or "").netloc.lower()

    def _get_studybible_version(self) -> str:
        """First path segment of the entry URL, e.g. ".../Nestle/Matthew%201"."""
        segments = [part for part in urlparse(self.entry_url or "").path.split("/") if part]
        return segments[0] if segments else DEFAULT_STUDYBIBLE_VERSION

    def _build_studybible_url(self, book_order: int, chapter_number: int) -> str:
        # The source serves the New Testament only, and an Old Testament book name answers
        # 200 with an empty passage box. The range check is therefore a write guard, not a
        # tidiness check: see _extract_verses_from_studybible_page.
        if not STUDYBIBLE_FIRST_NT_BOOK_ORDER <= book_order <= len(BIBLEGATEWAY_BOOK_NAMES):
            raise ValueError(f"Invalid studybible book order: {book_order}")

        parsed = urlparse(self.entry_url or DEFAULT_STUDYBIBLE_N1904_ENTRY_URL)
        base_url = urlunparse(parsed._replace(path="", params="", query="", fragment=""))
        # The English book names this source uses are the ones BibleGateway uses; the NT
        # slice of that table matches all 27 spellings exactly.
        book_name = BIBLEGATEWAY_BOOK_NAMES[book_order - 1]
        # quote() keeps the observed "%20" form; urlencode() would emit "+".
        segment = quote(f"{book_name} {chapter_number}")
        return f"{base_url}/{self._get_studybible_version()}/{segment}"

    @staticmethod
    def _build_ebible_chapter_segment(book_order: int, chapter_number: int) -> str | None:
        if not 1 <= book_order <= len(USFM_BOOK_CODES):
            return None
        chapter_count = KJV_CHAPTER_COUNTS[book_order - 1]
        # Zero-padded to a per-book width: Psalms (150 chapters) needs three digits,
        # every other book two. PSA23.htm is a 404 while PSA023.htm is not.
        width = 3 if chapter_count >= 100 else 2
        return f"{USFM_BOOK_CODES[book_order - 1].upper()}{chapter_number:0{width}d}"

    def _build_ebible_url(self, book_order: int, chapter_number: int) -> str:
        segment = self._build_ebible_chapter_segment(book_order, chapter_number)
        if segment is None:
            raise ValueError(f"Invalid ebible book order: {book_order}")

        parsed = urlparse(self.entry_url or DEFAULT_EBIBLE_RV1909_ENTRY_URL)
        base_url = urlunparse(parsed._replace(path="", params="", query="", fragment=""))
        return f"{base_url}/{self._get_ebible_translation_code()}/{segment}.htm"

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
        if self._is_biblegateway_source():
            return self._build_biblegateway_url(book_order, chapter_number, book_code=book_code)
        if self._is_ebible_source():
            return self._build_ebible_url(book_order, chapter_number)
        if self._is_jpnbible_source():
            return self._build_jpnbible_url(book_order, chapter_number)
        if self._is_wikisource_source():
            return self._build_wikisource_url(book_order, chapter_number)
        if self._is_studybible_source():
            return self._build_studybible_url(book_order, chapter_number)
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
        if self._is_biblegateway_source():
            chapter_urls = self._discover_chapter_urls_for_biblegateway(
                book_order,
                book_code=book_code,
            )
            self._chapter_url_cache[book_order] = chapter_urls
            return chapter_urls
        if self._is_ebible_source():
            chapter_urls = self._discover_chapter_urls_for_ebible(book_order)
            self._chapter_url_cache[book_order] = chapter_urls
            return chapter_urls
        if self._is_jpnbible_source():
            chapter_urls = self._discover_chapter_urls_for_jpnbible(book_order)
            self._chapter_url_cache[book_order] = chapter_urls
            return chapter_urls
        if self._is_wikisource_source():
            chapter_urls = self._discover_chapter_urls_for_wikisource(book_order)
            self._chapter_url_cache[book_order] = chapter_urls
            return chapter_urls
        if self._is_studybible_source():
            chapter_urls = self._discover_chapter_urls_for_studybible(book_order)
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

    def _discover_chapter_urls_for_biblegateway(
        self,
        book_order: int,
        book_code: str | None = None,
    ) -> dict[int, str]:
        chapter_count = self._get_kjv_chapter_count(book_order)
        if chapter_count is None:
            return {}

        return {
            chapter_num: self._build_biblegateway_url(book_order, chapter_num, book_code=book_code)
            for chapter_num in range(1, chapter_count + 1)
        }

    def _discover_chapter_urls_for_wikisource(self, book_order: int) -> dict[int, str]:
        # Chapter counts match KJV_CHAPTER_COUNTS exactly (measured: 1,189 chapter
        # headings across the 66 book pages), so no probing request is needed.
        chapter_count = self._get_kjv_chapter_count(book_order)
        if chapter_count is None:
            return {}

        return {
            chapter_num: self._build_wikisource_url(book_order, chapter_num)
            for chapter_num in range(1, chapter_count + 1)
        }

    def _discover_chapter_urls_for_studybible(self, book_order: int) -> dict[int, str]:
        # Chapter counts match KJV_CHAPTER_COUNTS for all 27 New Testament books
        # (measured: 260 chapters). Probing is not an option here anyway - a chapter past
        # the end answers 200 with an empty passage box, so a probe loop never terminates
        # on a 404.
        if book_order < STUDYBIBLE_FIRST_NT_BOOK_ORDER:
            return {}

        chapter_count = self._get_kjv_chapter_count(book_order)
        if chapter_count is None:
            return {}

        return {
            chapter_num: self._build_studybible_url(book_order, chapter_num)
            for chapter_num in range(1, chapter_count + 1)
        }

    def _discover_chapter_urls_for_jpnbible(self, book_order: int) -> dict[int, str]:
        # Chapter counts match KJV_CHAPTER_COUNTS exactly (measured: 1,189 chapter divs
        # across the 66 book pages), so no probing request is needed.
        chapter_count = self._get_kjv_chapter_count(book_order)
        if chapter_count is None:
            return {}

        return {
            chapter_num: self._build_jpnbible_url(book_order, chapter_num)
            for chapter_num in range(1, chapter_count + 1)
        }

    def _discover_chapter_urls_for_ebible(self, book_order: int) -> dict[int, str]:
        chapter_count = self._get_kjv_chapter_count(book_order)
        if chapter_count is None:
            return {}

        return {
            chapter_num: self._build_ebible_url(book_order, chapter_num)
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

        # Must run before the generic parsers: they would read BibleGateway
        # footnotes and navigation labels as verses.
        biblegateway_verses = self._extract_verses_from_biblegateway_passage(soup)
        if biblegateway_verses:
            return biblegateway_verses

        # Must also precede the generic parsers: the regex fallback happily parses an
        # eBible chapter into a full, contiguous verse list with the verse number left
        # inside verse 1, which no verse-count check would catch.
        ebible_verses = self._extract_verses_from_ebible_page(soup)
        if ebible_verses:
            return ebible_verses

        # Same reason as eBible: left to the generic parsers, a jpn.bible chapter comes
        # back as a full, contiguous verse list with the furigana readings baked into
        # the text, which no verse-count or contiguity check would catch.
        jpnbible_verses = self._extract_verses_from_jpnbible_page(soup)
        if jpnbible_verses:
            return jpnbible_verses

        wikisource_verses = self._extract_verses_from_wikisource_page(soup)
        if wikisource_verses:
            return wikisource_verses

        # Same reason again: the generic parsers read this source's cross-reference
        # navigation as verses, so a Nestle chapter comes back as a single verse holding
        # "Samuel 7:13" instead of the 25 Greek verses on the page.
        studybible_verses = self._extract_verses_from_studybible_page(soup)
        if studybible_verses:
            return studybible_verses

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

    def _extract_verses_from_wikisource_page(self, soup: BeautifulSoup) -> list[Verse]:
        """
        Parse one 聖經 (和合本) chapter sliced out of a zh.wikisource book page:

          <h2 id="第一篇">第一篇</h2>
          <p><span id="1:1"><sup>1</sup></span><small>大衞的詩。</small>耶和華是…</p>
          <p><span id="24:29"><sup>29</sup></span><sup>30</sup>利百加有一個哥哥…</p>

        Text is collected per paragraph, never across paragraphs: the licence box at the
        end of every book is a paragraph without any marker, and accumulating past the
        paragraph would append it to that book's last verse.
        """
        chapters_seen = set()
        for span in soup.select("span[id]"):
            match = WIKISOURCE_VERSE_ID_PATTERN.match(span.get("id") or "")
            if match is not None and span.find("sup"):
                chapters_seen.add(match.group(1))
        if not chapters_seen:
            return []
        # A whole book page would otherwise come back as one plausible, contiguous verse
        # list: every chapter's verse 1 collides and _sanitize_verses keeps the first.
        # The only way here is a broken _split_wikisource_book, so say so loudly.
        if len(chapters_seen) > 1:
            logger.warning(
                "wikisource page carries %d chapters (%s...); expected a single chapter slice",
                len(chapters_seen),
                sorted(chapters_seen, key=int)[:5],
            )
            return []

        working = BeautifulSoup(str(soup), "html.parser")
        for removable in working.select(WIKISOURCE_REMOVABLE_SELECTOR):
            removable.decompose()

        heading = working.find(["h2", "h3"])
        is_psalm = bool(heading) and heading.get_text("", strip=True).endswith("篇")

        entries: list[list] = []
        for paragraph in working.find_all("p"):
            if paragraph.find("sup") is None:
                continue
            if is_psalm and not entries:
                self._drop_wikisource_psalm_title(paragraph)

            pending: list[int] = []
            current: tuple[int, ...] | None = None
            chunks: dict[tuple[int, ...], list[str]] = {}
            for node in paragraph.descendants:
                if isinstance(node, Tag):
                    if node.name == "sup":
                        label = node.get_text("", strip=True)
                        # Cross-reference markers are Suzhou numerals, not verse numbers:
                        # treating them as verses would cut the verse in half there.
                        if label.isdigit():
                            pending.append(int(label))
                            current = None
                    continue
                if not isinstance(node, NavigableString):
                    continue
                # Marker text is never body text, whichever kind of marker it is.
                if node.find_parent("sup") is not None:
                    continue
                text = str(node)
                if not text.strip():
                    continue
                if pending:
                    current = tuple(pending)
                    chunks.setdefault(current, [])
                    pending = []
                if current is not None:
                    chunks[current].append(text)

            for numbers, parts in chunks.items():
                text = self._normalize_text("".join(parts).replace(" ", " "))
                entries.append([numbers, CJK_JOIN_PATTERN.sub("", text)])

        verses: list[Verse] = []
        for numbers, text in entries:
            if not text:
                continue
            # Consecutive markers mean the source set those verses as one unit; store it
            # at every number so verse numbering stays contiguous.
            for verse_number in numbers:
                verses.append(Verse(verse_number=verse_number, text=text))
        return verses

    @staticmethod
    def _drop_wikisource_psalm_title(paragraph: Tag) -> None:
        """
        Remove a psalm superscription: the first <small> in verse 1 of a Psalm.

        Every other translation here drops superscriptions. Outside Psalms - and inside
        Psalms when the <small> is a bracketed note - the same markup carries a
        translator's note that must be kept, so both conditions are required.
        """
        first = paragraph.find("small")
        if first is None:
            return
        if first.get_text("", strip=True).startswith(WIKISOURCE_NOTE_OPENING_BRACKET):
            return
        marker = paragraph.find("sup")
        if marker is not None and first not in marker.find_all_next("small"):
            return
        first.decompose()

    def _parse_jpnbible_verse_id(self, raw_id: str | None) -> tuple[int, int, int, str] | None:
        """
        Read a jpn.bible verse id into (chapter, first verse, last verse, split suffix).

        "3:16"                    -> (3, 16, 16, "")
        "22:3!a"                  -> (22, 3, 3, "a")   one half of a split verse
        "132:3 Ps.132.4 Ps.132.5" -> (132, 3, 5, "")   merged range, every member listed
        """
        if not raw_id:
            return None

        tokens = raw_id.split()
        match = JPNBIBLE_VERSE_ID_PATTERN.match(tokens[0])
        if match is None:
            return None

        chapter = int(match.group(1))
        start = int(match.group(2))
        suffix = match.group(3) or ""
        end = start
        for token in tokens[1:]:
            ref_match = JPNBIBLE_OSIS_REF_PATTERN.match(token)
            if ref_match is not None:
                # The LAST listed reference is the end of the range, not the first.
                end = max(end, int(ref_match.group(2)))

        if end < start or end - start > JPNBIBLE_MAX_RANGE_WIDTH:
            end = start
        return chapter, start, end, suffix

    def _extract_verses_from_jpnbible_page(self, soup: BeautifulSoup) -> list[Verse]:
        """
        Parse one jpn.bible chapter (a `div[id]` sliced out of the book page):

          <span class="verse" id="1:1">
            <span class="verse-number">1</span><span class="verse-content">text…</span>
          </span>

        Prose keeps the body inside `span.verse-content`. Poetry leaves that span empty
        and the body follows as sibling nodes until an explicit end marker
        (`span.verse[data-e-id]`), so text is accumulated between markers as on eBible.
        """
        # `span.verse-content` is what distinguishes this source: eBible uses
        # span.verse+id="V1", bskorea and BibleGateway use different classes entirely.
        # main.book cannot be used here because the caller passes a chapter slice.
        if soup.select_one("span.verse-content") is None:
            return []

        working = BeautifulSoup(str(soup), "html.parser")
        for removable in working.select(JPNBIBLE_REMOVABLE_SELECTOR):
            removable.decompose()

        chunks: dict[tuple[int, int, int, str], list[str]] = {}
        current: tuple[int, int, int, str] | None = None
        block_changed = False

        for node in working.descendants:
            if isinstance(node, Tag):
                classes = node.get("class") or []
                if node.name == "span" and "verse" in classes:
                    # No id means an end marker (data-e-id): the verse stops here.
                    current = self._parse_jpnbible_verse_id(node.get("id"))
                    if current is not None:
                        chunks.setdefault(current, [])
                    block_changed = False
                elif node.name in JPNBIBLE_BLOCK_TAGS and current is not None:
                    block_changed = True
                continue

            if not isinstance(node, NavigableString) or current is None:
                continue
            # The rendered marker is the verse number, never body text.
            if node.find_parent("span", class_="verse-number") is not None:
                continue

            text = str(node)
            if not text.strip():
                continue

            chunks[current].append((" " if block_changed else "") + text)
            block_changed = False

        # A whole book page would otherwise come back as one plausible, contiguous verse
        # list with every chapter's verse 1 concatenated. Callers must pass a chapter,
        # and the only way here is a broken _split_jpnbible_book, so say so loudly: the
        # generic parsers downstream would happily produce a full verse list from it.
        chapters_seen = {key[0] for key in chunks}
        if len(chapters_seen) > 1:
            logger.warning(
                "jpn.bible page carries %d chapters (%s...); expected a single chapter slice",
                len(chapters_seen),
                sorted(chapters_seen)[:5],
            )
            return []

        # Join the halves of a split verse in suffix order. Exodus 22 prints 3b before
        # 3a, so document order would reverse the sentence.
        merged: dict[tuple[int, int], list[str]] = {}
        for (_chapter, start, end, suffix), parts in sorted(
            chunks.items(), key=lambda kv: (kv[0][1], kv[0][3])
        ):
            merged.setdefault((start, end), []).append("".join(parts))

        entries: list[list] = []
        for (start, end), parts in sorted(merged.items()):
            text = self._normalize_text("".join(parts).replace(" ", " "))
            # Block joins insert a space; CJK scripts must not keep it.
            entries.append([start, end, CJK_JOIN_PATTERN.sub("", text)])

        for index in range(len(entries) - 1):
            text = entries[index][2]
            if text and text[-1] in JPNBIBLE_OPENING_BRACKETS:
                entries[index][2] = text[:-1].rstrip()
                entries[index + 1][2] = text[-1] + entries[index + 1][2]

        verses: list[Verse] = []
        for start, end, text in entries:
            if not text:
                continue
            # A merged range is one printed unit: store it at every number it covers so
            # verse numbering stays contiguous and any number returns the right text.
            for verse_number in range(start, end + 1):
                verses.append(Verse(verse_number=verse_number, text=text))
        return verses

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

    def _extract_verses_from_biblegateway_passage(self, soup: BeautifulSoup) -> list[Verse]:
        """
        Parse a BibleGateway passage page:
          <div class="passage-text">...<span class="text Gen-1-1">...</span>...</div>

        Verse numbers come from the class token, never from the rendered number:
        the first verse of a chapter displays the *chapter* number via
        `span.chapternum`, so Genesis 2:1 would otherwise be stored as verse 2.
        """
        container = soup.select_one("div.passage-text")
        if container is None:
            return []

        # Parallel translations render one container per version; keep the first.
        working = BeautifulSoup(str(container), "html.parser")
        for removable in working.select(BIBLEGATEWAY_CONTAINER_REMOVABLE_SELECTOR):
            removable.decompose()

        fragments: list[tuple[int, int, str, bool]] = []
        for node in working.select("span.text"):
            if node.find_parent("span", class_="text") is not None:
                continue

            token = None
            for css_class in node.get("class", []):
                token = BIBLEGATEWAY_VERSE_CLASS_PATTERN.match(css_class)
                if token:
                    break
            if token is None:
                continue

            has_footnote = node.select_one("sup.footnote") is not None
            fragment = BeautifulSoup(str(node), "html.parser")
            for removable in fragment.select(BIBLEGATEWAY_INLINE_REMOVABLE_SELECTOR):
                removable.decompose()

            # Keep source whitespace: an explicit separator would inject spaces
            # around inline markup such as removed footnote markers.
            text = self._normalize_text(fragment.get_text(""))
            is_omitted = False
            if not text:
                # Only a footnote marker means WEB does not translate this verse.
                # Anything else that parses empty is treated as a parse failure so a
                # DOM change cannot silently fill the book with placeholders.
                if not has_footnote:
                    continue
                text = BIBLEGATEWAY_OMITTED_VERSE_TEXT
                is_omitted = True

            fragments.append((int(token.group(1)), int(token.group(2)), text, is_omitted))

        if not fragments:
            return []

        dominant_chapter = Counter(chapter for chapter, _, _, _ in fragments).most_common(1)[0][0]

        # A single verse is split across several spans in poetry blocks
        # (Psalms 23:4 spans four), so fragments are joined, not deduplicated.
        merged: dict[int, list[tuple[str, bool]]] = {}
        for chapter, verse_number, text, is_omitted in fragments:
            if chapter != dominant_chapter:
                continue
            merged.setdefault(verse_number, []).append((text, is_omitted))

        verses: list[Verse] = []
        for verse_number, parts in sorted(merged.items()):
            translated = [text for text, is_omitted in parts if not is_omitted]
            text = " ".join(translated) if translated else BIBLEGATEWAY_OMITTED_VERSE_TEXT
            verses.append(Verse(verse_number=verse_number, text=text))
        return verses

    def _extract_verses_from_ebible_page(self, soup: BeautifulSoup) -> list[Verse]:
        """
        Parse an eBible.org (USFM-derived) chapter page:
          <div class="main">
            <div class="p"><span class="verse" id="V1">1&nbsp;</span>text...</div>
          </div>

        Unlike BibleGateway, verse text is NOT wrapped in an element: `span.verse` is
        only the number marker and the body follows as sibling nodes. Text is therefore
        accumulated between markers rather than read out of a node.
        """
        container = soup.select_one("div.main")
        if container is None:
            return []

        working = BeautifulSoup(str(container), "html.parser")
        for removable in working.select(EBIBLE_REMOVABLE_SELECTOR):
            removable.decompose()

        if working.select_one("span.verse") is None:
            return []

        # Detect before stripping footnotes: the evidence disappears with the marker.
        omitted = self._collect_ebible_omitted_verses(working)
        for marker in working.select(EBIBLE_FOOTNOTE_SELECTOR):
            if marker.decomposed:  # went with an enclosing marker
                continue
            before = self._ebible_text_beside_note(marker.previous_elements)
            after = self._ebible_text_beside_note(marker.next_elements)
            marker.decompose()
            # fraLSG sets some markers between two words with no space ("et<note>on"): the
            # superscript is the only visible separator, so deleting it glues the words
            # (189 places, mostly span.wj edges in the Gospels). The space goes onto the
            # next text node, not in place of the marker - the accumulator below skips
            # whitespace-only nodes. Letters on both sides only, so "mot<note>." stays.
            if before is not None and after is not None and before[-1].isalpha() and after[0].isalpha():
                after.replace_with(" " + after)

        chunks: dict[int, list[str]] = {}
        current: int | None = None
        block_changed = False

        for node in working.descendants:
            if isinstance(node, Tag):
                classes = node.get("class") or []
                if node.name == "span" and "verse" in classes:
                    # The id is authoritative; the rendered marker is display text.
                    match = EBIBLE_VERSE_ID_PATTERN.match(node.get("id") or "")
                    current = int(match.group(1)) if match else None
                    block_changed = False
                elif node.name in EBIBLE_BLOCK_TAGS and current is not None:
                    block_changed = True
                continue

            if not isinstance(node, NavigableString) or current is None:
                continue
            # The marker's own text is the verse number, never body text.
            if node.find_parent("span", class_="verse") is not None:
                continue

            text = str(node)
            if not text.strip():
                continue

            # Keep source whitespace inside a block; separate blocks with one space so
            # a verse spanning two paragraphs does not concatenate words.
            chunks.setdefault(current, []).append((" " if block_changed else "") + text)
            block_changed = False

        verses: list[Verse] = []
        for verse_number in sorted(set(chunks) | omitted):
            text = self._normalize_text("".join(chunks.get(verse_number, [])).replace(" ", " "))
            # Block joins insert a space; CJK scripts must not keep it (spablm/RV1909 must).
            text = CJK_JOIN_PATTERN.sub("", text)
            if not text and verse_number in omitted:
                text = OMITTED_VERSE_TEXT
            if text:
                verses.append(Verse(verse_number=verse_number, text=text))
        return verses

    @staticmethod
    def _ebible_text_beside_note(elements: Iterable[PageElement]) -> NavigableString | None:
        """First non-empty text in `elements` that no footnote marker contains."""
        for element in elements:
            if not isinstance(element, NavigableString) or not element:
                continue
            # Skips the marker's own popup (next_elements walks into it first) and the
            # popup of an adjacent marker.
            if any(parent.css.match(EBIBLE_FOOTNOTE_SELECTOR) for parent in element.parents):
                continue
            return element
        return None

    @staticmethod
    def _collect_ebible_omitted_verses(working: BeautifulSoup) -> set[int]:
        """
        Verse markers whose whole body is a footnote — the source omits the text.

        spablm drops the same four verses BibleGateway's WEB does (Luke 17:36,
        Acts 8:37, 15:34, 24:7), emitting the marker plus an `a.notemark` explaining
        which manuscripts carry it. Recording them as OMITTED_VERSE_TEXT keeps verse
        numbering contiguous, so a real gap still reads as a scrape failure.

        The footnote is required evidence: an arbitrarily empty span must stay skipped,
        or a DOM change would quietly fill the DB with placeholders instead of failing.
        """
        with_note: set[int] = set()
        with_body: set[int] = set()
        current: int | None = None

        for node in working.descendants:
            if isinstance(node, Tag):
                classes = node.get("class") or []
                if node.name == "span" and "verse" in classes:
                    match = EBIBLE_VERSE_ID_PATTERN.match(node.get("id") or "")
                    current = int(match.group(1)) if match else None
                elif current is not None and "notemark" in classes:
                    with_note.add(current)
                continue

            if not isinstance(node, NavigableString) or current is None:
                continue
            if node.find_parent("span", class_="verse") is not None:
                continue
            # Text inside the popup belongs to the note, not to the verse.
            if node.find_parent(class_="notemark") is not None:
                continue
            if str(node).strip():
                with_body.add(current)

        return with_note - with_body

    def _extract_verses_from_studybible_page(self, soup: BeautifulSoup) -> list[Verse]:
        """
        Parse a studybible.info chapter page:
          <div class="passage row Nestle">Nestle<sup><a class="version_info">(i)</a></sup>
            <sup><a class="verse_ref Nestle" title="Matthew 1:1 Nestle">1</a></sup> Βίβλος ...
          </div>

        Like eBible, the marker holds only the number and the body follows as sibling
        nodes, so text is accumulated between markers. The leading "Nestle (i)" version
        link sits before the first marker and is dropped by that alone.

        No block separator is inserted between chunks: measured across all 260 chapters,
        the container holds nothing but `sup` and `a` - no `p`, `br` or `div` - so the
        block-boundary space eBible needs would only be misleading here.
        """
        version = self._get_studybible_version()
        container = None
        for candidate in soup.select("div.passage"):
            if version in (candidate.get("class") or []):
                container = candidate
                break
        if container is None:
            return []

        working = BeautifulSoup(str(container), "html.parser")
        if working.select_one("a.verse_ref") is None:
            return []

        chunks: dict[int, list[str]] = {}
        chapters: set[int] = set()
        current: int | None = None

        for node in working.descendants:
            if isinstance(node, Tag):
                if node.name == "a" and "verse_ref" in (node.get("class") or []):
                    # The title is authoritative and carries the chapter as well.
                    match = STUDYBIBLE_REF_PATTERN.match(
                        (node.get("title") or "").removesuffix(f" {version}").strip()
                    )
                    current = int(match.group("verse")) if match else None
                    if match:
                        chapters.add(int(match.group("chapter")))
                continue

            if not isinstance(node, NavigableString) or current is None:
                continue
            # Marker text is the verse number, and the version link is not body text.
            if node.find_parent("a") is not None or node.find_parent("sup") is not None:
                continue
            if node.strip():
                chunks.setdefault(current, []).append(str(node))

        if len(chapters) > 1:
            logger.warning(
                "studybible page mixes chapters %s; skipping to avoid a plausible splice",
                sorted(chapters),
            )
            return []

        verses: list[Verse] = []
        for verse_number in sorted(chunks):
            # 27% of this source is not NFC: U+0387 plus 21 oxia letters. Left as-is,
            # Matthew 1:1 does not match a normally typed "Βίβλος". NFC is applied here
            # rather than globally because every other source is already NFC, and because
            # check_translation_drift.py re-parses through this same adapter.
            text = unicodedata.normalize(
                "NFC", self._normalize_text("".join(chunks[verse_number]))
            )
            if text:
                verses.append(Verse(verse_number=verse_number, text=text))
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
