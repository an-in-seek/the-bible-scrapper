# BibleGateway NIV(New International Version) 본문 스크래핑 개발 설계

## 1. 목적

`biblegateway.com`의 NIV 본문을 수집해 창세기 1장부터 요한계시록 22장까지 66권 전 구절을 적재하는 설계다.

- 예시 URL
  - `https://www.biblegateway.com/passage/?search=Genesis%201&version=NIV`
  - `https://www.biblegateway.com/passage/?search=Psalms%20119&version=NIV`
  - `https://www.biblegateway.com/passage/?search=3%20John%201&version=NIV`
- 판본: 페이지 하단 표기가 `Copyright ©1973, 1978, 1984, 2011 by Biblica, Inc.`이므로 **NIV 2011**이다. 같은 사이트의 `NIVUK`는 별개 판본이며 대상이 아니다.

NIV는 [WEB](world-english-bible-scraping-design.md)·[ASV](american-standard-version-scraping-design.md)와 **같은 소스, 같은 URL 규칙, 같은 파서**를 쓴다. 이 문서는 그 두 문서를 반복하지 않고 NIV에서 달라지는 점만 다룬다. 두 문서에서 그대로 유효한 항목은 아래와 같다.

- URL 생성 규칙과 66권 영문 책명 (`BIBLEGATEWAY_BOOK_NAMES`)
- 절 번호를 `span.text` 클래스 토큰에서 읽는 규칙
- 분할 절 병합, 각주·상호참조 제거, `h3` 소제목 제거
- `Crawl-delay: 15` 준수 (코드에서 하한으로 강제)
- 장 단위 커밋, missing-only insert, `bible_book` 비생성 계약

## 2. 권리 — 사용자 지시로 설계를 진행한다

**NIV는 퍼블릭 도메인이 아니다.** 이 저장소의 다른 역본과 달리 저작권이 살아 있고, WEB 설계 문서는 "저작권이 있는 역본(NIV, ESV 등)은 수집 대상으로 삼지 않는다"고 적어 두었다. 이 문서는 **"저작권이 있어도 일단 무시하고 설계하라"는 사용자 지시(2026-10-05)에 따라 기술 설계만** 진행한다. 아래 사실은 적재 여부를 판단할 때 다시 봐야 하므로 기록해 둔다.

| 항목 | 확인 내용 (2026-10-05) |
| --- | --- |
| 저작권자 | Biblica, Inc. (페이지 표기) |
| 무허가 인용 한도 | Biblica 일반 지침: 500절 이하이면서, 성경 한 권 전체가 아니고, 인용하는 저작물의 25%를 넘지 않을 때. 그 이상은 Biblica의 서면 허가가 필요하다. `biblica.com/permissions`는 403을 돌려줘서, 이 지침을 옮겨 적은 2차 출처들로 확인했다 |
| 이 설계의 적재량 | 66권, 약 31,103절. 위 한도의 약 62배이고 모든 책을 통째로 포함한다 |
| BibleGateway 이용약관 (2025-06-04 개정) | "Company Content" 조항이 콘텐츠의 복사·다운로드·보관(archive)·재배포를 금지한다 |
| `robots.txt` | `/passage/`는 허용, `/bible/*`는 차단, `Crawl-delay: 15`. WEB 때 실측과 같다 |

정리하면 다음과 같다.

- **설계와 파서 개선은 저작권과 무관하게 가치가 있다.** 5.2에서 보듯 NIV 조사 중에 이미 적재된 WEB·ASV의 오염이 발견됐다. 이 수정은 퍼블릭 도메인 역본에 그대로 적용된다.
- **NIV 전권 적재는 허가 범위를 넘는다.** 적재(10절 운영 계획)는 이 설계에서 별도 게이트로 둔다. 실행 여부는 이 표를 보고 사용자가 결정한다.
- 이 문서는 NIV 본문을 인용하지 않는다. DOM 예시는 구조만 보이고 본문 자리는 `(본문)`처럼 표시한다.

## 3. 결론 먼저

