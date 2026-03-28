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
