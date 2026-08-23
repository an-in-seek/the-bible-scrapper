from bs4 import BeautifulSoup

from scraper import OMITTED_VERSE_TEXT, HolyBibleScraper


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


EBIBLE_ENTRY_URL = "https://ebible.org/spaRV1909/GEN01.htm"

EBIBLE_CHAPTER_HTML = """
<ul class="tnav"><li><a href="index.htm">Génesis</a></li><li><a href="GEN02.htm">&gt;</a></li></ul>
<div class="main">
<div class="mt">Génesis</div><div class="chapterlabel" id="V0"> 1</div><div class="p">
<span class="verse" id="V1">1&nbsp;</span>EN el principio crió Dios los cielos y la tierra.
<span class="verse" id="V2">2&nbsp;</span>Y la tierra estaba desordenada y vacía.
<span class="verse" id="V3">3&nbsp;</span>Y dijo Dios: Júntense las aguas que <span class="add">están</span> debajo de los cielos.
</div>
<ul class="tnav"><li><a href="index.htm">Génesis</a></li></ul>
<div class="footnote"><hr></div>
<div class="copyright"><p><a href="copyright.htm">Public Domain</a></p></div>
</div>
"""


class FakeResponse:
    """Minimal stand-in for requests.Response for encoding tests."""

    def __init__(self, body: str, content_type: str, encoding: str | None) -> None:
        self.content = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}
        self.status_code = 200
        self.encoding = encoding
        self.apparent_encoding = "utf-8"

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding or "utf-8", errors="replace")

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.headers: dict[str, str] = {}

    def get(self, url: str, timeout: int | None = None) -> FakeResponse:
        return self.response


def _ebible_scraper() -> HolyBibleScraper:
    scraper = HolyBibleScraper(entry_url=EBIBLE_ENTRY_URL)
    # The constructor raises these to the politeness floor; drop them again so the
    # unit tests do not sleep. Coverage for the floor itself lives in its own test.
    scraper.sleep_min = 0.0
    scraper.sleep_max = 0.0
    return scraper


def test_get_source_name_detects_ebible() -> None:
    assert _ebible_scraper().get_source_name() == "ebible"


def test_build_ebible_url_pads_chapter_per_book() -> None:
    scraper = _ebible_scraper()

    assert scraper._build_chapter_url(1, 1) == "https://ebible.org/spaRV1909/GEN01.htm"
    assert scraper._build_chapter_url(1, 50) == "https://ebible.org/spaRV1909/GEN50.htm"
    # Psalms has 150 chapters, so eBible pads it to three digits: PSA23.htm is a 404.
    assert scraper._build_chapter_url(19, 23) == "https://ebible.org/spaRV1909/PSA023.htm"
    assert scraper._build_chapter_url(19, 119) == "https://ebible.org/spaRV1909/PSA119.htm"
    assert scraper._build_chapter_url(64, 1) == "https://ebible.org/spaRV1909/3JN01.htm"
    assert scraper._build_chapter_url(66, 22) == "https://ebible.org/spaRV1909/REV22.htm"


def test_build_ebible_url_inherits_translation_code_from_entry_url() -> None:
    scraper = HolyBibleScraper(
        entry_url="https://ebible.org/engwebp/GEN01.htm", sleep_min=0.0, sleep_max=0.0
    )

    assert scraper._build_chapter_url(1, 2) == "https://ebible.org/engwebp/GEN02.htm"


def test_discover_ebible_chapter_urls_uses_canonical_count() -> None:
    scraper = _ebible_scraper()

    assert len(scraper.discover_chapter_urls_for_book(1)) == 50
    assert len(scraper.discover_chapter_urls_for_book(19)) == 150
    assert len(scraper.discover_chapter_urls_for_book(65)) == 1


def test_ebible_source_applies_politeness_delay_floor() -> None:
    scraper = HolyBibleScraper(entry_url=EBIBLE_ENTRY_URL)

    assert scraper.sleep_min >= 1.0
    assert scraper.sleep_max >= 2.0