**NIV는 현재 파서로 돌리면 조용히 오염된다.** 실측 32개 장 중 5개 장, 33절이 틀렸다. 절 수·연속성·빈 절 검사는 모두 통과한다.

| 항목 | 상태 |
| --- | --- |
| URL 생성, 책명, crawl-delay | 수정 불필요 (`version`을 엔트리 URL에서 승계) |
| 생략 절 `(omitted)` 처리 | 수정 불필요 — WEB과 같은 DOM이다 (5.4) |
| `p.translation-note` 제거 | 수정 불필요 — 이미 제거 목록에 있다 (5.5) |
| **`h4` 제거** | **수정함 (2026-10-05)** — 시편 표제·시 119편 히브리 자모·아가 화자 표시가 본문에 섞인다 (5.1) |
| **small caps 대문자화** | **수정함 (2026-10-05)** — A안(대문자화)으로 결정 (5.3) |
| **기존 WEB·ASV 데이터** | **보정 필요** — 같은 원인의 오염이 이미 DB에 있다 (5.2, 8절) |
| 엔트리 URL 해석, 정합성 검증 표 | **수정함 (2026-10-05)** — NIV 한 행 추가 |
| DB | `bible_translation` 11번 행과 CHECK 값은 **이미 있다**. `bible_book` 66행만 필요 (7절) |

## 4. 실측 결과

2026-10-05, 이 저장소의 `HolyBibleScraper`로 32개 장을 수집했다. `Crawl-delay: 15`를 지켰다. 페이지는 구조 분석에만 쓰고 DB에 넣지 않았다.

수집한 장은 구조상 위험한 곳을 골랐다.

- 기본: 창 1, 2 / 욜 2 / 말 4 / 롬 14, 16 / 계 12 / 유다서 / 요삼
- 시편과 시: 시 3, 23, 51, 119 / 아 1
- KJV에 있으나 비평본문이 빼는 절이 있는 장: 마 17, 18, 23 / 막 7, 9, 11, 15 / 눅 17, 23 / 요 5 / 행 8, 15, 24, 28
- 괄호로 처리되는 본문: 막 16 / 요 7, 8 / 요일 5

### 4.1 요소 개수 (대표 8개 장)

| 요소 | 창 1 | 시 3 | 시 119 | 아 1 | 막 16 | 요 7 | 행 8 | 요삼 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `div.passage-text` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `span.text` | 34 | 20 | 376 | 58 | 22 | 60 | 50 | 16 |
| 고유 절 토큰 | 31 | 8 | 176 | 17 | 20 | 53 | 40 | **15** |
| `sup.footnote` | 1 | 2 | 4 | 3 | 1 | 3 | 3 | 1 |
| `sup.crossreference` | 89 | 16 | 318 | 28 | 21 | 65 | 45 | 22 |
| `h3` | 1 | 1 | 1 | 0 | 1 | 4 | 4 | 0 |
| `h4` | 2 | **3** | **24** | **11** | 2 | 2 | 2 | 2 |
| `span.small-caps` | 0 | 6 | 24 | 0 | 0 | 0 | 0 | 0 |
| `span.woj` | 0 | 0 | 0 | 0 | 0 | 19 | 0 | 0 |
| 중첩 `span.text` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

- `h4` 중 2개는 모든 장에 있는 `h4.resources-header`(`Footnotes`, `Cross references`)다. 각각 `div.footnotes`·`div.crossrefs` 안에 있어 컨테이너째 제거되므로 무해하다. 나머지가 5.1의 문제다.
- `data-osis` 속성은 없다. 파서는 이 속성에 의존하지 않는다.
- 상호참조가 WEB보다 훨씬 많다(32개 장 합계 1,671개). 제거 규칙은 그대로 동작했고, 파싱 결과에 `[a]`·`(A)` 형태의 표지가 남은 절은 0이다.

### 4.2 KJV 대조

같은 DB의 KJV(10) 절 수와 32개 장을 비교했다.

| 결과 | 장 |
| --- | --- |
| 절 수와 마지막 절 번호가 KJV와 같다 | 31개 장 |
| 다르다 | **요삼 1장: NIV 15절, KJV 14절** |

