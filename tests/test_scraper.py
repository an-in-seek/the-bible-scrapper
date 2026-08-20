from bs4 import BeautifulSoup

from scraper import HolyBibleScraper


def test_parse_verses_with_regex_fallback() -> None:
    html = """
    <html>
      <body>
        <main>
          <div>1 In the beginning God created the heaven and the earth.</div>
          <div>2 And the earth was without form, and void; and darkness was upon the face of the deep.</div>
          <div>3 And God said, Let there be light: and there was light.</div>
        </main>
      </body>
    </html>
    """
    scraper = HolyBibleScraper(entry_url="https://example.com")
    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 3
    assert verses[0].verse_number == 1
    assert verses[0].text.startswith("In the beginning")
    assert verses[2].verse_number == 3


def test_parse_retry_after_seconds_numeric() -> None:
    assert HolyBibleScraper._parse_retry_after_seconds("12") == 12
    assert HolyBibleScraper._parse_retry_after_seconds("0") == 1


def test_parse_retry_after_seconds_invalid() -> None:
    assert HolyBibleScraper._parse_retry_after_seconds(None) is None
    assert HolyBibleScraper._parse_retry_after_seconds("") is None
    assert HolyBibleScraper._parse_retry_after_seconds("not-a-date") is None


def test_detect_rate_limited_html_markers() -> None:
    assert HolyBibleScraper._looks_like_rate_limited_html("<html><body>429 Error</body></html>")
    assert HolyBibleScraper._looks_like_rate_limited_html("Too Many Requests")
    assert not HolyBibleScraper._looks_like_rate_limited_html(
        "<html><body>In the beginning God created the heaven and the earth.</body></html>"
    )


def test_build_thekingsbible_url_rule() -> None:
    scraper = HolyBibleScraper(entry_url="https://thekingsbible.com/Bible/1/1")

    assert scraper._build_chapter_url(1, 1) == (
        "https://thekingsbible.com/Bible/1/1"
    )
    assert scraper._build_chapter_url(1, 50) == (
        "https://thekingsbible.com/Bible/1/50"
    )
    assert scraper._build_chapter_url(2, 1) == (
        "https://thekingsbible.com/Bible/2/1"
    )


def test_discover_thekingsbible_chapter_urls_uses_canonical_count() -> None:
    scraper = HolyBibleScraper(entry_url="https://thekingsbible.com/Bible/1/1")
    urls = scraper.discover_chapter_urls_for_book(1)

    assert len(urls) == 50
    assert urls[1].endswith("/Bible/1/1")
    assert urls[50].endswith("/Bible/1/50")


def test_parse_verses_with_chapter_colon_prefix() -> None:
    html = """
    <div class="chapter-content">
      <p>1:1 In the beginning God created the heaven and the earth.</p>
      <p>1:2 And the earth was without form, and void; and darkness was upon the face of the deep.</p>
      <p>1:3 And God said, Let there be light: and there was light.</p>
    </div>
    """
    scraper = HolyBibleScraper(entry_url="https://thekingsbible.com/Bible/1/1")
    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 3
    assert verses[0].verse_number == 1
    assert verses[1].verse_number == 2
    assert verses[2].verse_number == 3


def test_parse_verses_filters_error_line_like_429_error() -> None:
    html = "<div>429 Error</div>"
    scraper = HolyBibleScraper(entry_url="https://thekingsbible.com/Bible/1/1")
    verses = scraper.parse_verses_from_html(html)
    assert verses == []


def test_parse_verses_from_bibletable_structure() -> None:
    html = """
    <table class="bibletable">
      <tr>
        <td class="ref">1:1</td>
        <td>In the beginning God created the heaven and the earth.</td>
        <td class="glyph">&nbsp;</td>
      </tr>
      <tr>
        <td class="ref">1:2</td>
        <td>And the earth was without form, and void; and darkness <i>was</i> upon the face of the deep.</td>
        <td class="glyph"><a class="dict" href="#">dict</a></td>
      </tr>
    </table>
    """
    scraper = HolyBibleScraper(entry_url="https://thekingsbible.com/Bible/1/1")
    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 2
    assert verses[0].verse_number == 1
    assert verses[0].text.startswith("In the beginning")
    assert verses[1].verse_number == 2
    assert "darkness was upon the face of the deep" in verses[1].text