def test_parse_verses_from_ebible_page_accumulates_between_markers() -> None:
    verses = _ebible_scraper().parse_verses_from_html(EBIBLE_CHAPTER_HTML)

    assert [verse.verse_number for verse in verses] == [1, 2, 3]
    assert verses[0].text == "EN el principio crió Dios los cielos y la tierra."
    # The marker text must not leak into the body.
    assert not verses[0].text.startswith("1")
    # Supplied words are body text.
    assert "están" in verses[2].text
    # Navigation, book title and copyright must not appear.
    assert all("Génesis" not in verse.text for verse in verses)
    assert all("Public Domain" not in verse.text for verse in verses)


def test_parse_verses_from_ebible_page_separates_block_boundaries() -> None:
    # Defensive rule: no observed RV1909 chapter splits a verse across blocks, so this
    # is the only coverage that the join inserts a space instead of gluing words.
    html = """
    <div class="main">
      <div class="p"><span class="verse" id="V1">1&nbsp;</span>primera parte</div>
      <div class="p">segunda parte</div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text == "primera parte segunda parte"


def test_parse_verses_from_ebible_page_drops_headings_between_verses() -> None:
    # eBible renders acrostic titles (div.d) and speaker labels (div.sp) as blocks that
    # carry no verse marker. Left in place they append to the PREVIOUS verse: Psalms 119
    # leaked 20 headings and Song of Songs 1 leaked 7 before these were removed.
    html = """
    <div class="main">
      <div class="chapterlabel" id="V0">119</div>
      <div class="d">ALEF</div>
      <div class="q"><span class="verse" id="V1">1&nbsp;</span>primera linea</div>
      <div class="q2"><span class="verse" id="V2">2&nbsp;</span>segunda linea</div>
      <div class="d">BET</div>
      <div class="q"><span class="verse" id="V3">3&nbsp;</span>tercera linea</div>
      <div class="sp">Amado</div>
      <div class="q"><span class="verse" id="V4">4&nbsp;</span>cuarta linea</div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [1, 2, 3, 4]
    assert verses[1].text == "segunda linea"
    assert verses[2].text == "tercera linea"
    assert all("ALEF" not in verse.text for verse in verses)
    assert all("BET" not in verse.text for verse in verses)
    assert all("Amado" not in verse.text for verse in verses)


def test_parse_verses_from_ebible_page_drops_inline_footnote_popup() -> None:
    # The footnote marker nests the note body in span.popup inside the verse text.
    html = """
    <div class="main">
      <div class="p">
        <span class="verse" id="V24">24&nbsp;</span>guardar el camino del arbol de la
        vida<a href="#FN1" class="notemark">*<span class="popup">Nota al pie que no
        pertenece al texto biblico.</span></a>
      </div>
      <div class="footnote"><p class="f" id="FN1"><span class="ft">Nota al pie.</span></p></div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text.endswith("vida")
    assert "Nota al pie" not in verses[0].text


def test_parse_verses_from_ebible_page_keeps_words_of_jesus() -> None:
    html = """
    <div class="main">
      <div class="p"><span class="verse" id="V17">17&nbsp;</span>Jesus les dijo:
      <span class="wj">«Venid en pos de mi»</span>.</div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert len(verses) == 1
    assert "Venid en pos de mi" in verses[0].text