요삼은 KJV 14절을 NIV가 14·15절로 나눈다. 요한계시록 12장(17절), 로마서 14·16장(23·27절), 말라기 4장(6절), 요엘 2장(32절)은 KJV와 같다. 샘플 밖에서 다른 장이 더 있는지는 적재 후 9.2의 양방향 대조로 확정한다. 지금 예상하는 총 절 수는 **31,103절**(KJV 31,102 + 1)이다.

## 5. 함정

### 5.1 함정 1. `h4` 세 종류가 절 클래스를 달고 본문에 섞인다 (가장 큼)

NIV 페이지에는 절 클래스를 단 `h4`가 세 종류 있다. 현재 제거 목록에는 `h4.psalm-title`만 있어 셋 다 빠져나간다.

```html
<!-- 시편 표제: 클래스가 없다 -->
<h4><span class="text Ps-3-1">(표제)</span></h4>
<!-- 시 119편 히브리 자모 -->
<h4 class="psalm-acrostic"><span class="text Ps-119-1">(자모 + 이름)</span></h4>
<!-- 아가 화자 표시 -->
<h4 class="speaker"><span class="text Song-1-2">(화자)</span></h4>
```

스팬이 그 절의 클래스를 가지므로 파서는 이를 그 절의 첫 조각으로 합친다. 실측 결과는 아래와 같다.

| 장 | 오염된 절 | 형태 |
| --- | --- | --- |
| 시 3, 23, 51 | 각 1절 | 표제가 1절 앞에 붙는다 |
| 시 119 | 22절 (1, 9, 17, … 169) | 히브리 자모와 이름이 각 연 첫 절 앞에 붙는다 |
| 아 1 | 8절 (2, 4, 8, 9, 12, 15, 16, 17) | 화자 표시가 절 앞, **또는 절 중간**(1:4)에 끼어든다 |

절 중간에 끼어드는 경우가 특히 나쁘다. 1:4는 한 절 안에서 화자가 바뀌므로 `h4`가 두 조각 사이에 있고, "절이 표제로 시작하는가"를 보는 SQL 검사로는 찾을 수 없다.

**수정**: 컨테이너 제거 목록의 `h4.psalm-title`을 `h4`로 넓힌다.

- 32개 장 전부에서 `h4` 제거 전후의 절 번호 집합이 같다. 소실 0, 바뀐 절은 정확히 위 33절이다.
- 각주·상호참조 머리글 `h4`는 어차피 컨테이너와 함께 지워지므로 영향이 없다.
- 클래스를 하나씩 나열하는 방식(`h4.psalm-acrostic, h4.speaker, h4:not([class])`)은 채택하지 않는다. 다음에 새 클래스가 나오면 또 조용히 샌다. 본문을 `h4`에 담는 사례는 이번 NIV 32개 장과 WEB·ASV 재수집 2개 장에서 관측되지 않았다. 전권에 없다는 보장은 8절의 재파싱 대조가 준다.

### 5.2 함정 2. 같은 오염이 이미 WEB·ASV에 적재돼 있다

NIV를 조사하다가 발견했다. 원인이 5.1과 같은 `h4`라는 것은 WEB 아가 1장, ASV 시 119편을 다시 받아(2026-10-05) 확인했다.

| 역본 | 원인 요소 | DB 실측 (읽기 전용 조회) |
| --- | --- | --- |
| WEB (22) | `h4.speaker` — `Beloved`, `Lover`, `Friends` | 아가에서 이 단어로 **시작하는** 절 27개. 절 중간 후보로 1:4, 5:1, 6:13, 8:5 |
| ASV (23) | `h4.psalm-acrostic` — `א Aleph.` … `ת Tav.` | 시 119편 22절 (1, 9, … 169) |

다시 받은 페이지에서도 같다. WEB 아 1장은 `h4` 제거로 8절이 바뀌고(1:4 포함), ASV 시 119편은 22절이 바뀐다.