def test_parse_verses_from_ordered_list_html() -> None:
    html = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td width="30">&nbsp;</td>
        <td valign="top" bgcolor="#FAFAFA" class="tk4br">
          <ol start="001" id="b_001">
            <li><font class="tk4l">And the LORD spake unto Moses, saying,</font></li>
            <li><font class="tk4l">On the first day of the first <a href="javascript:openDict('807', 'month')">month</a> shalt thou set up the tabernacle of the tent of the congregation.</font></li>
            <li><font class="tk4l">And thou shalt put therein the ark of the testimony, and cover the ark with the vail.</font></li>
          </ol>
        </td>
      </tr>
    </table>
    """
    scraper = HolyBibleScraper(entry_url="https://thekingsbible.com/Bible/1/1")
    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 3
    assert verses[0].verse_number == 1
    assert verses[0].text.startswith("And the LORD spake unto Moses")
    assert verses[1].verse_number == 2
    assert "month shalt thou set up the tabernacle" in verses[1].text


def test_parse_verses_from_split_ordered_lists_with_start_offset() -> None:
    html = """
    <table>
      <tr><td><b>Genesis 40장 [KJV]</b></td></tr>
    </table>
    <table>
      <tr>
        <td>
          <ol start="001" id="b_001">
            <li><font class="tk4l">Verse one text.</font></li>
            <li><font class="tk4l">Verse two text.</font></li>
            <li><font class="tk4l">Verse three text.</font></li>
            <li><font class="tk4l">Verse four text.</font></li>
            <li><font class="tk4l">Verse five text.</font></li>
          </ol>
        </td>
      </tr>
    </table>
    <table>
      <tr>
        <td>
          <ol start="006" id="b_006">
            <li><font class="tk4l">Verse six text.</font></li>
            <li><font class="tk4l">Verse seven text.</font></li>
            <li><font class="tk4l">Verse eight text.</font></li>
            <li><font class="tk4l">Verse nine text.</font></li>
            <li><font class="tk4l">Verse ten text.</font></li>
          </ol>
        </td>
      </tr>
    </table>
    """
    scraper = HolyBibleScraper(entry_url="https://thekingsbible.com/Bible/1/1")
    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 10
    assert verses[0].verse_number == 1
    assert verses[4].verse_number == 5
    assert verses[5].verse_number == 6
    assert verses[5].text == "Verse six text."
    assert verses[-1].verse_number == 10


def test_build_bskorea_url_rule() -> None:
    scraper = HolyBibleScraper(
        entry_url=(
            "https://www.bskorea.or.kr/bible/korbibReadpage.php"
            "?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
        )
    )

    assert scraper._build_chapter_url(3, 27) == (
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=lev&chap=27&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )
    assert scraper._build_chapter_url(4, 1) == (
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=num&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )


def test_discover_bskorea_chapter_urls_uses_canonical_count() -> None:
    scraper = HolyBibleScraper(
        entry_url=(
            "https://www.bskorea.or.kr/bible/korbibReadpage.php"
            "?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
        )
    )
    urls = scraper.discover_chapter_urls_for_book(3)

    assert len(urls) == 27
    assert urls[1].endswith("book=lev&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal")
    assert urls[27].endswith("book=lev&chap=27&sec=1&cVersion=&fontSize=15px&fontWeight=normal")


def test_parse_verses_from_bskorea_html_structure() -> None:
    html = """
    <div id="tdBible1" class="bible_read" style="font-size: 15px; font-weight: normal;">
      <div style="text-align:right"><a href="#none"><img src="/images/sub/bible/btn_listen.png"></a></div>
      <b>개역개정</b><br>
      <font style="display:none;" size="2">민수기</font>
      <font class="chapNum">제 1 장</font><br><br>
      <font class="smallTitle">첫 소제목</font><br><br>
      <span style="color:#376BCB;"><span class="number">1&nbsp;&nbsp;&nbsp;</span>여호와께서 <font class="name">모세</font>에게 말씀하여 이르시되 </span><br>
      <span><span class="number">2&nbsp;&nbsp;&nbsp;</span>수중 <font size="1">생물</font>을 계수하라 </span><br>
      <br><br><font class="smallTitle">중간 소제목</font><br><br>
      <span><span class="number">3&nbsp;&nbsp;&nbsp;</span><font class="area">갓</font> 지파에서는
        <font class="name"><font size="2"><a class="comment" href="#">1)</a></font>드우엘</font>의 아들
        <font class="name">엘리아삽</font>이요
        <div id="D_1" class="D2" style="display:none;z-index:100">2:14 '르우엘'</div>
      </span>
    </div>
    """
    scraper = HolyBibleScraper(
        entry_url=(
            "https://www.bskorea.or.kr/bible/korbibReadpage.php"
            "?version=GAE&book=num&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
        )
    )
    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 3
    assert verses[0].verse_number == 1
    assert verses[0].text == "여호와께서 모세에게 말씀하여 이르시되"
    assert verses[1].verse_number == 2
    assert verses[1].text == "수중 생물을 계수하라"
    assert verses[2].verse_number == 3
    assert verses[2].text == "갓 지파에서는 드우엘의 아들 엘리아삽이요"
    assert "민수기" not in verses[0].text
    assert "첫 소제목" not in verses[0].text
    assert "중간 소제목" not in verses[2].text
    assert "1)" not in verses[2].text
    assert "르우엘" not in verses[2].text


def test_parse_verses_from_bskorea_prefers_tdbible1_when_parallel_exists() -> None:
    html = """
    <div id="tdBible1" class="bible_read">
      <span><span class="number">1&nbsp;&nbsp;&nbsp;</span>첫 번째 본문</span>
    </div>
    <div id="tdBible2" class="bible_read">
      <span><span class="number">1&nbsp;&nbsp;&nbsp;</span>두 번째 본문</span>
    </div>
    """
    scraper = HolyBibleScraper(
        entry_url=(
            "https://www.bskorea.or.kr/bible/korbibReadpage.php"
            "?version=GAE&book=gen&chap=1&sec=1&cVersion=HAN^&fontSize=15px&fontWeight=normal"
        )
    )
    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text == "첫 번째 본문"


def test_parse_verses_from_bskorea_keeps_korean_particles_attached() -> None:
    html = """
    <div id="tdBible1" class="bible_read">
      <span style="color:#376BCB;">
        <span class="number">1&nbsp;&nbsp;&nbsp;</span><font class="name">모세</font>가
        <font class="area">모압</font> 평지에서
        <font class="area">느보</font> 산에 올라가
      </span>
    </div>
    """
    scraper = HolyBibleScraper(
        entry_url=(
            "https://www.bskorea.or.kr/bible/korbibReadpage.php"
            "?version=GAE&book=deu&chap=34&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
        )
    )

    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text == "모세가 모압 평지에서 느보 산에 올라가"


BIBLEGATEWAY_ENTRY_URL = "https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB"


def test_get_source_name_detects_biblegateway() -> None:
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    assert scraper.get_source_name() == "biblegateway"


def test_build_biblegateway_url_rule() -> None:
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    assert scraper._build_chapter_url(1, 1) == (
        "https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB"
    )
    assert scraper._build_chapter_url(40, 28) == (
        "https://www.biblegateway.com/passage/?search=Matthew%2028&version=WEB"
    )


def test_build_biblegateway_url_encodes_multiword_book_name() -> None:
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    assert scraper._build_chapter_url(9, 1) == (
        "https://www.biblegateway.com/passage/?search=1%20Samuel%201&version=WEB"
    )


def test_build_biblegateway_url_inherits_version_from_entry_url() -> None:
    scraper = HolyBibleScraper(
        entry_url="https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV"
    )

    assert scraper._build_chapter_url(1, 2).endswith("?search=Genesis%202&version=ASV")


def test_discover_biblegateway_chapter_urls_uses_canonical_count() -> None:
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    genesis = scraper.discover_chapter_urls_for_book(1)
    jude = scraper.discover_chapter_urls_for_book(65)

    assert len(genesis) == 50
    assert genesis[50].endswith("?search=Genesis%2050&version=WEB")
    assert len(jude) == 1
    assert jude[1].endswith("?search=Jude%201&version=WEB")


def test_biblegateway_source_enforces_crawl_delay_floor() -> None:
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL, sleep_min=0.1, sleep_max=0.2)

    assert scraper.sleep_min >= 15.0
    assert scraper.sleep_max >= 15.0


def test_other_sources_keep_default_sleep_settings() -> None:
    scraper = HolyBibleScraper(entry_url="https://thekingsbible.com/Bible/1/1")

    assert scraper.sleep_min == 0.3
    assert scraper.sleep_max == 1.0


def test_parse_verses_from_biblegateway_html_structure() -> None:
    html = """
    <div class="passage-table" data-osis="Gen.1.1-Gen.1.31">
      <div class="passage-text">
        <div class="passage-content passage-class-0">
          <div class="version-WEB result-text-style-normal text-html">
            <p class="chapter-1">
              <span id="en-WEB-1" class="text Gen-1-1"><span class="chapternum">1&nbsp;</span>In the beginning, God<sup data-fn="#fen-WEB-1a" class="footnote">[<a href="#fen-WEB-1a">a</a>]</sup> created the heavens and the earth. </span>
              <span id="en-WEB-2" class="text Gen-1-2"><sup class="versenum">2&nbsp;</sup>The earth was formless and empty.</span>
            </p>
            <div class="footnotes">
              <h4>Footnotes</h4>
              <ol><li id="fen-WEB-1a"><a href="#en-WEB-1">1:1</a> <span class="footnote-text">The Hebrew word rendered God is Elohim.</span></li></ol>
            </div>
          </div>
        </div>
      </div>
    </div>
    """
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    verses = scraper.parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [1, 2]
    assert verses[0].text == "In the beginning, God created the heavens and the earth."
    assert verses[1].text == "The earth was formless and empty."
    assert all("Footnotes" not in verse.text for verse in verses)
    assert all("Elohim" not in verse.text for verse in verses)


def test_parse_verses_from_biblegateway_uses_class_token_not_chapternum() -> None:
    # The first verse of a chapter renders the chapter number, not the verse number.
    html = """
    <div class="passage-text"><div class="passage-content">
      <div class="version-WEB">
        <p class="chapter-1">
          <span class="text Gen-2-1" id="en-WEB-32"><span class="chapternum">2&nbsp;</span>The heavens, the earth, and all their vast array were finished. </span>
          <span class="text Gen-2-2" id="en-WEB-33"><sup class="versenum">2&nbsp;</sup>On the seventh day God finished his work.</span>
        </p>
      </div>
    </div></div>
    """
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    verses = scraper.parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [1, 2]
    assert verses[0].text.startswith("The heavens")


def test_parse_verses_from_biblegateway_merges_split_spans_and_drops_psalm_title() -> None:
    html = """
    <div class="passage-text"><div class="passage-content">
      <div class="version-WEB">
        <h4 class="psalm-title"><span class="text Ps-23-1" id="en-WEB-14237">A Psalm by David.</span></h4>
        <div class="poetry"><p class="line">
          <span class="chapter-2"><span class="text Ps-23-1"><span class="chapternum">23 </span>Yahweh is my shepherd;</span></span><br/>
          <span class="indent-1"><span class="indent-1-breaks">    </span><span class="text Ps-23-1">I shall lack nothing.</span></span><br/>
          <span class="text Ps-23-2" id="en-WEB-14238"><sup class="versenum">2 </sup>He makes me lie down in green pastures.</span>
        </p></div>
      </div>
    </div></div>
    """
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    verses = scraper.parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [1, 2]
    assert verses[0].text == "Yahweh is my shepherd; I shall lack nothing."


def test_parse_verses_from_biblegateway_keeps_words_of_jesus() -> None:
    html = """
    <div class="passage-text"><div class="passage-content">
      <div class="version-WEB">
        <p><span class="text Matt-5-3" id="en-WEB-23238"><sup class="versenum">3 </sup><span class="woj">Blessed are the poor in spirit,</span><sup class="crossreference" data-cr="#cen-WEB-23238A">(<a href="#cen-WEB-23238A">A</a>)</sup></span></p>
        <div class="poetry"><p class="line"><span class="indent-1"><span class="text Matt-5-3"><span class="woj">for theirs is the Kingdom of Heaven.</span></span></span></p></div>
        <div class="crossrefs hidden"><a class="crossref-link" href="#">Matthew 5:3</a> : Isaiah 57:15</div>
      </div>
    </div></div>
    """
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text == "Blessed are the poor in spirit, for theirs is the Kingdom of Heaven."


def test_parse_verses_from_biblegateway_uses_first_passage_text_only() -> None:
    html = """
    <div class="passage-text"><div class="passage-content"><div class="version-WEB">
      <p><span class="text Gen-1-1">Primary translation verse.</span></p>
    </div></div></div>
    <div class="passage-text"><div class="passage-content"><div class="version-NIV">
      <p><span class="text Gen-1-1">Parallel translation verse.</span></p>
    </div></div></div>
    """
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text == "Primary translation verse."


def test_parse_verses_from_biblegateway_ignores_other_chapters() -> None:
    html = """
    <div class="passage-text"><div class="passage-content"><div class="version-WEB">
      <p>
        <span class="text Gen-1-30">Verse thirty of chapter one.</span>
        <span class="text Gen-1-31">Verse thirty-one of chapter one.</span>
        <span class="text Gen-2-1">Verse one of chapter two.</span>
      </p>
    </div></div></div>
    """
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    verses = scraper.parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [30, 31]


def test_parse_verses_from_biblegateway_records_untranslated_verse() -> None:
    # WEB leaves Acts 8:37 untranslated: the span holds only a footnote marker.
    html = """
    <div class="passage-text"><div class="passage-content"><div class="version-WEB">
      <p>
        <span class="text Acts-8-36" id="en-WEB-1"><sup class="versenum">36 </sup>They came to some water.</span>
        <span class="text Acts-8-37" id="en-WEB-2"><sup class="versenum">37 </sup><sup data-fn="#fen-WEB-a" class="footnote">[<a href="#fen-WEB-a">a</a>]</sup></span>
        <span class="text Acts-8-38" id="en-WEB-3"><sup class="versenum">38 </sup>He commanded the chariot to stand still.</span>
      </p>
    </div></div></div>
    """
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    verses = scraper.parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [36, 37, 38]
    assert verses[1].text == "(omitted)"


def test_parse_verses_from_biblegateway_drops_empty_span_without_footnote() -> None:
    # Guard: an empty span with no footnote is a parse failure, not an omission.
    html = """
    <div class="passage-text"><div class="passage-content"><div class="version-WEB">
      <p>
        <span class="text Gen-1-1" id="en-WEB-1"><sup class="versenum">1 </sup>Real verse text.</span>
        <span class="text Gen-1-2" id="en-WEB-2"><sup class="versenum">2 </sup></span>
      </p>
    </div></div></div>
    """
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    verses = scraper.parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [1]


def test_parse_verses_from_biblegateway_prefers_translated_fragment_over_marker() -> None:
    html = """
    <div class="passage-text"><div class="passage-content"><div class="version-WEB">
      <p>
        <span class="text Luke-17-36"><sup class="versenum">36 </sup><sup class="footnote">[<a href="#a">a</a>]</sup></span>
        <span class="text Luke-17-36">Actual translated line.</span>
      </p>
    </div></div></div>
    """
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)

    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text == "Actual translated line."


def test_parse_verses_from_biblegateway_drops_editorial_section_heading() -> None:
    # ASV renders editorial headings as <h3> and tags them with the verse-1 class,
    # so keeping them would prepend the heading to Psalms 23:1. WEB has no <h3> at
    # all, which makes this the only coverage for that removal rule.
    html = """
    <div class="passage-text"><div class="passage-content"><div class="version-ASV">
      <h4 class="psalm-title"><span class="text Ps-23-1">A Psalm of David.</span></h4>
      <h3><span class="text Ps-23-1" id="en-ASV-14237">Jehovah the psalmist's shepherd.</span></h3>
      <div class="poetry"><p class="line">
        <span class="text Ps-23-1"><span class="chapternum">23 </span>Jehovah is my shepherd;</span><br/>
        <span class="text Ps-23-1">I shall not want.</span>
      </p></div>
    </div></div></div>
    """
    scraper = HolyBibleScraper(
        entry_url="https://www.biblegateway.com/passage/?search=Psalms%2023&version=ASV"
    )

    verses = scraper.parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text == "Jehovah is my shepherd; I shall not want."


def test_parse_verses_from_biblegateway_handles_asv_chapter_without_verse_span() -> None:
    # ASV omits Acts 8:37 by dropping the span entirely; the footnote marker hangs off
    # verse 36. Nothing should be invented for the missing number.
    html = """
    <div class="passage-text"><div class="passage-content"><div class="version-ASV">
      <p>
        <span class="text Acts-8-36"><sup class="versenum">36 </sup>They came unto a certain water.<sup class="footnote">[<a href="#f">l</a>]</sup></span>
        <span class="text Acts-8-38"><sup class="versenum">38 </sup>And he commanded the chariot to stand still.</span>
      </p>
    </div></div></div>
    """
    scraper = HolyBibleScraper(
        entry_url="https://www.biblegateway.com/passage/?search=Acts%208&version=ASV"
    )

    verses = scraper.parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [36, 38]
    assert all(verse.text != "(omitted)" for verse in verses)


def test_biblegateway_parser_returns_empty_for_other_sources() -> None:
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)
    soup = BeautifulSoup("<div class='bible_read'><p>1 text</p></div>", "html.parser")

    assert scraper._extract_verses_from_biblegateway_passage(soup) == []