def test_parse_verses_from_ebible_page_joins_verse_across_blocks() -> None:
    """A verse split over two blocks must join with exactly one space.

    RV1909 puts a whole chapter in one div.p, so this path never ran there. spablm
    splits prose into many div.p and poetry into div.q/div.q2, and Genesis 3:13 really
    does straddle a block boundary.
    """
    html = """
    <div class="main">
      <div class="p"><span class="verse" id="V13">13&nbsp;</span>&#191;Qu&#233; es lo que has hecho?</div>
      <div class="p">Y dijo la mujer.</div>
      <div class="q"><span class="verse" id="V14">14&nbsp;</span>Maldita ser&#225;s</div>
      <div class="q2">entre todas las bestias.</div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [13, 14]
    assert verses[0].text == "¿Qué es lo que has hecho? Y dijo la mujer."
    assert verses[1].text == "Maldita serás entre todas las bestias."


def test_ebible_chapter_urls_follow_the_entry_url_translation_code() -> None:
    """The translation code comes from the entry URL path, so spablm needs no new code."""
    scraper = HolyBibleScraper(entry_url="https://ebible.org/spablm/GEN01.htm")
    scraper.sleep_min = 0.0
    scraper.sleep_max = 0.0

    assert scraper.get_source_name() == "ebible"
    assert scraper._build_ebible_url(1, 1) == "https://ebible.org/spablm/GEN01.htm"
    # Psalms pads to three digits; PSA23.htm is a 404.
    assert scraper._build_ebible_url(19, 23) == "https://ebible.org/spablm/PSA023.htm"
    assert scraper._build_ebible_url(64, 1) == "https://ebible.org/spablm/3JN01.htm"


def test_get_source_version_reads_ebible_code_from_path_and_others_from_query() -> None:
    def version_for(url: str) -> str | None:
        scraper = HolyBibleScraper(entry_url=url)
        scraper.sleep_min = 0.0
        scraper.sleep_max = 0.0
        return scraper.get_source_version()

    assert version_for("https://ebible.org/spaRV1909/GEN01.htm") == "spaRV1909"
    assert version_for("https://ebible.org/spablm/GEN01.htm") == "spablm"
    assert version_for("https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV") == "ASV"
    assert version_for("https://thekingsbible.com/Bible/1/1") is None


def test_parse_verses_from_ebible_page_marks_footnote_only_verse_as_omitted() -> None:
    """spablm drops the same verses WEB does, leaving the marker plus a footnote.

    Recording them keeps verse numbering contiguous, so a real gap still reads as a
    scrape failure rather than a translation choice.
    """
    html = """
    <div class="main">
      <div class="p"><span class="verse" id="V35">35&nbsp;</span>Dos moler&#225;n juntas.</div>
      <div class="p"><span class="verse" id="V36">36&nbsp;</span><a href="#FN1" class="notemark">*<span
        class="popup">Algunos manuscritos griegos a&#241;aden este vers&#237;culo.</span></a></div>
      <div class="p"><span class="verse" id="V37">37&nbsp;</span>Ellos respondiendo.</div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [35, 36, 37]
    assert verses[1].text == OMITTED_VERSE_TEXT
    assert "manuscritos" not in verses[1].text


def test_parse_verses_from_ebible_page_skips_empty_verse_without_footnote() -> None:
    """No footnote means no evidence of an intentional omission: skip, do not mark.

    Marking every empty span would let a DOM change quietly fill the DB with
    placeholders instead of failing loudly.
    """
    html = """
    <div class="main">
      <div class="p"><span class="verse" id="V1">1&nbsp;</span>Primero.</div>
      <div class="p"><span class="verse" id="V2">2&nbsp;</span></div>
      <div class="p"><span class="verse" id="V3">3&nbsp;</span>Tercero.</div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [1, 3]


def test_parse_verses_from_ebible_page_keeps_body_text_that_has_a_footnote() -> None:
    """A footnote alongside real text must not trigger the omitted marker."""
    html = """
    <div class="main">
      <div class="p"><span class="verse" id="V1">1&nbsp;</span>En el principio<a href="#FN1"
        class="notemark">*<span class="popup">Nota del traductor.</span></a> Dios cre&#243;.</div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text != OMITTED_VERSE_TEXT
    assert "Nota del traductor" not in verses[0].text
    assert "En el principio" in verses[0].text


def _jpnm_scraper() -> HolyBibleScraper:
    scraper = HolyBibleScraper(entry_url="https://ebible.org/jpnm/GEN01.htm")
    scraper.sleep_min = 0.0
    scraper.sleep_max = 0.0
    return scraper