- 이 오염은 절 수·연속성·빈 절 검사를 모두 통과했다. 그래서 WEB·ASV 적재 검증에서 걸리지 않았다.
- `h4.psalm-title`만 제거하던 규칙이 만들어진 경위는 WEB 설계에 있다. 그때 관측된 `h4`가 표제 하나뿐이었다.
- 위 숫자는 **SQL 패턴으로 찾은 하한**이다. 다른 책에 다른 `h4`가 있는지는 알 수 없다. 정확한 범위는 8절의 재파싱 대조로 확정한다.
- WEB 시 119편과 ASV 아가에서는 SQL 패턴으로 오염이 보이지 않는다. 두 역본 모두 아 2:4, 3:10이 `He brought`, `He made`로 시작하지만 원래 본문이다. 같은 사이트라도 역본마다 조판이 다르다.

### 5.3 함정 3. small caps가 소문자로 저장된다 — A안으로 결정

NIV는 신명(YHWH)을 `LORD`로 조판한다. HTML은 대문자를 쓰지 않고 CSS로 보이게 한다.

```html
<span class="small-caps" style="font-variant: small-caps">Lord</span>
```

`get_text()`는 CSS를 모르므로 저장값은 `Lord`가 된다. 실측 결과는 아래와 같다.

- 본문 `Lord` 64곳 (창 2, 시 3·23·119, 욜 2, 말 4)
- **십자가 명패 2곳이 전부 소문자로 저장된다**: 막 15:26, 눅 23:38. 화면에는 대문자로 보이는 문구다.

| 선택지 | 결과 |
| --- | --- |
| **A. small caps 안의 글자를 대문자로 바꾼다 (권장)** | `LORD`, 명패 대문자. 인쇄본과 같고, 같은 DB의 KJV도 `LORD`로 적재돼 있다(5,552절). YHWH(`LORD`)와 Adonai(`Lord`)의 구분이 남는다 |
| B. 원문 HTML 그대로 둔다 | 구현 없음. 신명과 일반 `Lord`가 구분되지 않고, 명패가 소문자로 남는다 |

- A는 공용 BibleGateway 파서에 들어간다. WEB은 신명을 `Yahweh`, ASV는 `Jehovah`로 옮기므로 영향이 작을 것으로 본다. DB에서 `LORD`가 든 절은 WEB 1개, ASV 0개다. 이번 WEB·ASV 샘플(아 1, 시 119)의 `span.small-caps`도 0개였다. 그래도 전권에 없다고 단정할 수는 없으므로 8절의 재파싱 대조에서 함께 확인한다.
- A를 구현할 때는 스팬 안의 텍스트 노드만 바꾼다. 스팬 안에 각주 `sup`이 있어도 그 텍스트는 이미 지워진 뒤여야 한다(인라인 제거 다음에 대문자화한다).

### 5.4 생략 절 — WEB과 같은 DOM이라 `(omitted)`가 그대로 동작한다

NIV는 KJV에 있는 16절을 본문에서 빼고 각주로 돌린다. ASV는 스팬 자체가 없었지만, **NIV는 WEB처럼 각주 표지만 든 스팬을 남긴다.** 현재 파서는 별도 수정 없이 `(omitted)`를 기록한다.

```html
<span class="text Matt-17-21"><sup class="versenum">21 </sup><sup class="footnote">[a]</sup></span>
```

샘플에서 `(omitted)`로 기록된 절은 16개다.

> 마 17:21, 18:11, 23:14 / 막 7:16, 9:44, 9:46, 11:26, 15:28 / 눅 17:36, 23:17 / 요 5:4 / 행 8:37, 15:34, 24:7, 28:29 / 롬 16:24

이 목록은 일부러 고른 후보 장을 수집해서 나온 것이므로, 샘플 밖에 다른 생략 절이 없다는 보장은 아니다. 적재 후 `(omitted)` 건수를 세어 이 16개와 일치하는지 확인한다(9.1).

### 5.5 괄호 본문의 편집자 주 — 이미 제거된다

막 16:9–20과 요 7:53–8:11 앞에는 "가장 오래된 사본에는 없다"는 편집자 주가 있다. 이 주는 **다음 절의 클래스를 단 스팬**으로 들어 있다.

