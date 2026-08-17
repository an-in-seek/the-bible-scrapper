# BibleGateway WEB(World English Bible) 본문 스크래핑 개발 설계

## 1. 목적

현재 저장소는 아래 두 소스를 지원한다.

- `thekingsbible.com` KJV
- `bskorea.or.kr` NKRV(`version=GAE`)

이번 설계의 목적은 세 번째 소스로 `biblegateway.com`의 WEB(World English Bible) 본문을 동일한 파이프라인으로 수집해 **창세기 1장부터 요한계시록 22장까지 66권 전 구절을 DB에 적재**하는 것이다.

즉 최종 산출물은 특정 장 샘플이 아니라 아래 전량이다.

- 66권 / 1,189장 (구약 929장 + 신약 260장)
- 각 장의 전 절 (KJV 기준 약 31,100절 규모)

부분 실행(`--start-book`, `--start-chapter`)은 어디까지나 분할 실행과 검증 수단이며, 완료 기준은 [11. 전권 적재 운영 계획](#11-전권-적재-운영-계획)의 검증 쿼리를 모두 통과하는 상태다. 단, 검증 4는 WEB에 본문이 없는 **알려진 4건**을 예외로 인정한다.

- 예시 URL
  - `https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB`
  - `https://www.biblegateway.com/passage/?search=Genesis%202&version=WEB`
  - `https://www.biblegateway.com/passage/?search=Genesis%2010&version=WEB`
  - `https://www.biblegateway.com/passage/?search=Genesis%2050&version=WEB`
  - `https://www.biblegateway.com/passage/?search=Matthew%201&version=WEB`
  - `https://www.biblegateway.com/passage/?search=Matthew%2028&version=WEB`
  - `https://www.biblegateway.com/passage/?search=1%20Samuel%201&version=WEB`

대상 역본은 `WEB`이며, 설계는 `version` 파라미터만 교체하면 BibleGateway의 다른 영어 역본에도 재사용 가능하도록 구성한다.  
단, 저작권이 있는 역본(NIV, ESV 등)은 수집 대상으로 삼지 않는다. 자세한 내용은 [13. 라이선스와 운영 리스크](#13-라이선스와-운영-리스크)를 참고한다.

권장 기본 엔트리 URL 환경변수:

```env
WEB_ENTRY_URL=https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB
```

## 2. 대상 페이지 특성

### 2.1 URL 파라미터

- `search`
  - 조회 대상 구절 표현식. 예: `Genesis 1`, `1 Samuel 1`
  - 공백은 `%20`으로 인코딩된다.
  - 장 단위 수집에서는 `"{영문 책명} {장 번호}"` 형태만 사용한다.
- `version`
  - 역본 코드. 예: `WEB`
- 그 외 `interface=print`, `;NIV` 병렬 지정 같은 옵션은 사용하지 않는다.
  - 병렬 역본을 지정하면 본문 컨테이너가 다중화되어 파싱이 복잡해진다.

bskorea가 `book`/`chap` 숫자·코드 파라미터를 쓰는 것과 달리, BibleGateway는 사람이 읽는 구절 표현식을 그대로 쿼리로 받는다.  
따라서 `book_order -> 영문 책명` 매핑이 URL 생성의 핵심이다.

### 2.2 DOM 구조

아래 구조는 실제 응답 6건(Genesis 1 / Genesis 2 / Psalms 23 / 1 Samuel 1 / Matthew 5 / Jude)을 받아 확인한 것이다. 실측 수치는 [부록 C](#부록-c-실측-검증-결과)에 있다.

**산문 본문(Genesis 1)**

```text
div.passage-table[data-osis="Gen.1.1-Gen.1.31"]
└ div.passage-cols
  └ div.passage-col.passage-col-mobile.version-WEB[data-translation="WEB"]
    ├ h1.passage-display        (책/장 표시, 역본 드롭다운)
    ├ div.dropdowns             (역본 select 목록)
    └ div.passage-text
      └ div.passage-content.passage-class-0
        └ div.version-WEB.result-text-style-normal.text-html
          ├ p.chapter-1
          │ ├ span#en-WEB-1.text.Gen-1-1
          │ │ ├ span.chapternum     "1 "
          │ │ ├ (본문 텍스트)
          │ │ └ sup.footnote        "[a]"
          │ └ span#en-WEB-2.text.Gen-1-2
          │   ├ sup.versenum        "2 "
          │   └ (본문 텍스트)
          ├ p ... (이하 문단 반복)
          └ div.footnotes
            └ ol > li#fen-WEB-1a > span.footnote-text
```

**시가 본문(Psalms 23)** — 구조가 다르다.

```text
div.version-WEB.result-text-style-normal.text-html
├ h4.psalm-title
│ └ span.text.Ps-23-1              "A Psalm by David."   <- 표제인데 1절 클래스를 가짐
└ div.poetry
  └ p.line
    ├ span.chapter-2 > span.text.Ps-23-1 > span.chapternum "23 " + "Yahweh is my shepherd;"
    ├ br
    ├ span.indent-1
    │ ├ span.indent-1-breaks       (공백 4칸)
    │ └ span.text.Ps-23-1          "I shall lack nothing."
    └ ... (br + indent + 조각 반복)
```

**신약 본문(Matthew 5)** — 위 둘이 섞이고 상호 참조가 추가된다.

```text
div.version-WEB...
├ p.chapter-1                       (산문 절)
├ div.poetry.top-1                  (팔복 등 시가 절)
├ p ...
├ div.footnotes
└ div.crossrefs.hidden
```

핵심 특징:

- 절 노드는 `span.text`이며, 클래스에 `Gen-1-1` 형태의 `OSIS약어-장-절` 토큰이 함께 붙는다.
  - OSIS 약어는 검색어와 다르다. `search=Psalms 23` -> `Ps-23-1`, `search=1 Samuel 1` -> `1Sam-1-1`
- 절은 문단(`p`) 또는 시가 블록(`div.poetry > p.line`) 안에 인라인으로 나열된다. 문단·행 경계는 절 경계와 일치하지 않는다.
- 각주는 본문 안 `sup.footnote`(`[a]`)와 문서 하단 `div.footnotes` 두 곳에 존재한다.
- 상호 참조는 본문 안 `sup.crossreference`(`(A)`)와 문서 하단 `div.crossrefs.hidden`에 존재한다. 신약에서만 관측되었다.
- `span.woj`(예수님 말씀)는 본문 텍스트다. Matthew 5에서 62개 관측.
- `div.footnotes` / `div.crossrefs` 내부에는 `span.text`가 **없다**. 따라서 각주 본문이 절로 오인될 구조적 위험은 없지만, 방어적으로 먼저 제거한다.
- 역본 선택 `select` 안에 400개 이상의 `option`이 들어 있어, 페이지 전체 텍스트 추출은 사실상 사용할 수 없다.

즉, bskorea와 마찬가지로 이 사이트도 범용 정규식 파서가 아니라 **DOM 특화 파서**가 필요하다.

### 2.3 반드시 주의해야 하는 함정

이 소스에서 가장 위험한 항목 4개를 먼저 명시한다. 모두 실제 응답에서 재현을 확인했다.

#### 함정 1. `span.chapternum`은 절 번호가 아니다

각 장의 **1절**은 절 번호 대신 장 번호를 표시한다.

```html
<span id="en-WEB-1" class="text Gen-1-1"><span class="chapternum">1&nbsp;</span>In the beginning, God...</span>
```

Genesis 2:1이면 아래처럼 렌더링된다.

```html
<span class="text Gen-2-1" id="en-WEB-32"><span class="chapternum">2 </span>The heavens, the earth, and all their vast array were finished. </span>
```

(실제 응답에서 그대로 확인한 마크업이다.)

여기서 화면 표시 숫자를 절 번호로 읽으면 Genesis 2:1이 2절로 저장된다.  
따라서 **절 번호는 반드시 `class`의 `Gen-2-1` 토큰에서 추출해야 한다.** `chapternum`/`versenum` 텍스트는 절 번호 판정에 사용하지 않는다.

또한 **단일 장 책에는 `span.chapternum`이 아예 없다.** Jude는 1절도 `sup.versenum`을 쓴다(`chapternum` 0개 관측). 따라서 "1절에는 항상 chapternum이 있다"는 가정도 세우면 안 된다.

#### 함정 2. `id` 속성은 절 번호가 아니다

`id="en-WEB-1"`의 숫자는 페이지 내부 일련번호이며 절 번호가 아니다.  
Genesis 1은 우연히 1..31로 일치하지만, 장이 바뀌면 어긋난다. `id`는 파싱 기준으로 쓰지 않는다.

#### 함정 3. 하나의 절이 여러 `span`으로 쪼개진다

시가 본문(`div.poetry > p.line`)에서는 같은 절이 여러 `span.text`로 분할되며, 이때 **동일한 클래스 토큰이 반복**된다.

```html
<span class="text Ps-23-1"><span class="chapternum">23 </span>Yahweh is my shepherd;</span>
<br/>
<span class="indent-1"><span class="indent-1-breaks">    </span><span class="text Ps-23-1">I shall lack nothing.</span></span>
```

실측 분할 규모:

| 장 | `span.text` 개수 | 실제 절 수 | 최대 분할 |
| --- | --- | --- | --- |
| Psalms 23 | 17 | 6 | 4조각 (4절, 5절) |
| Matthew 5 | 56 | 48 | 2조각 (3~10절 팔복) |
| 1 Samuel 1 | 29 | 28 | 2조각 (23절) |
| Genesis 1 | 31 | 31 | 분할 없음 |

절 번호 단위로 "첫 번째만 채택"하면 Psalms 23:4는 4조각 중 1조각만 남는다.  
따라서 파서는 **절 번호 기준 그룹핑 후 문서 순서대로 이어붙이는** 방식이어야 한다.  
이는 bskorea 파서의 "중복 절 번호는 첫 번째만 채택" 규칙과 정반대이므로, 공통 `_sanitize_verses`에 도달하기 전에 파서 내부에서 병합을 끝내야 한다.

조각 사이 구분자는 **단일 공백**이다. 조각 텍스트에는 뒤 공백이 없고 들여쓰기 공백(`span.indent-1-breaks`)은 `span.text` 바깥에 있으므로, 공백 없이 이으면 `shepherd;I shall`처럼 붙는다.

#### 함정 4. 시편 표제가 1절 클래스를 달고 있다

```html
<h4 class="psalm-title"><span class="text Ps-23-1" id="en-WEB-14237">A Psalm by David.</span></h4>
```

`A Psalm by David.`는 표제인데 BibleGateway는 여기에 **`Ps-23-1` 클래스**를 붙인다.  
그대로 수집하면 Psalms 23:1이 `A Psalm by David. Yahweh is my shepherd; I shall lack nothing.`가 된다.

**결정: 표제는 저장하지 않는다.** `h4.psalm-title`을 파싱 전에 제거한다.

근거:

- 같은 DB의 KJV(`thekingsbible`), NKRV(`bskorea`)는 표제/소제목을 절 본문에 넣지 않는다. 역본 간 절 본문 정의가 어긋나면 대조 조회가 깨진다.
- WEB 인쇄본에서도 시편 표제는 절 번호가 없는 제목으로 조판된다.

이 규칙은 `h3`가 아니라 **`h4`** 태그라는 점에 주의한다. 실제 응답은 `h4.psalm-title`이며, `h3` 소제목은 6개 샘플 전부에서 0개였다(WEB에는 편집자 소제목이 없다).

## 3. 목표 데이터 모델

현재 코드베이스의 DTO를 그대로 사용한다.

- `models.py`
  - `ChapterPayload`
  - `Verse`

필수 산출물:

- `book_order`
- `chapter_number`
- `source_url`
- `verses`
  - `verse_number`
  - `text`

`translation_id`는 파싱 결과 DTO의 산출물이 아니라, DB 적재 시 `bible_book` 조회 범위를 결정하는 적재 컨텍스트 값으로 취급한다.

### 3.1 번역본 메타데이터 전제

WEB 적재를 위해서는 `public.bible_translation`에 대상 row가 먼저 있어야 한다. 예:

```sql
INSERT INTO public.bible_translation
(language_code, translation_order, id, "name", translation_type)
VALUES ('en', 3, 3, 'World English Bible', 'WEB');
```

`id` 값은 환경마다 다르므로 구현은 숫자를 하드코딩하지 않고, 아래 조건 조회로 결정한다.

- `translation_type = 'WEB'`
- `name = 'World English Bible'`
- `language_code = 'en'`

`db.BibleRepository._get_translation_id()`가 이미 이 조합 조회를 지원하므로 추가 구현은 필요 없다.

### 3.2 book / chapter / verse 재사용 정책

기존 소스와 동일하다.

- `bible_book`은 생성하지 않고 조회만 한다. 대상 `translation_id` 기준 `book_order=1..66`이 이미 존재해야 한다.
- `bible_chapter`는 기존 row를 재사용하고, 없는 장만 insert 한다.
- `bible_verse`는 기존 `verse_number`를 조회해 없는 절만 insert 한다.
- 재실행 시 중복 insert가 발생하지 않아야 한다.

### 3.3 저장하지 않는 메타데이터

1차 범위에서는 아래를 저장하지 않는다.

- 각주 본문 (`div.footnotes`)
- 상호 참조 (`div.crossrefs`)
- 소제목 (`h3`)
- 시편 표제 (`p.psalm-title`)
- 역본 표시명 (`World English Bible`)

다만 파서 검증 로그에는 활용 가능하다.

## 4. 설계 방향

### 4.1 핵심 원칙

- URL 규칙이 결정적이므로 링크 탐색이 아니라 직접 URL 생성 방식을 사용한다.
- 파싱 범위는 `div.passage-text` 하위로 엄격히 제한한다.
- 절 식별은 `span.text`의 `클래스 토큰`만을 신뢰한다.
- 같은 절 번호의 분할 `span`은 문서 순서대로 병합한다.
- 각주/상호참조/소제목/번호 마크업은 제거하고 본문 인라인 마크업은 텍스트만 남긴다.
- 기존 DB 적재 로직과 retry/throttle 로직은 그대로 재사용하고, URL 생성과 DOM 파싱만 추가한다.

### 4.2 구조 선택

bskorea 설계 문서는 어댑터 분리(옵션 B)를 기준안으로 제시했지만, 현재 저장소는 아직 옵션 A(=`scraper.py` 내부 분기) 형태로 구현되어 있다.

- `_is_thekingsbible_source()` / `_is_bskorea_source()`
- `_build_thekingsbible_url()` / `_build_bskorea_url()`
- `_discover_chapter_urls_for_thekingsbible()` / `_discover_chapter_urls_for_bskorea()`
- `_extract_verses_from_bskorea_read_page()`

따라서 이번 WEB 추가는 **현재 구조와 동일한 옵션 A 방식으로 구현**한다. 세 번째 소스를 같은 패턴으로 붙여 대칭성을 유지하는 편이, 지금 시점에 어댑터 리팩터링을 병행하는 것보다 리스크가 작다.

추가 대상:

- `_is_biblegateway_source()`
- `_build_biblegateway_url()`
- `_discover_chapter_urls_for_biblegateway()`
- `_extract_verses_from_biblegateway_passage()`
- `get_source_name()`에 `"biblegateway"` 분기

다만 소스가 3개가 되는 시점에 `HolyBibleScraper`의 책임이 임계점에 근접하므로, **네 번째 소스를 추가할 때는 어댑터 분리를 선행 조건으로 삼는다.** 이 판단 기준을 문서에 남겨 둔다.

## 5. URL 생성 설계

### 5.1 책 이름 매핑

BibleGateway는 `book=lev` 같은 코드가 아니라 영문 책명을 사용한다. `book_order -> 영문 책명` 고정 매핑 상수를 정의한다.

```python
BIBLEGATEWAY_BOOK_NAMES: tuple[str, ...] = (
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
)
```

주의 사항:

- 숫자 책은 `1 Samuel`처럼 공백을 포함한다. 인코딩 시 `1%20Samuel`이 된다.
- `Revelation`이며 `Revelations`가 아니다.
- `Psalms`, `Psalm` 모두 조회되지만 상수는 `Psalms`로 고정한다.
- `Song of Solomon`을 사용한다. `Song of Songs`도 조회되지만 상수는 하나로 고정한다.

`bible_book.book_key`는 **사용하지 않는다.**  
bskorea는 `book_key.lower()`가 사이트 코드와 형태가 유사해 `resolve_book_code_for_source()`에서 우선 사용했지만, BibleGateway는 `GEN` 같은 축약 키가 아니라 사람이 읽는 이름을 기대하므로 DB 값에 의존할 이유가 없다. 상수 매핑만 신뢰한다.

`resolve_book_code_for_source()`는 아래처럼 확장한다.

```python
if scraper.get_source_name() == "biblegateway":
    return scraper._get_biblegateway_book_name(book.book_order)
```

즉 기존 `book_code` 파라미터 배관을 그대로 재사용하며, 시그니처 변경은 없다.

### 5.2 장 URL 생성

```text
https://www.biblegateway.com/passage/
  ?search={book_name}%20{chapter_number}
  &version={version}
```

인코딩 규칙:

- `urlencode()`는 공백을 `+`로 바꾸므로 사용하지 않는다. 관측된 URL 형태(`%20`)와 일치시키기 위해 `quote()`를 사용한다.

```python
from urllib.parse import quote

search = quote(f"{book_name} {chapter_number}")
url = f"{base_url}?search={search}&version={version}"
```

`version` 우선순위:

1. `--entry-url` 또는 `WEB_ENTRY_URL`에 포함된 `version` 쿼리 파라미터
2. 기본값 `WEB`

bskorea의 `_build_bskorea_url()`이 엔트리 URL의 쿼리에서 `version`을 승계하는 것과 동일한 규칙이다.  
엔트리 URL의 `search` 값은 승계하지 않고 항상 재생성한다.

예:

- 창세기 1장
  - `https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB`
- 창세기 50장
  - `https://www.biblegateway.com/passage/?search=Genesis%2050&version=WEB`
- 마태복음 1장
  - `https://www.biblegateway.com/passage/?search=Matthew%201&version=WEB`
- 사무엘상 1장
  - `https://www.biblegateway.com/passage/?search=1%20Samuel%201&version=WEB`

### 5.3 장 목록 생성

WEB은 개신교 정경 66권 구성이며 장 수는 KJV와 동일하다.  
따라서 기존 `KJV_CHAPTER_COUNTS` 상수를 그대로 재사용한다.

```python
def _discover_chapter_urls_for_biblegateway(self, book_order, book_code=None):
    chapter_count = self._get_kjv_chapter_count(book_order)
    if chapter_count is None:
        return {}
    return {
        chapter_num: self._build_biblegateway_url(book_order, chapter_num, book_code=book_code)
        for chapter_num in range(1, chapter_count + 1)
    }
```

문서 1절의 URL 목록에 있는 `Genesis chapter 40`은 예시 나열일 뿐이며, 창세기의 실제 장 수는 상수 기준 `50`이다. 장 수 판단 기준은 항상 `KJV_CHAPTER_COUNTS`이며 문서 예시가 아니다.

단일 장 책(오바댜, 빌레몬, 요한이서, 요한삼서, 유다서)은 `chapter_count = 1`이므로 `search=Jude 1` 한 번만 요청한다.

이 방식의 이점은 bskorea와 동일하다.

- 사이트 메뉴 구조 변경에 영향이 적다.
- 불필요한 추가 요청이 없다.
- 테스트가 결정적이다.

## 6. 본문 파싱 설계

### 6.1 파싱 대상 범위

```python
container = soup.select_one("div.passage-text")
```

`select_one`으로 **첫 번째 컨테이너만** 사용한다.

실측 결과 단일 역본 조회에서는 `div.passage-text`가 **1개**다. `passage-col`과 `passage-col-mobile`은 서로 다른 두 컬럼이 아니라 **같은 div에 함께 붙은 클래스**이므로, 데스크톱/모바일 본문 중복은 발생하지 않는다.

그럼에도 `select_one`을 쓰는 이유는 병렬 역본 때문이다.

- 병렬 역본(`version=WEB;NIV`)이 켜지면 `passage-col`이 역본 수만큼 늘어난다.
- 우리는 `version` 파라미터를 단일 값으로 고정하지만, 엔트리 URL을 사용자가 잘못 넣을 수 있으므로 첫 컨테이너만 쓰는 편이 안전하다.

컨테이너가 없으면 `[]`를 반환해 다음 파서로 넘긴다(현재 `_extract_verses` 폴백 체인과 동일한 계약).

장 번호 필터는 `data-osis`가 아니라 **dominant chapter 방식**을 쓴다.

- `_extract_verses(soup)`는 장 번호를 인자로 받지 않는다. 시그니처를 바꾸면 `parse_verses_from_html()` 공개 API까지 영향이 간다.
- 매칭된 토큰들의 장 번호를 `Counter`로 집계해 최빈값을 채택하고, 그 외 장의 절은 버린다.
- 이는 `_extract_verses_from_bibletable()`과 `_extract_verses_from_chapter_prefixed_lines()`가 이미 쓰고 있는 방식이므로 코드베이스 일관성도 유지된다.
- `data-osis`는 참고용이며 파싱 기준으로 쓰지 않는다.

### 6.2 절 노드 식별 규칙

```python
VERSE_CLASS_PATTERN = re.compile(r"^[A-Za-z0-9]+-(\d{1,3})-(\d{1,3})$")
```

절차:

1. 컨테이너를 복제하고 6.3의 제거 대상을 먼저 `decompose()` 한다.
2. `container.select("span.text")`로 절 후보를 문서 순서대로 순회한다.
3. 각 노드의 `class` 목록에서 `VERSE_CLASS_PATTERN`에 매칭되는 토큰을 찾는다.
4. 매칭 토큰의 첫 번째 그룹이 장 번호, 두 번째 그룹이 절 번호다.
5. 전체를 훑은 뒤 장 번호 최빈값(dominant chapter)을 정하고, 다른 장의 조각은 버린다.
6. 절 번호별로 텍스트 조각을 문서 순서대로 누적한다.
7. 조각을 단일 공백으로 이어붙여 최종 본문을 만든다.

제거를 순회 **이전에** 일괄 수행하는 점이 bskorea 파서와 다르다. bskorea는 절 노드마다 복제 후 제거했지만, 여기서는 `h4.psalm-title` 같은 **절 노드 자체를 통째로 없애야 하는 대상**이 있어 컨테이너 단위 선처리가 필요하다.

클래스 토큰의 책 약어(`Gen`, `Ps`, `1Sam` 등)는 OSIS 약어이며 `search` 파라미터의 책명과 일치하지 않는다.

| `search` | 절 클래스 |
| --- | --- |
| `Genesis 1` | `Gen-1-1` |
| `Psalms 23` | `Ps-23-1` |
| `1 Samuel 1` | `1Sam-1-1` |
| `Matthew 5` | `Matt-5-1` |
| `Jude 1` | `Jude-1-1` |

따라서 **책 약어는 검증에 사용하지 않고 뒤쪽 숫자 2개만 사용한다.** 정규식의 `[A-Za-z0-9]+`는 `1Sam`처럼 숫자로 시작하는 약어를 포함해야 하므로 `[A-Za-z]+`로 좁히면 안 된다.

중첩 방지:

- `span.text` 안에 또 다른 `span.text`가 들어가는 구조는 관측되지 않았지만, 방어적으로 "이미 처리한 노드의 자손인 노드"는 건너뛴다.

### 6.3 제거해야 하는 마크업

컨테이너를 복제한 뒤 아래를 일괄 제거한다.

**반드시 제거해야 함 (실측 확인)**

- `h4.psalm-title`
  - 시편 표제. **1절 클래스를 달고 있어 제거하지 않으면 본문에 섞인다.** 함정 4 참고.
- `span.chapternum`
  - 장 번호 표시. 제거하지 않으면 1절 본문 앞에 장 번호가 붙는다.
- `sup.versenum`
  - 절 번호 표시.
- `sup.footnote`
  - `[a]`, `[b]` 각주 호출 표시. Genesis 1에 2개, Matthew 5에 12개.
- `sup.crossreference`
  - `(A)` 상호 참조 표시. **대괄호가 아니라 소괄호다.** Matthew 5에 9개.

**방어적 제거 (해당 샘플에서 절 오염은 관측되지 않음)**

- `div.footnotes`, `div.crossrefs`
  - 내부에 `span.text`가 없어 구조상 절로 수집되지 않지만, 선제거해 두면 이후 마크업 변경에 안전하다.
- `p.psalm-title`, `h3`, `p.translation-note`, `a.full-chap-link`, `div.passage-other-trans`
  - 6개 샘플에서 모두 0개였다. WEB에는 편집자 소제목(`h3`)이 없다. 사이트 개편 대비로만 남긴다.

제거하지 않고 `get_text()`를 호출하면 아래 문제가 생긴다.

- `1 In the beginning, God[a] created...`처럼 장 번호와 각주 표시가 본문에 섞인다.
- Psalms 23:1이 `A Psalm by David. Yahweh is my shepherd; ...`가 된다.

### 6.4 유지해야 하는 인라인 마크업

아래는 태그를 제거하되 텍스트는 유지한다.

- `span.woj`
  - 신약 예수님의 말씀 강조. **본문이다.** Matthew 5에서 62개 관측.
- `span.indent-1`
  - 시가 들여쓰기 래퍼. 내부에 `span.text` 조각을 담고 있으므로 제거하면 본문이 통째로 날아간다.
- `span.small-caps`, `i`, `em`, `b`, `strong`, `a.bibleref`
  - 6개 샘플에서는 관측되지 않았다. 별도 처리 없이 텍스트만 남으면 된다.

예:

- `<span class="woj">“Blessed are the poor in spirit,</span>` -> `“Blessed are the poor in spirit,`

`span.indent-1-breaks`(들여쓰기용 공백 4칸)는 `span.text` **바깥**에 있으므로 조각 텍스트에 포함되지 않는다. 별도 제거가 필요 없다.

### 6.5 절 텍스트 정규화

절 조각 하나를 텍스트로 만들 때는 `get_text("")`를 사용한다.

- 구분자를 `" "`로 주면 인라인 태그 경계마다 공백이 삽입되어, `God<sup>[a]</sup>` 제거 후 `God ,` 같은 형태가 생길 수 있다.
- 원본 HTML에 이미 필요한 공백이 존재하므로 구분자 없이 추출한 뒤 정규화하는 편이 안전하다. bskorea 파서와 동일한 판단이다.

같은 절의 조각을 이어붙일 때는 **단일 공백**으로 연결한다. 조각은 별도 문단/행에서 왔으므로 공백이 필요하다.

최종 정규화:

- `&nbsp;`(U+00A0)를 일반 공백으로 치환한다.
- 연속 공백을 단일 공백으로 축약한다.
- 앞뒤 공백을 제거한다.
- 빈 문자열이면 버린다.

```python
text = text.replace(" ", " ")
text = re.sub(r"\s+", " ", text).strip()
```

`_normalize_text()`의 `\s+`는 유니코드 모드에서 U+00A0을 포함하므로 실질적으로는 `re.sub`만으로도 처리되지만, 의도를 명시하기 위해 치환을 함께 둔다.

### 6.6 실측 파싱 결과

위 설계대로 구현한 프로토타입을 실제 응답 6건에 돌린 결과다. 6건 모두 절 번호가 `1..N`으로 빠짐없이 연속했다.

| 샘플 | 절 수 | 검증 포인트 |
| --- | --- | --- |
| Genesis 1 | 31 | 각주 `[a]`, `[b]` 제거 / 각주 목록이 32절로 생성되지 않음 |
| Genesis 2 | 25 | `chapternum`이 `2`인데 절 번호는 `1` |
| Psalms 23 | 6 | 표제 제외, 4조각 분할 절 병합 |
| 1 Samuel 1 | 28 | 공백 포함 책명 URL, 23절 2조각 병합 |
| Matthew 5 | 48 | `woj` 보존, 상호 참조 `(A)` 제거, 팔복 2조각 병합 |
| Jude | 25 | 단일 장 책, `chapternum` 없음 |

주요 산출 텍스트:

```text
Gen 1:1   In the beginning, God created the heavens and the earth.
Gen 2:1   The heavens, the earth, and all their vast array were finished.
Ps 23:1   Yahweh is my shepherd; I shall lack nothing.
Ps 23:4   Even though I walk through the valley of the shadow of death, I will fear no evil,
          for you are with me. Your rod and your staff, they comfort me.
Matt 5:3  “Blessed are the poor in spirit, for theirs is the Kingdom of Heaven.
Jude 1:25 to God our Savior, who alone is wise, be glory and majesty, dominion and power,
          both now and forever. Amen.
```

`Ps 23:1`에 표제 `A Psalm by David.`가 없고, `Gen 1:1`에 `[a]`가 없으며, `Gen 2:1`이 1절로 저장된 것이 핵심 확인 사항이다.

### 6.7 예외 처리

다음 경우를 방어한다.

- `div.passage-text`가 없음
  - `[]` 반환 후 다음 파서로 위임
- 절 수가 0개
  - 파서 실패로 간주. 해당 장은 DB 쓰기 전에 건너뛰므로 빈 chapter row가 남지 않는다.
- 첫 절 번호가 1이 아님
  - 기존 적재 로직과 동일하게 경고 후 해당 장 skip
- 절 번호는 있으나 텍스트가 비어 있음
  - 해당 절 제외
- 같은 절 번호가 여러 `span`에 분할됨
  - 병합 (유실 금지)
- 요청 장과 다른 장의 절이 섞여 있음
  - 장 번호 필터로 제외
- 검색 결과 없음 페이지가 반환됨
  - 절 노드가 0개이므로 자연스럽게 실패 처리된다.
- 429 / 차단 페이지
  - 기존 `_looks_like_rate_limited_html()`과 `_sanitize_verses()`의 오류 문자열 필터가 처리한다.

## 7. 코드 통합 설계

### 7.1 `_extract_verses()` 체인 순서

현재 체인은 아래 순서다.

```text
bskorea -> bibletable -> chapter-prefixed -> ordered list -> structured nodes -> regex fallback
```

BibleGateway 파서는 **bskorea 다음, bibletable 앞**에 삽입한다.

```text
bskorea -> biblegateway -> bibletable -> ... -> regex fallback
```

이유:

- `_extract_verses_from_structured_nodes()`는 `span, p, li, div, td`를 훑으며 `^\d+ 텍스트` 패턴을 잡는다. BibleGateway 페이지에 이 파서가 먼저 도달하면 소제목, 각주, 드롭다운 텍스트를 절로 오인할 위험이 크다.
- 전용 파서가 먼저 성공하면 이후 폴백은 호출되지 않는다.
- 전용 파서는 컨테이너가 없을 때 `[]`를 반환하므로 다른 소스의 동작에 영향이 없다.

### 7.2 소스 판별

```python
def _is_biblegateway_source(self) -> bool:
    parsed = urlparse(self.entry_url)
    host = parsed.netloc.lower()
    return ("biblegateway.com" in host) or parsed.path.rstrip("/").endswith("/passage")
```

`get_source_name()`은 `"biblegateway"`를 반환하도록 확장한다.

`_build_chapter_url()`과 `discover_chapter_urls_for_book()`에도 동일한 분기를 추가한다. 판별 순서는 `thekingsbible -> bskorea -> biblegateway -> 템플릿 추론`으로 두면 기존 동작이 바뀌지 않는다.

### 7.3 엔트리 URL 해석

현재 `scrape_bible_to_db.py`의 `resolve_default_entry_url()`은 KJV/NKRV 2종만 다루며, `_is_nkrv_translation_hint()`는 `bool | None` 3값 반환이다. 소스가 3종이 되면 이 구조는 확장되지 않는다.

권장 리팩터링:

```python
ENTRY_URL_ENV_BY_TRANSLATION_TYPE = {
    "KJV": "KJV_ENTRY_URL",
    "NKRV": "NKRV_ENTRY_URL",
    "WEB": "WEB_ENTRY_URL",
}
```

해석 우선순위:

1. `--entry-url` 명시값
2. `BIBLE_TRANSLATION_TYPE`에 대응하는 환경변수
3. `BIBLE_TRANSLATION_ID` 힌트에 대응하는 환경변수
4. `BIBLE_LANGUAGE_CODE`
   - `ko` -> `NKRV_ENTRY_URL`
   - `en` -> `KJV_ENTRY_URL` 또는 `WEB_ENTRY_URL` 중 설정된 것
   - `en`인데 둘 다 설정되어 있으면 모호하므로 오류로 중단하고 `--entry-url` 명시를 요구한다.
5. 설정된 엔트리 URL이 하나뿐이면 그 값
6. 아무것도 없으면 내장 기본값 `DEFAULT_ENTRY_URL`

핵심 변경점은 `language_code='en'`이 더 이상 KJV를 단독으로 지시하지 못한다는 것이다. 기존 `_is_nkrv_translation_hint()`의 `language_code == "en" -> KJV` 규칙은 WEB 도입 시 오동작하므로 반드시 함께 수정해야 한다.

하위 호환:

- `WEB_ENTRY_URL`이 설정되지 않은 기존 환경에서는 해석 결과가 지금과 동일해야 한다.

### 7.4 소스/번역본 정합성 검증

`validate_source_translation_compatibility()`에 아래 규칙을 추가한다.

BibleGateway + `version=WEB`:

- `translation_type == 'WEB'`이면 통과
- `name == 'World English Bible'`이고 `language_code == 'en'`이면 경고 후 통과
- 그 외에는 `Source/translation mismatch` 오류

기존 소스 보호 규칙 추가:

- `thekingsbible` 소스에 `translation_type == 'WEB'`이면 오류
- `bskorea` 소스에 `translation_type == 'WEB'`이면 오류
- `biblegateway` 소스에 `translation_type in ('KJV', 'NKRV')`이면 오류

이 검증이 없으면 WEB 본문이 KJV 번역본의 `bible_book` 아래로 잘못 적재되며, 적재 후 원복 비용이 매우 크다. 그래서 실행 초기에 중단시키는 현재 정책을 그대로 따른다.

### 7.5 CLI

CLI 인자 자체는 변경하지 않는다. 소스는 `--entry-url`(또는 환경변수)로 결정되고, 번역본은 `BIBLE_*` 환경변수로 결정되는 현재 계약을 유지한다.

WEB 실행 예:

```bash
export BIBLE_TRANSLATION_TYPE=WEB
export BIBLE_TRANSLATION_NAME="World English Bible"
export BIBLE_LANGUAGE_CODE=en
export WEB_ENTRY_URL="https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB"
python3 scrape_bible_to_db.py --start-book 1 --end-book 1
```

smoke test(DB 미접속) 예:

```bash
export WEB_ENTRY_URL="https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB"
python3 scrape_bible_to_db.py --test-genesis1
python3 scrape_bible_to_db.py --test-book 40 --test-chapter 1
```

smoke test 경로는 `fetch_chapter_payload()`가 `book_code=None`으로 호출되므로, 책명은 `BIBLEGATEWAY_BOOK_NAMES` 상수에서 해석된다. 즉 DB 없이도 동작한다.

## 8. 테스트 설계

### 8.1 단위 테스트 우선

현재 저장소 스타일과 동일하게 inline HTML fixture 기반으로 작성한다. 부록의 Genesis 1 HTML을 축약해 fixture로 사용한다.

필수 테스트:

- URL 생성
  - `Genesis 1` -> `?search=Genesis%201&version=WEB`
  - `1 Samuel 1` -> `?search=1%20Samuel%201&version=WEB`
  - 엔트리 URL의 `version` 승계
- 장 목록 생성
  - 창세기 `1..50`, 마태복음 `1..28`, 유다서 `1..1`
- 소스 판별
  - `get_source_name()`이 `"biblegateway"`를 반환
- 정상 절 파싱
  - Genesis 1에서 `1..31` 절이 모두 추출되는지
- 절 번호 기준
  - `chapternum`이 아닌 클래스 토큰에서 절 번호를 읽는지
- 각주 제거
  - 본문에 `[a]`, `[b]`가 없는지
  - `Footnotes`, `The Hebrew word rendered` 문자열이 절로 생성되지 않는지
- 분할 절 병합
  - 같은 클래스의 `span` 2개가 하나의 절로 합쳐지는지
  - 조각 사이가 단일 공백으로 이어지는지
- 시편 표제 제외
  - `h4.psalm-title` 안의 `Ps-23-1` 조각이 1절 본문에 섞이지 않는지
- 병렬 역본 컨테이너
  - `passage-text`가 2개인 HTML에서 첫 번째만 사용하는지
- `span.woj` 보존
  - 예수님 말씀 텍스트가 유실되지 않는지
- 다른 장 혼입 제외
  - `Gen-2-1` 클래스가 섞여 있을 때 장 1 요청 결과에서 제외되는지
- 인라인 태그 평탄화
  - `span.woj`, `i` 텍스트가 유지되는지
- 번역본 식별
  - `WEB` / `World English Bible` / `en` 조건으로 translation id를 찾는지
- 정합성 검증
  - biblegateway + KJV 메타데이터 조합에서 오류가 발생하는지
- 엔트리 URL 해석
  - `WEB_ENTRY_URL`만 설정된 경우 그 값이 선택되는지
  - `KJV_ENTRY_URL`과 `WEB_ENTRY_URL`이 함께 있고 `language_code=en`만 주어지면 오류로 중단되는지
- idempotency
  - 이미 존재하는 chapter/verse가 있을 때 재실행해도 중복 insert가 없는지

### 8.2 추천 테스트 케이스 예시

#### 케이스 1. 기본 절 파싱

- 입력: Genesis 1 예시 HTML
- 기대:
  - 총 절 수 `31`
  - 1절 본문이 `In the beginning, God created the heavens and the earth.`
  - 31절 본문이 `...a sixth day.`로 끝남

#### 케이스 2. 장 번호 표시 제거

- 입력: `<span class="text Gen-2-1"><span class="chapternum">2&nbsp;</span>The heavens...</span>`
- 기대:
  - 절 번호 `1`
  - 본문이 `2`로 시작하지 않음

#### 케이스 3. 각주 제거

- 입력: 1절에 `sup.footnote`, 문서 하단에 `div.footnotes` 포함
- 기대:
  - 본문에 `[a]` 없음
  - 각주 텍스트가 별도 절로 생성되지 않음

#### 케이스 4. 분할 절 병합 + 시편 표제 제외

- 입력: Psalms 23 구조 — `h4.psalm-title > span.text.Ps-23-1`(`A Psalm by David.`)와 `div.poetry` 안의 `Ps-23-1` 조각 2개
- 기대:
  - 절 1개
  - 본문 `Yahweh is my shepherd; I shall lack nothing.`
  - 본문에 `A Psalm by David.` 없음

#### 케이스 5. 병렬 역본 컨테이너

- 입력: 서로 다른 본문을 담은 `div.passage-text` 2개
- 기대:
  - 첫 번째 컨테이너의 절만 수집됨

#### 케이스 6. 장 혼입 제외

- 입력: `Gen-1-31`과 `Gen-2-1`이 같은 컨테이너에 존재
- 기대:
  - 장 1 요청 결과에 `Gen-2-1` 본문이 포함되지 않음

#### 케이스 7. 인라인 강조 보존

- 입력: `<span class="woj">Follow me</span>`를 포함한 절
- 기대:
  - `Follow me`가 본문에 남음

#### 케이스 8. 폴백 파서 미개입

- 입력: BibleGateway HTML
- 기대:
  - `_extract_verses_from_structured_nodes()`가 호출되기 전에 전용 파서가 결과를 반환

#### 케이스 9. 비-BibleGateway HTML 무영향

- 입력: 기존 bskorea / thekingsbible fixture
- 기대:
  - BibleGateway 파서가 `[]`를 반환하고 기존 테스트가 모두 통과

#### 케이스 10. 정합성 검증

- 입력: biblegateway 엔트리 URL + `translation_type='KJV'`
- 기대:
  - `Source/translation mismatch` 오류로 실행 중단

### 8.3 통합 테스트

네트워크 의존 테스트는 기본 CI 대상에서 제외하고 선택 실행으로 둔다.

- 실제 Genesis 1 fetch smoke test
- 응답 상태 확인
- 절 수 `31` 확인

외부 사이트 변경과 차단 가능성이 있으므로 단위 테스트를 품질 기준으로 삼는다.

## 9. 네트워크와 요청 정책

### 9.1 robots.txt 실측

`https://www.biblegateway.com/robots.txt`를 확인한 결과는 아래와 같다.

```text
User-agent: *
Disallow: /cgi-bin/guestbook
Disallow: /feedback
Disallow: /user
Disallow: /bible/1*   ... /bible/Z*   (알파벳/숫자별 다수)
Crawl-delay: 15
```

두 가지가 확정된다.

1. **`/passage/`는 Disallow 목록에 없다.** 우리가 쓰려는 경로는 허용된다. (차단 대상은 `/bible/*` 경로다.)
2. **`Crawl-delay: 15`가 모든 봇에 적용된다.**

### 9.2 요청 간격 정책

`Crawl-delay: 15`는 권고가 아니라 사이트가 명시한 요청 간격이다. 이를 지키면 전권 적재 소요 시간이 결정된다.

- 1,189 요청 × 15초 ≈ **4시간 57분**
- 책 전환 대기(5초 × 65) 약 5분
- 합계 **약 5시간** (재시도 제외)

따라서 아래를 적용한다.

- BibleGateway 소스일 때 `sleep_min`을 **15초 미만으로 내릴 수 없게** 한다. 생성자에서 하한을 강제한다.

```python
BIBLEGATEWAY_CRAWL_DELAY_SECONDS = 15.0

if self._is_biblegateway_source():
    self.sleep_min = max(self.sleep_min, BIBLEGATEWAY_CRAWL_DELAY_SECONDS)
    self.sleep_max = max(self.sleep_max, BIBLEGATEWAY_CRAWL_DELAY_SECONDS + 3.0)
```

CLI 인자나 환경변수로 조절하는 방식은 채택하지 않는다. 사람이 잊거나 성급하게 낮출 수 있는 값이라면 준수 여부가 운에 달리게 된다. **코드에서 하한을 강제하는 편이 옳다.**

- 책 간 `BOOK_TRANSITION_DELAY_SECONDS`(5초)는 그대로 유지한다.
- 기존 429 처리, `Retry-After` 파싱, throttle 승수 로직을 그대로 사용한다.
- 실패 시 `--start-book`/`--end-book`으로 나눠 여러 세션에 분산 실행한다.
- 전체 실행 전 반드시 smoke test로 파서를 검증한다.

기존 KJV/NKRV 소스의 기본값(0.3 / 1.0)은 바뀌지 않는다. 하한은 BibleGateway에만 적용된다.

## 10. 리스크 및 대응

### 리스크 1. DOM 구조 변경

BibleGateway는 UI 개편이 잦다.

대응:

- 파싱 기준을 `span.text` + 클래스 토큰이라는 최소 계약으로 좁힌다. 이 계약은 앵커 링크 규약과 연동되어 있어 상대적으로 안정적이다.
- 컨테이너 선택 실패 시 `[]` 반환으로 폴백 체인을 유지한다.
- 절 수가 기대치와 크게 다르면 경고 로그를 남긴다.

### 리스크 2. 절 번호 오인

`chapternum`/`id` 사용은 조용한 데이터 오염을 만든다.

대응:

- 절 번호는 클래스 토큰에서만 추출한다.
- Genesis 2:1 케이스를 회귀 테스트로 고정한다.

### 리스크 3. 분할 절 유실

대응:

- 절 번호 그룹핑 후 병합.
- 시가서 fixture 테스트 추가.

### 리스크 4. 요청 차단

대응:

- 요청 간격 상향.
- 기존 retry/throttle 재사용.
- 장 수 생성형 접근으로 불필요 요청 최소화.
- 차단이 반복되면 [13절](#13-라이선스와-운영-리스크)의 대체 소스로 전환.

### 리스크 5. 잘못된 번역본으로 적재

대응:

- 실행 초기 소스/번역본 정합성 검증.
- 엔트리 URL 해석에서 `en` 모호성 발생 시 중단.

## 11. 전권 적재 운영 계획

이 절은 "창세기~요한계시록 전 구절 적재"라는 최종 목표를 실제로 달성하고 검증하기 위한 실행 계획이다.

### 11.1 작업 규모

- 총 요청 수: 1,189회 (장 단위 1요청, 재시도 제외)
  - 구약 929장, 신약 260장
- 예상 소요 시간: **약 5시간**
  - `robots.txt`의 `Crawl-delay: 15`를 준수한 값이다(9.2 참고). 이 시간은 단축 대상이 아니라 전제 조건이다.
  - 한 세션에 5시간을 붙잡아 두기보다 11.3의 구간 분할로 나눠 실행하는 편이 낫다.
- 적재 절 수: **31,098절** (실측)
  - KJV는 31,102절이다. 차이 4절은 11.4의 알려진 예외와 정확히 일치한다.
  - 그래도 **총 절 수만으로 완료를 판정하지 않는다.** 판정 기준은 11.4의 구조 검증 쿼리다.

### 11.2 사전 준비 체크리스트

전권 실행 전 아래를 모두 만족해야 한다.

1. `public.bible_translation`에 WEB row 존재 (`translation_type='WEB'`)
2. 해당 `translation_id` 기준 `bible_book` 66권 존재 (`book_order=1..66`)
3. `.env`에 DB 접속 정보와 `WEB_ENTRY_URL` 설정
4. 성능 인덱스 생성

```sql
CREATE INDEX IF NOT EXISTS idx_chapter_book_id ON bible_chapter(book_id);
CREATE INDEX IF NOT EXISTS idx_verse_chapter_id ON bible_verse(chapter_id);
```

5. 파서 검증 smoke test 통과 (최소 3개 장)

```bash
python3 scrape_bible_to_db.py --test-book 1 --test-chapter 1    # Genesis 1, 31절
python3 scrape_bible_to_db.py --test-book 19 --test-chapter 119 # Psalms 119, 176절 (최장 장)
python3 scrape_bible_to_db.py --test-book 65 --test-chapter 1   # Jude, 단일 장 책
```

6. 소스/번역본 정합성 검증 통과 (오적재 방지)

### 11.3 분할 실행 전략

66권을 한 번에 돌리지 않고 구간으로 나눠 실행한다. 실패 시 재시도 범위를 좁히고, 차단 위험을 분산하기 위해서다.

권장 구간:

| 구간 | 범위 | 책 | 장 수 | 예상 소요 |
| --- | --- | --- | --- | --- |
| 1 | `--start-book 1 --end-book 5` | 모세오경 | 187 | 약 47분 |
| 2 | `--start-book 6 --end-book 17` | 여호수아~에스더 | 249 | 약 63분 |
| 3 | `--start-book 18 --end-book 22` | 욥기~아가 | 243 | 약 61분 |
| 4 | `--start-book 23 --end-book 39` | 이사야~말라기 | 250 | 약 63분 |
| 5 | `--start-book 40 --end-book 44` | 복음서~사도행전 | 117 | 약 30분 |
| 6 | `--start-book 45 --end-book 66` | 로마서~요한계시록 | 143 | 약 36분 |

소요 시간은 장당 15초 기준이며 합계는 1,189장 / 약 5시간이다.

```bash
python3 scrape_bible_to_db.py --start-book 1 --end-book 5
```

각 구간이 끝나면 11.4의 검증 쿼리를 돌린 뒤 다음 구간으로 넘어간다.

### 11.4 완료 검증 쿼리

전권 적재 완료 판정은 로그가 아니라 DB 상태로 한다. `:tid`는 WEB의 `translation_id`다.

**검증 1. 66권이 모두 적재되었는가**

```sql
SELECT COUNT(*) AS book_count
FROM public.bible_book
WHERE translation_id = :tid
  AND EXISTS (
      SELECT 1 FROM public.bible_chapter c
      JOIN public.bible_verse v ON v.chapter_id = c.id
      WHERE c.book_id = bible_book.id
  );
-- 기대값: 66
```

**검증 2. 총 장 수가 1,189인가**

```sql
SELECT COUNT(*) AS chapter_count
FROM public.bible_chapter c
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid;
-- 기대값: 1189
```

**검증 3. 절이 하나도 없는 빈 장이 있는가**

```sql
SELECT b.book_order, b.name, c.chapter_number
FROM public.bible_chapter c
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid
  AND NOT EXISTS (SELECT 1 FROM public.bible_verse v WHERE v.chapter_id = c.id)
ORDER BY b.book_order, c.chapter_number;
-- 기대값: 0 rows
```

**검증 4. 절 번호가 1부터 연속인가 (누락 절 탐지)**

```sql
SELECT b.book_order, b.name, c.chapter_number,
       MIN(v.verse_number) AS first_verse,
       MAX(v.verse_number) AS last_verse,
       COUNT(*)            AS verse_count
FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b    ON b.id = c.book_id
WHERE b.translation_id = :tid
GROUP BY b.book_order, b.name, c.chapter_number
HAVING MIN(v.verse_number) <> 1
    OR COUNT(*) <> MAX(v.verse_number)
ORDER BY b.book_order, c.chapter_number;
-- 기대값: 아래 알려진 예외 4건 외 0 rows
```

이 쿼리가 전권 적재의 **핵심 완료 기준**이다. 절 번호가 1부터 시작하고 최대 절 번호와 절 개수가 같으면 구멍이 없다는 뜻이다.

#### 알려진 예외 4건 (결함 아님)

WEB에는 아래 네 구절의 **본문이 없다.** 따라서 이 쿼리는 항상 4 rows를 반환하며, 이는 정상이다.

| book_order | 책 | 장 | 누락 절 |
| --- | --- | --- | --- |
| 42 | Luke | 17 | 36 |
| 44 | Acts | 8 | 37 |
| 44 | Acts | 15 | 34 |
| 44 | Acts | 24 | 7 |

현대 역본에서 본문에서 빠지는 것으로 알려진 구절들이며, KJV(31,102절)와 WEB(31,098절)의 절 수 차이도 정확히 이 4절이다.

**중요: 이 절들은 BibleGateway HTML에 스팬 자체가 없는 것이 아니다.** 절 스팬은 존재하지만 내용이 각주 마커뿐이다.

```html
<span class="text Acts-8-37"><sup class="versenum">37 </sup><sup class="footnote">[a]</sup></span>
```

렌더링하면 `36 ...baptized?”  37 [a]  38 He commanded...`처럼 보인다.  
파서가 `sup.versenum`과 `sup.footnote`를 제거하면 빈 문자열이 되고, 6.7의 "번호만 있고 텍스트가 비어 있음 -> 해당 절 제외" 규칙에 따라 버려진다.

이 동작이 옳다고 판단한 근거:

- 저장할 본문이 없는 절에 빈 row를 만들 이유가 없다.
- 각주 내용을 본문으로 넣으면 "각주는 절 본문에 포함하지 않는다"(6.3)는 규칙과 충돌한다.
- 같은 DB의 KJV에는 이 4절이 본문으로 존재하므로, 역본 간 실제 텍스트 차이가 그대로 드러나는 편이 정확하다.

따라서 이 4건이 나왔다고 재적재하거나 파서를 고치면 안 된다.  
**5건 이상이 나오거나 위 표에 없는 장이 나오면** 그때는 실제 누락이므로 조사 대상이다.

**검증 5. 본문 오염 탐지**

```sql
SELECT b.book_order, c.chapter_number, v.verse_number, v.text
FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b    ON b.id = c.book_id
WHERE b.translation_id = :tid
  AND (
        v.text ~ '\[[a-z]\]'          -- 각주 표시 잔존
     OR v.text ~ '^\d+\s'             -- 절/장 번호 잔존
     OR v.text ILIKE '%Footnotes%'
     OR v.text ILIKE '%Cross references%'
     OR length(v.text) < 3
  )
ORDER BY b.book_order, c.chapter_number, v.verse_number;
-- 기대값: 0 rows (또는 검토 후 허용 가능한 극소수)
```

**검증 6. 경계 구절 육안 확인**

아래 구절은 파서 함정을 대표하므로 실제 값을 눈으로 확인한다.

- `Genesis 1:1` — 장 번호(`1 `)와 각주(`[a]`) 제거 확인
- `Genesis 2:1` — `chapternum`이 `2`인데 절 번호가 `1`로 저장됐는지 확인
- `Psalms 23:1` — 분할 `span` 병합 확인
- `Psalms 119:176` — 최장 장의 마지막 절 존재 확인
- `John 3:16` — 신약 정상 적재 확인
- `Jude 1:25` — 단일 장 책의 마지막 절 확인
- `Revelation 22:21` — 전권 마지막 절 확인

### 11.5 재개와 재실행

- `--resume`은 `bible_verse`가 하나라도 존재하는 최대 `book_order`의 **다음 책**부터 시작한다. 즉 중간에 끊긴 책은 완료된 것으로 오인된다.
- 따라서 구간 실행이 중간에 실패하면 `--resume`이 아니라 **해당 책 범위를 명시해 재실행**한다.

```bash
python3 scrape_bible_to_db.py --start-book 19 --end-book 19
```

- 재실행은 기존 chapter/verse를 재사용하고 누락분만 insert 하므로 안전하다(idempotent).
- 검증 4에서 구멍이 발견된 특정 장만 다시 채울 수도 있다. 단, 알려진 예외 4건은 재실행해도 채워지지 않는다(WEB에 본문이 없다).

```bash
python3 scrape_bible_to_db.py --start-book 19 --end-book 19 --start-chapter 119 --end-chapter 119
```

### 11.6 중단 기준

아래 상황에서는 실행을 계속하지 말고 중단한다.

- 연속 3개 이상의 장에서 `No verses parsed` 경고 발생 → DOM 변경 의심
- 429가 반복되어 throttle 승수가 상한(6.0)에 고정됨 → 차단 의심
- 검증 5에서 각주/번호 잔존이 대량 발견됨 → 파서 수정 후 해당 범위 재적재
- 검증 4가 **알려진 예외 4건 외에** 추가로 나옴 → 실제 누락이므로 조사 후 해당 장 재적재

부분 적재 상태로 방치하는 것보다, 원인을 고치고 해당 책 범위를 재실행하는 편이 항상 저렴하다.

## 12. 구현 순서 제안

1. `BIBLEGATEWAY_BOOK_NAMES` 상수 정의
2. `_is_biblegateway_source()`, `get_source_name()` 확장
3. `_build_biblegateway_url()`, `_discover_chapter_urls_for_biblegateway()` 구현
4. `_extract_verses_from_biblegateway_passage()` 구현 및 `_extract_verses()` 체인 삽입
5. inline HTML fixture 단위 테스트 추가 (케이스 1~9)
6. `resolve_book_code_for_source()` 확장
7. `resolve_default_entry_url()` / 엔트리 URL 해석 리팩터링
8. `validate_source_translation_compatibility()` 확장 및 테스트 (케이스 10)
9. smoke test 수행 (11.2의 3개 장)
10. 단일 책(예: 유다서) DB 적재 후 절 수/본문 검증
11. 11.3의 구간 분할로 66권 전권 적재
12. 11.4의 검증 쿼리 1~6 통과 확인 (검증 4는 알려진 예외 4건까지 허용)

## 13. 라이선스와 운영 리스크

WEB(World English Bible) 본문 자체는 퍼블릭 도메인이다. 따라서 본문 텍스트를 DB에 적재하는 것에는 저작권 제약이 없다.

다만 **BibleGateway는 자체 이용약관과 `robots.txt`를 가진 상업 사이트**이므로, 본문이 퍼블릭 도메인이라는 사실과 이 사이트에서 대량 수집해도 되는지는 별개 문제다.

`robots.txt` 실측 결과(9.1):

- `/passage/`는 **허용**된다. 차단 대상은 `/bible/*` 경로다.
- `Crawl-delay: 15`가 명시되어 있으며, 이 설계는 이를 코드에서 강제한다(9.2).

남은 확인 사항은 사이트 이용약관의 자동 수집 조항이다. 이는 문서로 대신할 수 없고 실행 주체가 판단해야 한다.

대체 소스 검토(권장):

- `ebible.org` 등에서 WEB 전문을 USFM/OSIS 파일로 배포한다.
- 파일 기반 수집은 요청 수가 사실상 0이고, DOM 변경 리스크와 차단 리스크가 없으며, 파싱 결과가 결정적이다.
- 즉 **정확성과 운영 안정성만 보면 파일 기반 임포트가 스크래핑보다 우월하다.**

이번 문서는 요청받은 BibleGateway 스크래핑 방식으로 전권 적재까지 완결되도록 설계했다. 다만 목적이 "WEB 66권 전 구절 확보" 자체라면, 1,189회 요청과 DOM 의존을 감수하는 대신 파일 기반 임포터를 별도 엔트리포인트로 두는 방안이 비용·안정성 면에서 더 낫다는 점은 명시해 둔다.

두 방식은 배타적이지 않다. 파일 기반으로 전권을 적재하고, BibleGateway 스크래퍼는 특정 장 검증·보정용으로 유지하는 조합도 가능하다.

## 14. 결론

BibleGateway WEB 페이지는 결정적인 쿼리 URL과, 절마다 `OSIS약어-장-절` 클래스를 부여하는 비교적 명확한 DOM을 가진다.  
따라서 이 저장소에 붙일 때 핵심은 아래 세 가지다.

- `book_order -> 영문 책명` 매핑 기반 URL 생성 (`%20` 인코딩 유지)
- `div.passage-text` 범위에서 `span.text`의 **클래스 토큰 기준** 절 번호 추출
- 같은 절 번호로 분할된 `span` 병합과 각주/번호 마크업 제거

여기에 엔트리 URL 해석과 소스/번역본 정합성 검증을 3소스 체계로 확장하면, 기존 DB 적재 구조와 retry 로직을 대부분 재사용하면서 WEB 영어 본문 수집을 안정적으로 추가할 수 있다.

---

## 부록 A. 스크래핑 URL 목록

### Genesis

- chapter 1: `https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB`
- chapter 2: `https://www.biblegateway.com/passage/?search=Genesis%202&version=WEB`
- chapter 3: `https://www.biblegateway.com/passage/?search=Genesis%203&version=WEB`
- ...
- chapter 10: `https://www.biblegateway.com/passage/?search=Genesis%2010&version=WEB`
- ...
- chapter 50: `https://www.biblegateway.com/passage/?search=Genesis%2050&version=WEB`

### Matthew

- chapter 1: `https://www.biblegateway.com/passage/?search=Matthew%201&version=WEB`
- chapter 2: `https://www.biblegateway.com/passage/?search=Matthew%202&version=WEB`
- chapter 3: `https://www.biblegateway.com/passage/?search=Matthew%203&version=WEB`
- ...
- chapter 10: `https://www.biblegateway.com/passage/?search=Matthew%2010&version=WEB`
- ...
- chapter 28: `https://www.biblegateway.com/passage/?search=Matthew%2028&version=WEB`

### 1 Samuel (공백 포함 책명)

- chapter 1: `https://www.biblegateway.com/passage/?search=1%20Samuel%201&version=WEB`
- chapter 31: `https://www.biblegateway.com/passage/?search=1%20Samuel%2031&version=WEB`

### Jude (단일 장 책)

- chapter 1: `https://www.biblegateway.com/passage/?search=Jude%201&version=WEB`

## 부록 B. Genesis 1 응답 HTML 발췌

파싱 설계 근거가 되는 구조만 남기고, 역본 선택 `select`의 option 목록(400줄 이상)과 SVG 아이콘 마크업은 생략했다.

```html
<div class="passage-table" data-osis="Gen.1.1-Gen.1.31">
  <div class="passage-cols mobile">
    <div class="prev-next">
      <div class="prev-chapter-empty"></div>
      <a class="next-chapter" href="/passage/?search=Genesis%202&amp;version=WEB" title="Genesis 2">…</a>
    </div>

    <div class="passage-col-tools">
      <div class="passage-tools w-sidebar no-sidebar">
        <a href="/passage/?search=Genesis%201&amp;version=WEB;NIV" class="parallel">…</a>
        <span class="share">…</span>
        <a rel="nofollow" href="/passage/?search=Genesis%201&amp;version=WEB&amp;interface=print" class="print">…</a>
        <span class="settings">…</span>
      </div>

      <div class="passage-col passage-col-mobile version-WEB" data-translation="WEB">
        <h1 class="passage-display">
          <div class="bcv …"><div class="dropdown-display"><div class="dropdown-display-text">Genesis 1</div>…</div></div>
          <div class="translation …"><div class="dropdown-display"><div class="dropdown-display-text">World English Bible</div>…</div></div>
          <div class="clearfix"></div>
        </h1>

        <!-- 생략: div.dropdowns 내부 역본 select / option 목록 -->

        <div class="passage-text">
          <div class="passage-content passage-class-0">
            <div class="version-WEB result-text-style-normal text-html">
              <p class="chapter-1">
                <span id="en-WEB-1" class="text Gen-1-1">
                  <span class="chapternum">1&nbsp;</span>In the beginning, God<sup data-fn="#fen-WEB-1a" class="footnote" data-link="[&lt;a href=&quot;#fen-WEB-1a&quot; title=&quot;See footnote a&quot;&gt;a&lt;/a&gt;]">[<a href="#fen-WEB-1a" title="See footnote a">a</a>]</sup> created the heavens and the earth.
                </span>
                <span id="en-WEB-2" class="text Gen-1-2">
                  <sup class="versenum">2&nbsp;</sup>The earth was formless and empty. Darkness was on the surface of the deep and God’s Spirit was hovering over the surface of the waters.
                </span>
              </p>

              <p>
                <span id="en-WEB-3" class="text Gen-1-3"><sup class="versenum">3&nbsp;</sup>God said, “Let there be light,” and there was light. </span>
                <span id="en-WEB-4" class="text Gen-1-4"><sup class="versenum">4&nbsp;</sup>God saw the light, and saw that it was good. God divided the light from the darkness. </span>
                <span id="en-WEB-5" class="text Gen-1-5"><sup class="versenum">5&nbsp;</sup>God called the light “day”, and the darkness he called “night”. There was evening and there was morning, the first day.</span>
              </p>

              <!-- 생략: 6절~28절 문단 (동일 구조 반복) -->

              <p>
                <span id="en-WEB-29" class="text Gen-1-29">
                  <sup class="versenum">29&nbsp;</sup>God said, “Behold,<sup data-fn="#fen-WEB-29b" class="footnote" data-link="[&lt;a href=&quot;#fen-WEB-29b&quot; title=&quot;See footnote b&quot;&gt;b&lt;/a&gt;]">[<a href="#fen-WEB-29b" title="See footnote b">b</a>]</sup> I have given you every herb yielding seed, which is on the surface of all the earth, and every tree, which bears fruit yielding seed. It will be your food.
                </span>
                <span id="en-WEB-30" class="text Gen-1-30"><sup class="versenum">30&nbsp;</sup>To every animal of the earth, and to every bird of the sky, and to everything that creeps on the earth, in which there is life, I have given every green herb for food;” and it was so.</span>
              </p>

              <p>
                <span id="en-WEB-31" class="text Gen-1-31"><sup class="versenum">31&nbsp;</sup>God saw everything that he had made, and, behold, it was very good. There was evening and there was morning, a sixth day.</span>
              </p>

              <div class="footnotes">
                <h4>Footnotes</h4>
                <ol>
                  <li id="fen-WEB-1a"><a href="#en-WEB-1" title="Go to Genesis 1:1">1:1</a> <span class="footnote-text">The Hebrew word rendered “God” is “אֱלֹהִ֑ים” (Elohim).</span></li>
                  <li id="fen-WEB-29b"><a href="#en-WEB-29" title="Go to Genesis 1:29">1:29</a> <span class="footnote-text">“Behold”, from “הִנֵּה”, means look at, take notice, observe, see, or gaze at. It is often used as an interjection.</span></li>
                </ol>
              </div>
              <!--end of footnotes-->
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="passage-scroller no-sidebar">
    <span class="prev-link empty"></span>
    <a class="next-link" href="/passage/?search=Genesis%202&amp;version=WEB" title="Genesis 2">…</a>
  </div>
</div>
```

이 발췌에서 파서가 실제로 의존하는 요소는 아래 5개뿐이다.

- `div.passage-text` (파싱 범위)
- `span.text` (절 노드)
- `class`의 `Gen-1-1` 토큰 (장/절 번호)
- `span.chapternum`, `sup.versenum` (제거 대상)
- `sup.footnote`, `div.footnotes` (제거 대상)

## 부록 C. 실측 검증 결과

이 문서의 DOM 관련 서술은 실제 응답 6건을 받아 확인한 것이다. 요청은 `Crawl-delay: 15`를 지켜 15초 간격으로 보냈고, 6건 모두 HTTP 200이었다.

### C.1 페이지별 요소 개수

| 요소 | Gen 1 | Gen 2 | Ps 23 | 1Sam 1 | Matt 5 | Jude |
| --- | --- | --- | --- | --- | --- | --- |
| `div.passage-table` | 1 | 1 | 1 | 1 | 1 | 1 |
| `div.passage-text` | 1 | 1 | 1 | 1 | 1 | 1 |
| `span.text` | 31 | 25 | 17 | 29 | 56 | 25 |
| 고유 절 토큰 | 31 | 25 | 6 | 28 | 48 | 25 |
| `span.chapternum` | 1 | 1 | 1 | 1 | 1 | **0** |
| `sup.versenum` | 30 | 24 | 5 | 27 | 47 | 25 |
| `sup.footnote` | 2 | 3 | 0 | 4 | 12 | 4 |
| `sup.crossreference` | 0 | 0 | 0 | 0 | 9 | 0 |
| `div.footnotes` | 1 | 1 | 0 | 1 | 1 | 1 |
| `div.crossrefs` | 0 | 0 | 0 | 0 | 1 | 0 |
| `h4.psalm-title` | 0 | 0 | 1 | 0 | 0 | 0 |
| `h3` | 0 | 0 | 0 | 0 | 0 | 0 |
| `span.woj` | 0 | 0 | 0 | 0 | 62 | 0 |
| `div.poetry` | 0 | 0 | 1 | 0 | 1 | 0 |
| 중첩 `span.text` | 0 | 0 | 0 | 0 | 0 | 0 |
| `div.footnotes` 내 `span.text` | 0 | 0 | - | 0 | 0 | 0 |

`data-osis` 값: `Gen.1.1-Gen.1.31`, `Gen.2.1-Gen.2.25`, `Ps.23.1-Ps.23.6`, `1Sam.1.1-1Sam.1.28`, `Matt.5.1-Matt.5.48`, `Jude.1.1-Jude.1.25`

### C.2 프로토타입 파서 결과

6건 모두 절 번호가 `1..N`으로 빠짐없이 연속했다.

| 샘플 | 추출 절 수 | 기대 절 수 | 결과 |
| --- | --- | --- | --- |
| Genesis 1 | 31 | 31 | 일치 |
| Genesis 2 | 25 | 25 | 일치 |
| Psalms 23 | 6 | 6 | 일치 |
| 1 Samuel 1 | 28 | 28 | 일치 |
| Matthew 5 | 48 | 48 | 일치 |
| Jude | 25 | 25 | 일치 |

### C.3 이 검증으로 정정된 초안 오류

| 초안 서술 | 실측 |
| --- | --- |
| 데스크톱/모바일 컬럼으로 본문이 2회 렌더될 수 있음 | `div.passage-text`는 1개. `passage-col`과 `passage-col-mobile`은 같은 div의 클래스 |
| 시편 표제는 `p.psalm-title` | `h4.psalm-title`이며, **내부 `span.text`가 1절 클래스를 가짐** |
| 상호 참조 표시는 `[A]` | `(A)` |
| 소제목 `h3` 제거 필요 | WEB에는 `h3` 소제목이 없음 (6건 모두 0) |
| 1절에는 `chapternum`이 있음 | 단일 장 책(Jude)에는 없음 |
| 요청 간격은 1~2.5초면 충분 | `robots.txt`가 `Crawl-delay: 15`를 명시. 전권 약 5시간 |