def test_parse_verses_from_ebible_page_joins_japanese_without_space() -> None:
    """Japanese writes no spaces between words, so the block join must not add one.

    The same separator is required for Spanish and English, which is why the rule is
    conditioned on both sides being CJK rather than removed outright.
    """
    html = """
    <div class="main">
      <div class="q"><span class="verse" id="V1">1&nbsp;</span>主は私の羊飼い。</div>
      <div class="q2">私は何も欠けることがない。</div>
      <div class="p"><span class="verse" id="V2">2&nbsp;</span>したのか。」</div>
      <div class="p">女は言った。</div>
    </div>
    """
    verses = _jpnm_scraper().parse_verses_from_html(html)

    assert [verse.verse_number for verse in verses] == [1, 2]
    assert verses[0].text == "主は私の羊飼い。私は何も欠けることがない。"
    assert verses[1].text == "したのか。」女は言った。"


def test_parse_verses_from_ebible_page_keeps_space_between_latin_words() -> None:
    """The Spanish/English block join still needs its space."""
    html = """
    <div class="main">
      <div class="p"><span class="verse" id="V13">13&nbsp;</span>&#191;Qu&#233; has hecho?</div>
      <div class="p">Y dijo la mujer.</div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text == "¿Qué has hecho? Y dijo la mujer."


def test_parse_verses_from_ebible_page_keeps_spaces_in_korean_text() -> None:
    """Hangul must stay outside the CJK range: Korean separates its words with spaces.

    Collapsing here would mirror the bskorea particle bug, turning '모세가 말하되'
    into an unreadable run.
    """
    html = """
    <div class="main">
      <div class="p"><span class="verse" id="V1">1&nbsp;</span>모세가 말하되</div>
      <div class="p">여호와께서 이르시니라</div>
    </div>
    """
    verses = _ebible_scraper().parse_verses_from_html(html)

    assert len(verses) == 1
    assert verses[0].text == "모세가 말하되 여호와께서 이르시니라"


def test_parse_verses_from_ebible_page_keeps_space_between_cjk_and_latin() -> None:
    """Only CJK-to-CJK collapses; a Latin word embedded in Japanese keeps its spaces."""
    html = """
    <div class="main">
      <div class="p"><span class="verse" id="V1">1&nbsp;</span>使徒 Paul は言った。</div>
    </div>
    """
    verses = _jpnm_scraper().parse_verses_from_html(html)

    assert verses[0].text == "使徒 Paul は言った。"


def test_ebible_chapter_urls_follow_jpnm_translation_code() -> None:
    scraper = _jpnm_scraper()

    assert scraper.get_source_name() == "ebible"
    assert scraper.get_source_version() == "jpnm"
    assert scraper._build_ebible_url(1, 1) == "https://ebible.org/jpnm/GEN01.htm"
    assert scraper._build_ebible_url(19, 23) == "https://ebible.org/jpnm/PSA023.htm"


def test_ebible_parser_returns_empty_for_other_sources() -> None:
    scraper = _ebible_scraper()
    soup = BeautifulSoup("<div class='bible_read'><p>1 text</p></div>", "html.parser")

    assert scraper._extract_verses_from_ebible_page(soup) == []


def test_request_html_recovers_encoding_when_header_omits_charset() -> None:
    scraper = _ebible_scraper()
    response = FakeResponse("<p>JEHOVÁ es mi pastor</p>", "text/html", "ISO-8859-1")
    scraper.session = FakeSession(response)

    html = scraper._request_html("https://ebible.org/spaRV1909/PSA023.htm")

    assert "JEHOVÁ" in html
    assert response.encoding == "utf-8"


def test_request_html_keeps_declared_charset_untouched() -> None:
    scraper = _ebible_scraper()
    response = FakeResponse("<p>ok</p>", "text/html; charset=UTF-8", "UTF-8")
    scraper.session = FakeSession(response)

    scraper._request_html("https://example.com/page.htm")

    assert response.encoding == "UTF-8"


def test_biblegateway_parser_returns_empty_for_other_sources() -> None:
    scraper = HolyBibleScraper(entry_url=BIBLEGATEWAY_ENTRY_URL)
    soup = BeautifulSoup("<div class='bible_read'><p>1 text</p></div>", "html.parser")

    assert scraper._extract_verses_from_biblegateway_passage(soup) == []