```html
<p class="translation-note center top-1"><span class="text Mark-16-9">(편집자 주)</span></p>
<p class="top-1"><span class="text Mark-16-9"><i><sup class="versenum">9 </sup>(본문)</i> …</span></p>
```

`p.translation-note`가 이미 컨테이너 제거 목록에 있어서 주는 버려지고 본문만 남는다(실측: 막 16:9, 요 7:53). **이 항목을 "쓰이지 않는 코드"로 지우면 두 곳에서 편집자 주가 절 앞에 붙는다.** 본문을 감싼 `<i>`는 표지 없이 글자만 남는다.

### 5.6 그 밖의 확인 사항

- `h3` 소제목은 ASV처럼 절 클래스를 달고 있다. 32개 장 합계 75개이며 모두 제거된다.
- 요 8:1은 `span.chapternum.mid-paragraph`로 장 번호를 문단 중간에 찍는다. `span.chapternum` 제거 규칙에 그대로 걸린다.
- `’ ”`(겹따옴표 사이 공백, 요 5:11 등)는 원문 조판이다. 손대지 않는다.
- 비 ASCII 문자는 따옴표류(`“ ” ‘ ’`), `—`, `…`뿐이다. 유니코드 정규화는 필요 없다.

## 6. 코드 변경 지점

### 6.1 `scraper.py`

```python
# h4 전체: psalm-title(WEB/ASV 표제), 클래스 없는 h4(NIV 표제),
# h4.psalm-acrostic(ASV·NIV 시 119편), h4.speaker(WEB·NIV 아가)
BIBLEGATEWAY_CONTAINER_REMOVABLE_SELECTOR = (
    "div.footnotes, div.crossrefs, h4, p.psalm-title, h3, "
    "p.translation-note, a.full-chap-link, div.passage-other-trans"
)
```

- 주석에는 세 종류와 "WEB·ASV에서 실제로 오염이 있었다"는 사실을 남긴다. 다음 사람이 이 규칙을 좁히지 못하게 하기 위해서다.
- 5.3 A안: `_extract_verses_from_biblegateway_passage()`에서 인라인 제거 다음, `get_text("")` 앞에 `span.small-caps` 안의 텍스트 노드를 `upper()`로 바꾼다.
- URL 생성, 책명, crawl-delay, `(omitted)` 규칙은 바꾸지 않는다. NIV 전용 분기는 만들지 않는다. 세 역본의 DOM 계약이 같기 때문이다.

### 6.2 `scrape_bible_to_db.py`

```python
ENTRY_URL_ENV_BY_TRANSLATION_TYPE["NIV"] = "NIV_ENTRY_URL"
TRANSLATION_TYPES_BY_LANGUAGE_CODE["en"] = ("KJV", "WEB", "ASV", "NIV")
ENTRY_URL_PREFERENCE_ORDER = (..., "LSG1910", "NIV")
TRANSLATION_SOURCE_REQUIREMENTS["NIV"] = {
    "source": "biblegateway",
    "version": "NIV",
    "name": "New International Version",   # DB 11번 행의 name과 같다
    "language_code": "en",
}
```

이 행이 없을 때의 동작은 현재 코드로 확인했다.

- `version=NIV`는 기대 역본이 없다(`_expected_translation_type()`가 `None`).
- 따라서 `translation_type`이 표에 없는 값이면 **검증 없이 통과한다.** DB에는 표에 없는 영어 역본 행이 14개(NIV, ESV, NASB, NLT … YLT) 있다.
- 지금 그 행들은 `bible_book`이 0권이라 실제로 적재되지는 않는다. 하지만 NIV용 66권을 만드는 순간 이 방어는 사라진다. 이 행은 7절보다 먼저 들어가야 한다.

행을 넣으면 `version=NIVUK`는 `_version_matches()`가 정확히 비교하므로(대소문자만 무시) NIV 메타데이터와 함께 쓰면 거부된다.

## 7. DB 준비

현재 상태(2026-10-05 실측, 읽기 전용 조회):

| 항목 | 상태 |
| --- | --- |
| `bible_translation` | **id 11, `NIV`, `New International Version`, `en` 행이 이미 있다**. `attribution`은 NULL |
| `translation_type` CHECK | `NIV` **이미 포함** |
| `language_code` CHECK | `en` 포함 |
| `bible_book` | **0권** |

DDL은 필요 없다. LSG1910 때와 달리 CHECK 변경이 없으므로 `ALTER TABLE` 잠금 문제도 없다.

`bible_book` 66행은 ASV 때와 같은 방식으로 KJV(10) 행을 복사한다.

```sql
SELECT setval('public.bible_book_id_seq', (SELECT COALESCE(MAX(id), 0) FROM public.bible_book), true);

INSERT INTO public.bible_book
    (translation_id, book_order, book_key, name, abbreviation, testament_type)
SELECT 11, src.book_order, src.book_key, src.name, src.abbreviation, src.testament_type
FROM public.bible_book src
WHERE src.translation_id = 10
  AND NOT EXISTS (
      SELECT 1 FROM public.bible_book dst
      WHERE dst.translation_id = 11 AND dst.book_order = src.book_order
  )
ORDER BY src.book_order;
```

- 이 SQL은 도구 밖에서 실행한다. 도구는 `bible_book`을 만들지 않는다.
- `attribution`을 채운다면 Biblica가 요구하는 표기 문구가 들어가야 한다. 다른 역본의 `— Public domain` 형식을 쓰면 안 된다.

## 8. 기존 WEB·ASV 보정

6.1의 파서 수정은 WEB·ASV의 이미 적재된 행을 바꾸지 않는다(missing-only). 순서는 아래와 같다.

1. **파서 수정과 테스트** (6.1, 11절)
2. **범위 확정 — 읽기 전용.** 수정된 파서로 `scripts/check_translation_drift.py`를 WEB(22)·ASV(23) 전권에 돌린다.
   - 각 1,189장, `Crawl-delay: 15`로 역본당 약 5시간이다.
   - **두 역본을 동시에 돌리지 않는다.** BibleGateway 요청 간격이 절반이 된다.
   - 5.2의 SQL 하한(WEB 27 + 절 중간 후보 4, ASV 22)은 이 단계의 결과와 비교하는 기준이다. 결과가 하한보다 작으면 무언가 틀렸다.
   - small caps(5.3 A안)로 바뀌는 절이 있는지도 이 결과에 함께 나온다.
3. **차이 목록 검토.** 바뀌는 절이 전부 `h4` 또는 small caps 때문인지 확인한다. 다른 이유로 바뀐 절이 있으면 멈춘다.
4. **보정 — DB 쓰기, 사용자 승인 후.** 확정된 절만 `bible_verse`에서 지우고, 해당 책 범위로 적재기를 다시 돌려 누락분을 채운다.
   - 장 행은 그대로 두므로 "절 먼저, 장 나중" 규칙과 충돌하지 않는다.
   - 적재기는 한 번에 하나만 돌린다(`sync_identity_sequences()`).
5. **다시 대조해서 차이 0을 확인한다.**

전권 대조가 부담되면 2단계를 시편·아가·애가로 줄일 수 있다. 다만 그러면 다른 책의 `h4`는 확인하지 못한 채로 남는다. 그 사실을 기록해 둔다.

## 9. 검증

### 9.1 기본 검증 (전 소스 공통)

| 검증 | 기대값 |
| --- | --- |
| 절이 적재된 책 | 66 |
| 장 | 1,189 |
| 절 | 31,103 (예상. 9.2로 확정) |
| 빈 절 / 첫 절이 1이 아닌 장 | 0 |
| 절 번호 구멍 | 0 (생략 절은 `(omitted)`로 채워진다) |
| `(omitted)` | 16 — 5.4 목록과 정확히 같은 좌표 |

### 9.2 KJV 대조 — 양방향

ASV 설계 8.2의 쿼리를 `translation_id` 10 ↔ 11로 양방향 실행한다.

- 기대값: NIV에만 있는 좌표는 **요삼 1:15 하나**, KJV에만 있는 좌표는 0
- 이와 다르면 그 장을 원문에서 확인하고 문서에 기록한다. 절 구분 차이인지 파싱 실패인지를 사람이 판정한다.

### 9.3 오염 검증 — 이 소스 필수

```sql
-- h4 잔존: 히브리 자모, 아가 화자 표시 (전권)
SELECT c.chapter_number, v.verse_number
FROM bible_verse v JOIN bible_chapter c ON c.id = v.chapter_id JOIN bible_book b ON b.id = c.book_id
WHERE b.translation_id = 11
  AND (v.text ~ '[א-ת]'
       OR (b.book_order = 22 AND v.text ~ '(^|[.!?,;”’] )(She|He|Friends)\s+[A-Z]'));
-- 각주·상호참조 표지
... AND v.text ~ '\[[a-z]{1,2}\]|\([A-Z]{1,2}\)';
-- small caps (A안일 때): 소문자 명패가 남지 않았는지
... AND v.text ILIKE '%king of the jews%' AND v.text NOT LIKE '%KING OF THE JEWS%';
```

- 첫 쿼리의 아가 조건은 오탐이 섞인다. `He`로 시작하는 원래 본문(ASV 아 2:4처럼)이 있을 수 있다. 결과는 원문과 대조해서 판정한다.
- 이 SQL은 하한일 뿐이다. 오염 검증의 기준은 9.4다.

### 9.4 재파싱 대조

적재 직후 `check_translation_drift.py --translation-id 11`을 표본 책(시편, 아가, 마가복음)에 돌려 차이 0을 확인한다. 파서와 적재 경로가 같은 결과를 내는지 보는 검사다.

### 9.5 경계 구절 육안 확인

- 시 3:1, 51:1 — 표제가 없어야 한다
- 시 119:1, 119:169 — 히브리 자모가 없어야 한다
- 아 1:4 — 절 중간에 화자 표시가 없어야 한다
- 막 16:9, 요 7:53 — 편집자 주가 없어야 한다
- 막 15:26 — 명패 (A안이면 대문자)
- 요삼 1:14, 1:15 — 둘 다 있어야 한다

## 10. 운영 계획 — 적재는 별도 게이트

**2절의 권리 문제 때문에 NIV 전권 적재는 사용자가 따로 결정한다.** 결정 전에 할 수 있는 일은 파서 수정, 테스트, WEB·ASV 보정, smoke test(DB 미접속)다.

- 66권 / 1,189장 / 요청 1,189회
- `Crawl-delay: 15` 하한과 응답 시간을 더해 **5시간 이상**
- 장 단위 커밋이므로 끊겨도 완료된 장은 남는다. 재개는 `--start-book`으로 한다
- `.env`에 다른 영어 `*_ENTRY_URL`이 있으면 `BIBLE_LANGUAGE_CODE=en`만으로는 엔트리가 결정되지 않는다. `--entry-url`과 `BIBLE_TRANSLATION_TYPE=NIV`를 함께 준다

smoke test(DB 미접속):

```bash
python3 scrape_bible_to_db.py --entry-url "https://www.biblegateway.com/passage/?search=Genesis%201&version=NIV" --test-book 19 --test-chapter 119
python3 scrape_bible_to_db.py --entry-url "https://www.biblegateway.com/passage/?search=Genesis%201&version=NIV" --test-book 22 --test-chapter 1
```

적재 실행 예(게이트 통과 후):

```bash
export BIBLE_TRANSLATION_ID=11
export BIBLE_TRANSLATION_TYPE=NIV
export NIV_ENTRY_URL="https://www.biblegateway.com/passage/?search=Genesis%201&version=NIV"
python3 scrape_bible_to_db.py --entry-url "$NIV_ENTRY_URL" --start-book 1 --end-book 1
```

## 11. 테스트 설계

인라인 HTML 픽스처만 쓴다. 네트워크는 쓰지 않는다. 픽스처의 본문은 NIV 문장이 아니라 임의의 문장으로 쓴다.

파서:

- 클래스 없는 `h4` 시편 표제가 1절에 섞이지 않는다
- `h4.psalm-acrostic`이 연 첫 절에 섞이지 않는다
- `h4.speaker`가 **절 중간에** 있을 때 두 조각만 합쳐지고 화자 표시는 빠진다 (아 1:4 형태)
- `h4`를 지워도 그 절의 본문 스팬은 남는다 (표제 스팬과 본문 스팬이 같은 클래스를 가질 때)
- `p.translation-note`의 같은 클래스 스팬이 절 앞에 붙지 않는다 (막 16:9 형태)
- (A안) `span.small-caps`의 `Lord`가 `LORD`로, 소문자 명패가 대문자로 저장된다. small caps 밖의 `Lord`는 그대로다
- 기존 `h4.psalm-title`, `h3`, `(omitted)` 테스트는 그대로 통과해야 한다

파이프라인:

- `version=NIV` + NIV 메타데이터 통과
- `version=NIV` + WEB/ASV 메타데이터 거부, `version=WEB` + NIV 메타데이터 거부
- `version=NIVUK` + NIV 메타데이터 거부
- `NIV_ENTRY_URL`만 있으면 선택되고, 다른 영어 URL과 함께 `en`만 주면 중단된다

## 12. 구현 순서

1. `TRANSLATION_SOURCE_REQUIREMENTS`와 엔트리 URL 해석에 NIV 추가, 테스트 (6.2)
2. `h4` 제거와 small caps 처리, 테스트 (6.1)
3. WEB·ASV 재파싱 대조 → 목록 검토 → 사용자 승인 후 보정 → 재대조 (8절)
4. README·CLAUDE.md 갱신 (지원 소스 표, `h4` 규칙, small caps 규칙, NIV의 권리 상태)
5. **게이트: NIV 적재 여부 결정 (2절)**
6. 통과 시 `bible_book` 66행 (7절) → smoke test → 1권 적재·검증 → 전권 → 9절 검증

1–4는 NIV 적재와 무관하게 진행할 수 있다. 특히 3은 이미 DB에 있는 오염을 고치는 일이다.

## 13. 리스크

### 리스크 1. `h4`를 다시 좁힌다

`h4.psalm-title` 하나만 보던 시절의 판단이 WEB·ASV 오염을 만들었다. 대응: 6.1의 주석과 11절의 세 테스트를 남긴다.

### 리스크 2. 오염 범위를 SQL로만 판단한다

5.2의 숫자는 패턴으로 찾은 하한이다. 절 중간에 끼어든 화자 표시는 패턴으로 찾기 어렵다. 대응: 8절 2단계를 재파싱 대조로 한다.

### 리스크 3. NIV 본문이 다른 영어 역본 행으로 들어간다

6.2의 행 없이 `bible_book`을 만들면 검증이 비어 있다. 대응: 구현 순서 1을 7절보다 먼저 끝낸다.

### 리스크 4. 권리 상태를 잊는다

DB의 다른 역본은 모두 퍼블릭 도메인이다. NIV 행이 섞이면 "이 DB는 자유롭게 배포할 수 있다"는 전제가 깨진다. 대응: README·CLAUDE.md에 NIV의 권리 상태를 적고, `attribution`을 비워 두지 않는다.

### 리스크 5. 요청 차단

리스크와 대응은 WEB·ASV와 같다. crawl-delay 하한은 코드가 강제한다. 429가 반복되면 중단한다.

## 14. 결론

- 기술적으로 NIV는 WEB·ASV와 같은 어댑터로 수집할 수 있다. 생략 절, 편집자 주, 소제목은 현재 규칙이 이미 처리한다.
- 다만 현재 파서로는 `h4` 세 종류가 시편·아가 33절(샘플 기준)을 조용히 오염시킨다. small caps도 소문자로 저장된다. 둘 다 파서 수정이 필요하다.
- 같은 `h4` 오염이 **이미 적재된 WEB 아가와 ASV 시 119편에 있다**. NIV 적재 여부와 관계없이 고쳐야 하는 문제다.
- NIV 전권 적재는 Biblica의 무허가 인용 한도와 BibleGateway 이용약관을 넘는다. 이 설계는 적재를 별도 게이트로 둔다.
