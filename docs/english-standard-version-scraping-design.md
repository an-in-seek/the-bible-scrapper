# BibleGateway ESV(English Standard Version) 본문 스크래핑 개발 설계

## 1. 목적

`biblegateway.com`의 ESV 본문을 수집해 창세기 1장부터 요한계시록 22장까지 66권 전 구절을 적재하는 설계다.

- 예시 URL
  - `https://www.biblegateway.com/passage/?search=Genesis%201&version=ESV`
  - `https://www.biblegateway.com/passage/?search=Psalms%20119&version=ESV`
  - `https://www.biblegateway.com/passage/?search=3%20John%201&version=ESV`
- 판본: 페이지 하단 표기가 `© 2001 by Crossway … ESV Text Edition: 2025.`이므로 **ESV 2025 텍스트판**이다. 같은 사이트의 `ESVUK`(영국식 철자판)는 별개 판본이며 대상이 아니다.

ESV는 [WEB](world-english-bible-scraping-design.md)·[ASV](american-standard-version-scraping-design.md)·[NIV](new-international-version-scraping-design.md)와 **같은 소스, 같은 URL 규칙, 같은 파서**를 쓴다. 이 문서는 세 문서를 반복하지 않고 ESV에서 달라지는 점만 다룬다. 그대로 유효한 항목은 아래와 같다.

- URL 생성 규칙과 66권 영문 책명 (`BIBLEGATEWAY_BOOK_NAMES`)
- 절 번호를 `span.text` 클래스 토큰에서 읽는 규칙, 분할 절 병합
- 각주·상호참조 제거, `h3` 소제목 제거, **`h4` 전체 제거**, `span.small-caps` 대문자화 (NIV 때 넣은 규칙)
- `Crawl-delay: 15` 준수 (코드에서 하한으로 강제)
- 장 단위 커밋, missing-only insert, `bible_book` 비생성 계약

## 2. 권리 — 사용자 지시로 진행한다

**ESV는 퍼블릭 도메인이 아니다.** 저작권자는 Crossway이고, NIV와 같은 처지다. 이 문서는 "영어 성경 ESV 번역본 스크래핑 작업 진행해"라는 사용자 지시(2026-10-26)에 따라 설계·배선·표본 실측까지 진행한다. NIV 때 "저작권이 있어도 일단 무시하고 설계하라"는 지시와 같은 선상이다. 아래 사실은 적재 여부를 판단할 때 다시 봐야 하므로 기록해 둔다. Crossway와 ESV API 항목은 2026-10-26에 원문 페이지를 읽어 확인했다. BibleGateway 항목은 NIV 때(2026-10-05) 확인한 내용이고, 이번에 다시 읽지는 않았다.

| 항목 | 확인 내용 (2026-10-26) |
| --- | --- |
| 저작권자 | Crossway (Good News Publishers의 출판 사역). 페이지 하단 표기와 같다 |
| 무허가 인용 한도 (`crossway.org/permissions/`) | 인쇄·디지털·오디오 모두 **500절 이하**. 단, 인용 절이 **어느 한 권의 절반을 넘지 않고**, 인용하는 저작물 전체의 **25% 이상이 되지 않으며**, 주석서나 성경 참고서에 쓰는 인용이 아닐 때. 그 이상은 서면 허가나 정식 라이선스가 필요하다 |
| 요구 표기 | `Scripture quotations are from the ESV® Bible (The Holy Bible, English Standard Version®), © 2001 by Crossway, a publishing ministry of Good News Publishers. ESV Text Edition: 2025. … Used by permission. All rights reserved.` 상표 `ESV`·`English Standard Version`의 사용도 Crossway 허가 대상이다 |
| Crossway 이용약관 (`crossway.org/terms/`) | 사이트에서 **500절 연속 또는 한 권의 절반을 넘게 복사·다운로드할 수 없다**. 적용 범위는 crossway.org, esv.org와 그 앱이다 |
| 공식 API (`api.esv.org`) | 비상업 용도 무료, **API 키(계정) 필요**. 저장 한도나 호출 한도는 문서에 공개돼 있지 않고, 한도를 넘는 질의는 응답이 잘린다고만 적혀 있다(2019-08-26 변경 이력) |
| 이 설계의 적재량 | 66권, 약 31,087절(4.2). 무허가 한도의 약 62배이고 모든 책을 통째로 포함한다 |
| BibleGateway 이용약관 (2026-10-05 확인) | NIV 때와 같다. "Company Content" 조항이 콘텐츠의 복사·다운로드·보관(archive)·재배포를 금지한다 |
| `robots.txt` (2026-10-05 확인) | `/passage/`는 허용, `Crawl-delay: 15` |
| 본문 개정 | ESV는 텍스트판이 계속 나온다. API 변경 이력(2025-02-20)에 따르면 이때 **36개 본문, 42절, 단어 68개**가 바뀌었다. 적재본은 적재 시점의 판으로 고정된다 |

정리하면 다음과 같다.

- **배선과 표본 실측은 적재 없이 할 수 있다.** ESV 배선은 정합성 검증 표 한 행과 엔트리 URL 해석이고, 표본은 구조 분석에만 쓰고 DB에 넣지 않았다.
- **ESV 전권 적재는 허가 범위를 넘는다.** NIV와 같이 적재(10절)는 별도 게이트로 둔다. 실행 여부는 이 표를 보고 사용자가 결정한다.
- 정식 경로는 Crossway 라이선스나 공식 API다. API도 키 발급(계정 생성)이 필요하고 Crossway 한도를 따르므로, 전권을 DB에 보관하는 용도로는 이 표의 제약이 그대로 남는다.
- `attribution`을 채울 때 "Used by permission"은 넣지 않는다. 허가를 받지 않았다(NIV와 같은 처리).
- 이 문서는 ESV 본문을 인용하지 않는다. DOM 예시는 구조만 보이고 본문 자리는 `(본문)`처럼 표시한다.

## 3. 결론 먼저

**파서는 한 줄도 바꿀 필요가 없다.** NIV 때 넣은 `h4` 전체 제거와 small caps 대문자화가 ESV의 구조를 그대로 처리한다. 표본 35개 장, 1,214절에서 오염 0, 공백 이상 0이다.

| 항목 | 상태 |
| --- | --- |
| URL 생성, 책명, crawl-delay | 수정 불필요 (`version`을 엔트리 URL에서 승계) |
| 파서 (`h3`·`h4` 제거, small caps, 분할 절 병합) | 수정 불필요 (5.2, 5.3) |
| 생략 절 | **ASV 방식** — 스팬이 없어 `(omitted)` 대신 절 번호 구멍 16개가 생긴다 (5.1) |
| 괄호 본문 `[[ ]]` | ESV의 원문 문자다. 그대로 저장한다 (5.4) |
| 엔트리 URL 해석, 정합성 검증 표 | **수정함 (2026-10-26)** — ESV 한 행 추가 (6.1) |
| 전권 적재용 요청 간격 | **추가함 (2026-10-26)** — `--min-delay` (6.2) |
| DB | `bible_translation` 12번 행과 CHECK 값은 **이미 있다**. `bible_book` 66행만 필요 (7절) |
| 적재 | **하지 않았다** — 별도 게이트 (2절, 10절) |

## 4. 실측 결과

2026-10-26, 이 저장소의 `HolyBibleScraper` 요청 경로로 35개 장을 수집했다. `Crawl-delay: 15` 하한을 지켰고(실측 간격 15.6~18.6초), 자동 재시도는 끄고 요청당 한 번만 보냈다. 페이지는 구조 분석에만 쓰고 DB에 넣지 않았다.

- 13번째 요청(시 51편)에 **HTTP 500**이 한 번 왔다. 제한 페이지가 아니라 서버 오류였고, 잠시 뒤 한 번 다시 요청하자 정상이었다. 적재기에서는 `requests.RequestException` 재시도(최대 7회 시도)가 이를 처리한다. 제한 페이지는 한 번도 오지 않았다.
- 수집한 장은 NIV 표본 32개 장과 같고, ESV에서 확인할 곳 3개 장(눅 22, 계 13, 고후 13)을 더했다.
  - 기본: 창 1, 2 / 욜 2 / 말 4 / 롬 14, 16 / 계 12, 13 / 유다서 / 요삼 / 고후 13
  - 시편과 시: 시 3, 23, 51, 119 / 아 1
  - KJV에 있으나 비평본문이 빼는 절이 있는 장: 마 17, 18, 23 / 막 7, 9, 11, 15 / 눅 17, 23 / 요 5 / 행 8, 15, 24, 28
  - 괄호로 처리되는 본문: 막 16 / 요 7, 8 / 요일 5 / 눅 22

### 4.1 요소 개수 (대표 8개 장)

| 요소 | 창 1 | 시 3 | 시 119 | 아 1 | 막 16 | 요 7 | 행 8 | 요삼 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `span.text` | 34 | 20 | 376 | 59 | 25 | 60 | 49 | 18 |
| 고유 절 토큰 | 31 | 8 | 176 | 17 | 20 | 53 | 39 | **15** |
| `sup.footnote` | 8 | 1 | 9 | 2 | 1 | 7 | 5 | 1 |
| `sup.crossreference` | 22 | 17 | 268 | 38 | 51 | 91 | 53 | 16 |
| `h3` | 1 | 1 | 1 | 2 | 4 | 6 | 4 | 3 |
| `h4` | 2 | **3** | **24** | **10** | 2 | 2 | 2 | 2 |
| `span.small-caps` | 0 | 6 | 24 | 0 | 0 | 0 | 0 | 0 |
| `span.woj` | 0 | 0 | 0 | 0 | 4 | 19 | 0 | 0 |
| `p.translation-note` | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| `span.selah` | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |

- `h4` 중 2개는 모든 장에 있는 `h4.resources-header`(각주·상호참조 머리글)다. 컨테이너째 제거되므로 무해하다.
- 절 클래스를 단 스팬을 감싸는 요소는 `p`(클래스 없음, `line`, `chapter-N`, `top-1`, `first-line-none top-1`), `span.indent-1`, `span.chapter-N`, `h3`, `h4.psalm-title`, `h4.psalm-acrostic`, `h4.speaker`, `p.translation-note`뿐이다. `span.text`가 아닌 요소가 절 클래스를 직접 단 경우는 0이다. 즉 NIV·WEB·ASV에서 이미 다룬 것 밖의 구조는 없다.
- 35개 장 합계: 상호참조 2,012개, 각주 201개, `h3` 120개. 파싱 결과에 `[a]`·`(A)` 형태의 표지가 남은 절은 0이다.

### 4.2 KJV 대조

같은 DB의 KJV(10) 절 수와 35개 장을 비교했다.

| 결과 | 장 |
| --- | --- |
| 절 수와 마지막 절 번호가 KJV와 같다 | 19개 장 |
| 마지막 절 번호는 같고 중간에 구멍이 있다 | 15개 장, 구멍 16개 (5.1) |
| 다르다 | **요삼 1장: ESV 15절, KJV 14절** (NIV와 같다) |

- 계 12장(17절)·13장(18절), 롬 14장(23절), 말 4장(6절), 욜 2장(32절), 고후 13장(14절), 눅 22장(71절, 43–44절 포함), 막 16장(20절), 요 7장(53절)·8장(59절), 요일 5장(21절)은 KJV와 같다.
- 롬 16장은 마지막 절이 27로 KJV와 같고 24절만 빠진다. WEB처럼 송영을 14장 끝으로 옮기지 않는다.
- 예상 총 절 수는 **31,087절**(KJV 31,102 − 16 + 1)이다. 샘플 밖의 차이는 적재 후 8.2의 양방향 대조로 확정한다.

## 5. NIV와 달라지는 점

### 5.1 생략 절 — 스팬이 없다 (ASV 방식)

표본에서 ESV가 본문에서 빼는 절은 NIV와 **같은 16개**다. 그런데 NIV·WEB은 각주 표지만 든 빈 스팬을 남기고, **ESV는 ASV처럼 스팬 자체를 남기지 않는다.**

```html
<span class="text Rom-16-23"><sup class="versenum">23 </sup>(본문)<sup class="footnote">[g]</sup></span>
<!-- Rom-16-24 스팬 없음. 각주 [g]가 "일부 사본은 24절을 넣는다"고 적는다 -->
<span class="text Rom-16-25"><sup class="versenum">25 </sup>(본문)</span>
```

표본에서 구멍으로 나온 좌표는 아래 16개이고, NIV의 `(omitted)` 16개와 좌표까지 같다. 후보 장을 골라 수집한 결과이므로 표본 밖에 다른 생략 절이 없다는 보장은 아니다. 적재 후 8.2로 확정한다.

> 마 17:21, 18:11, 23:14 / 막 7:16, 9:44, 9:46, 11:26, 15:28 / 눅 17:36, 23:17 / 요 5:4 / 행 8:37, 15:34, 24:7, 28:29 / 롬 16:24

**구멍을 그대로 둔다.** 이 저장소의 계약을 따른다.

- `(omitted)`는 스팬이 각주 표지만 들고 있을 때만 쓴다. 근거가 되는 스팬이 페이지에 없으므로 쓸 수 없다.
- 하드코딩한 목록으로 채우면 소스가 준 적 없는 행이 DB에 들어가고, 진짜 파싱 실패와 판본 차이를 구분할 수 없게 된다. ASV(구멍 16개)와 N1904(구멍 15개)도 같은 이유로 구멍을 두었다.
- 그 대신 적재 후 구멍을 **위 고정 목록과 정확히 대조한다**(8.2). 목록 밖의 구멍은 파싱 실패다.
- 결과적으로 같은 16절이 NIV에서는 `(omitted)` 행이고 ESV에서는 행이 없다. 역본을 나란히 보여 줄 때 이 차이를 알아야 한다.

### 5.2 `h4` — 세 종류이고, 지금 규칙이 모두 지운다

| 종류 | ESV 표본 | NIV와의 차이 |
| --- | --- | --- |
| 시편 표제 | `h4.psalm-title` 3개 (시 3, 23, 51) | NIV는 클래스 없는 `h4`. ESV는 WEB·ASV와 같다 |
| 시 119편 히브리 자모 | `h4.psalm-acrostic` 22개 | 같다 |
| 아가 화자 표시 | `h4.speaker` 8개 | 위치가 다르다. ESV는 아 1:2, 4, 5, 8, 11, 12, 15, 16에 붙고, 그중 **1:2, 1:4, 1:8에서는 절 중간**에 있다 |

`h4.psalm-title`만 지우던 예전 규칙이었다면 표본에서 **30절이 오염됐을 것이다**(시 119편 22절, 아 1장 8절). 지금의 `h4` 전체 제거로는 0이다. 두 규칙의 절 번호 집합은 35개 장 모두 같다. 즉 `h4`를 지워서 사라지는 절은 없다.

### 5.3 small caps — `Lord`만 있고, 명패는 small caps가 아니다

- 본문의 `span.small-caps`는 64개이고 모두 `Lord`다. 파싱 결과에서 `LORD`가 64곳이다. small caps가 아닌 `Lord`(구약의 아도나이, 신약의 퀴리오스)는 60곳이고 그대로 남는다.
- 나머지 small caps 10개는 본문 밖이다. `h3` 소제목 안 6개, 각주 안 4개(`9 a.m.`, `3 p.m.` 같은 시각 표기 포함)이고, 컨테이너째 제거된다.
- **NIV와 달리 십자가 명패(막 15:26, 눅 23:38)는 small caps가 아니다.** 원문 대소문자 그대로 저장된다. NIV 설계 9.3의 소문자 명패 쿼리는 ESV에 해당이 없다.
- 표본에는 에스겔처럼 `Lord GOD`가 많은 책이 없다. 대문자화 규칙은 small caps 안의 글자를 모두 바꾸므로 `GOD`도 같은 방식으로 처리될 것이다. 적재 후 `GOD` 건수로 확인한다.

### 5.4 괄호 본문 — `[[ ]]`는 원문 문자다

ESV는 막 16:9–20과 요 7:53–8:11을 이중 대괄호로 감싸 인쇄한다. BibleGateway 페이지에서도 이 대괄호가 본문 글자로 들어 있다.

- 파싱 결과: 막 16:9와 요 7:53이 `[[`로 시작하고, 막 16:20과 요 8:11이 `]]`로 끝난다. 표본에서 대괄호가 든 절은 이 4개뿐이다.
- **그대로 저장한다.** 편집 표지가 아니라 판본의 본문이다. 지우면 원문과 달라진다.
- 두 단락 앞의 편집자 주는 NIV처럼 `p.translation-note`(다음 절의 클래스를 단 스팬)로 들어 있고, 기존 제거 규칙이 지운다(표본 2개).
- 눅 22:43–44는 대괄호 없이 본문에 있다.

### 5.5 그 밖의 확인 사항

- `Selah`는 절 스팬 안의 `span.selah`다(시 3:2, 4, 8). KJV처럼 본문으로 남고 앞 낱말과 공백으로 떨어진다.
- 비 ASCII 문자는 따옴표류(`“ ” ‘ ’`)와 `—`뿐이다. 유니코드 정규화는 필요 없다.
- 이중 공백, 앞뒤 공백, 숫자로 시작하는 절은 0이다.
- `span.woj`(예수의 말씀)는 표지 없이 글자만 남는다.

## 6. 코드 변경 지점

### 6.1 `scrape_bible_to_db.py`

```python
ENTRY_URL_ENV_BY_TRANSLATION_TYPE["ESV"] = "ESV_ENTRY_URL"
TRANSLATION_TYPES_BY_LANGUAGE_CODE["en"] = ("KJV", "WEB", "ASV", "NIV", "ESV")
ENTRY_URL_PREFERENCE_ORDER = (..., "NIV", "ESV")
TRANSLATION_SOURCE_REQUIREMENTS["ESV"] = {
    "source": "biblegateway",
    "version": "ESV",
    "name": "English Standard Version",   # DB 12번 행의 name과 같다
    "language_code": "en",
}
```

- 이 행이 없으면 `version=ESV`는 기대 역본이 없어(`_expected_translation_type()`가 `None`) 표에 없는 영어 역본 행(NASB, CSB …)과 함께 써도 검증을 통과한다. NIV 설계 6.2와 같은 이유로 **7절의 `bible_book`보다 먼저** 들어가야 한다.
- `version=ESVUK`는 `_version_matches()`가 정확히 비교하므로(대소문자만 무시) ESV 메타데이터와 함께 쓰면 거부된다.
- 기존 NIV 테스트는 "표에 없는 영어 역본" 예로 ESV를 쓰고 있었다. ESV가 표에 들어오므로 그 자리를 NASB(13)로 바꿨다.

### 6.2 `--min-delay` (새 CLI 옵션)

NIV 적재는 15~18초 간격에서 약 800번째 요청에 제한을 받았고, 남은 426장은 30~33초 간격의 **스크래치 래퍼**로 받았다. 그 래퍼는 세션이 바뀌며 사라졌다. ESV도 1,189장이므로 같은 간격이 필요하다. 그래서 저장소에 옵션으로 넣었다.

```python
def raise_delay_floor(self, seconds: float) -> None:   # HolyBibleScraper
    self.sleep_min = max(self.sleep_min, seconds)
    self.sleep_max = max(self.sleep_max, seconds + 3.0)
```

- `--min-delay 30`이면 요청 간격이 30~33초가 된다.
- `max()`라서 **간격을 줄이는 데는 쓸 수 없다.** `--min-delay 1`을 줘도 BibleGateway는 15~18초 그대로다. `Crawl-delay` 하한(`BIBLEGATEWAY_CRAWL_DELAY_SECONDS`)은 바꾸지 않았다.
- smoke test(DB 미접속)에도 같은 간격이 적용된다.

### 6.3 `scraper.py` 파서 — 변경 없음

5절의 차이는 모두 NIV 때 넣은 규칙(`h4` 전체 제거, small caps 대문자화)과 기존 규칙(`h3` 제거, 분할 절 병합)으로 처리된다. ESV 전용 분기는 만들지 않는다.

## 7. DB 준비

현재 상태(2026-10-26 실측, 읽기 전용 조회):

| 항목 | 상태 |
| --- | --- |
| `bible_translation` | **id 12, `ESV`, `English Standard Version`, `en` 행이 이미 있다**. `attribution`은 NULL |
| `translation_type` CHECK | `ESV` **이미 포함** |
| `bible_book` | **0권** |
| `bible_chapter` | 0 |

DDL은 필요 없다. `bible_book` 66행은 NIV 때와 같은 방식으로 KJV(10) 행을 복사한다.

```sql
SELECT setval('public.bible_book_id_seq', (SELECT COALESCE(MAX(id), 0) FROM public.bible_book), true);

INSERT INTO public.bible_book
    (translation_id, book_order, book_key, name, abbreviation, testament_type)
SELECT 12, src.book_order, src.book_key, src.name, src.abbreviation, src.testament_type
FROM public.bible_book src
WHERE src.translation_id = 10
  AND NOT EXISTS (
      SELECT 1 FROM public.bible_book dst
      WHERE dst.translation_id = 12 AND dst.book_order = src.book_order
  )
ORDER BY src.book_order;
```

- 이 SQL은 도구 밖에서, 사용자가 요청할 때만 실행한다. 도구는 `bible_book`을 만들지 않는다.
- `bible_book`의 identity는 `BY DEFAULT`라 시퀀스가 `MAX(id)`보다 뒤처져 있을 수 있다. 첫 줄의 `setval`이 그 차이를 맞춘다. NIV 때도 이 순서로 넣었다.
- `attribution` 후보: BibleGateway 페이지 하단 문구 `The ESV® Bible (The Holy Bible, English Standard Version®), © 2001 by Crossway, a publishing ministry of Good News Publishers. ESV Text Edition: 2025.`에 Crossway 표기의 `All rights reserved.`를 붙인다. NIV도 페이지 문구를 썼다. 2절대로 "Used by permission"은 넣지 않는다.

## 8. 검증

### 8.1 기본 검증

| 검증 | 기대값 |
| --- | --- |
| 절이 적재된 책 | 66 |
| 장 | 1,189 |
| 절 | **31,087** (KJV 31,102 − 생략 16 + 요삼 1:15) |
| 빈 절 / 첫 절이 1이 아닌 장 | 0 |
| `(omitted)` | **0** — ESV는 생략 절의 스팬을 남기지 않는다(5.1) |
| 절 번호 구멍 | **16** — 5.1 목록과 정확히 같은 좌표 |

NIV(31,103)와 비교하면 절 수가 16 적다. 같은 16절을 NIV는 `(omitted)` 행으로, ESV는 구멍으로 갖기 때문이다. 본문 차이가 아니다.

### 8.2 KJV 대조 — 양방향

ASV 설계 8.2의 쿼리를 `translation_id` 10 ↔ 12로 양방향 실행한다.

- KJV에만 있는 좌표: **5.1의 16개와 정확히 같아야 한다.** 하나라도 다르면 그 장을 원문에서 확인한다
- ESV에만 있는 좌표: **요삼 1:15 하나**
- 롬 14·16장은 KJV와 같은 위치에 송영이 있다(4.2). WEB처럼 두 방향에서 짝을 이루는 절 구분 차이는 표본에서 나오지 않았다

### 8.3 오염 검증

NIV 설계 9.3의 쿼리를 `translation_id = 12`로 돌린다. 히브리 자모, 아가 화자 표시, 각주·상호참조 표지(`[a]`, `(A)`)가 0이어야 한다. ESV는 명패를 small caps로 조판하지 않으므로(5.3) 명패 쿼리는 해당이 없다.

### 8.4 재파싱 대조

적재 직후 `check_translation_drift.py --translation-id 12`를 표본 책(시편, 아가, 마가복음)에 돌려 차이 0을 확인한다.

### 8.5 경계 구절 육안 확인

- 시 3:1, 51:1 — 표제가 없어야 한다
- 시 119:1, 119:169 — 히브리 자모가 없어야 한다
- 아 1:2, 1:4, 1:8 — 절 중간에 화자 표시가 없어야 한다
- 막 16:9, 요 7:53 — 편집자 주가 없어야 한다
- 롬 16:23 다음이 16:25인지 (16:24 구멍)
- 요삼 1:14, 1:15 — 둘 다 있어야 한다

## 9. 기존 WEB·ASV 보정과의 관계

NIV 설계 8절의 WEB·ASV 재파싱 대조는 아직 끝나지 않았다(WEB 시 137편까지). ESV와는 독립된 일이지만, **둘 다 BibleGateway에 요청을 보내므로 동시에 돌리지 않는다.** 요청 간격이 절반이 되어 제한을 받기 쉽다.

## 10. 운영 계획 — 적재는 별도 게이트

**2절의 권리 문제 때문에 ESV 전권 적재는 사용자가 따로 결정한다.** 결정 전에 할 수 있는 일은 배선, 테스트, smoke test(DB 미접속)다. 여기까지는 끝났다.

- 66권 / 1,189장 / 요청 1,189회
- **`--min-delay 30`으로 돌린다.** 30~33초 간격과 응답 시간을 더해 **약 10~11시간**이다. 15초 하한으로는 NIV처럼 중간에 제한을 받을 가능성이 높다
- 장 단위 커밋이므로 끊겨도 완료된 장은 남는다. 재개는 `--start-book`으로 한다
- `.env`는 NKRV(`BIBLE_TRANSLATION_ID=2`)를 가리키고 있다. 셸 환경변수로 ID·타입을 덮어쓴다(셸이 이긴다)
- `.env`에 다른 영어 `*_ENTRY_URL`이 있으면 `BIBLE_LANGUAGE_CODE=en`만으로는 엔트리가 결정되지 않는다. `--entry-url`과 `BIBLE_TRANSLATION_TYPE=ESV`를 함께 준다
- 제한 페이지가 반복되면 멈춘다. 적재기를 두 개 동시에 돌리지 않는다

smoke test(DB 미접속):

```bash
python3 scrape_bible_to_db.py --entry-url "https://www.biblegateway.com/passage/?search=Genesis%201&version=ESV" --test-book 64 --test-chapter 1 --min-delay 30
python3 scrape_bible_to_db.py --entry-url "https://www.biblegateway.com/passage/?search=Genesis%201&version=ESV" --test-book 22 --test-chapter 1
```

실행 결과(2026-10-26): 요삼 1장 15절(`--min-delay 30`을 주고 32초), 아 1장 17절(18초). 둘 다 4.2의 표본과 같다.

적재 실행 예(게이트 통과 후):

```bash
export BIBLE_TRANSLATION_ID=12
export BIBLE_TRANSLATION_TYPE=ESV
export ESV_ENTRY_URL="https://www.biblegateway.com/passage/?search=Genesis%201&version=ESV"
python3 scrape_bible_to_db.py --entry-url "$ESV_ENTRY_URL" --min-delay 30 --start-book 1 --end-book 66
```

## 11. 테스트

인라인 HTML 픽스처만 쓴다. 네트워크는 쓰지 않는다. 파서를 바꾸지 않았으므로 새 파서 테스트는 없다. ESV의 구조는 기존 테스트가 덮는다. `h4` 세 종류(절 중간 화자 포함), small caps, `p.translation-note`는 NIV 때의 테스트가, 스팬 없는 생략 절은 `test_parse_verses_from_biblegateway_handles_asv_chapter_without_verse_span`이 확인한다.

파이프라인(`tests/test_pipeline.py`):

- `version=ESV` + ESV 메타데이터 통과, `translation_type`이 비어 있어도 이름·언어로 통과
- `version=ESV` + WEB/ASV/NIV/NASB 메타데이터 거부, `version=WEB`/`ASV`/`NIV` + ESV 메타데이터 거부
- `version=ESVUK` + ESV 메타데이터 거부
- `ESV_ENTRY_URL`과 `BIBLE_TRANSLATION_TYPE=ESV`면 ESV가 선택되고, NIV URL과 함께 `en`만 주면 중단된다

스크래퍼(`tests/test_scraper.py`):

- `raise_delay_floor(30)`이면 30~33초가 된다
- `raise_delay_floor(1)`은 BibleGateway의 15초 하한을 내리지 못한다

## 12. 리스크

### 리스크 1. ESV 본문이 다른 영어 역본 행으로 들어간다

6.1의 행 없이 `bible_book`을 만들면 검증이 비어 있다. 대응: 행과 테스트를 먼저 넣었다(이 문서와 같은 변경).

### 리스크 2. 구멍을 파싱 실패로 오인하거나, 파싱 실패를 구멍으로 오인한다

ESV는 `(omitted)`가 없어 "절 번호 연속"이 불변식이 아니다. 대응: 8.2에서 구멍 좌표를 5.1의 고정 목록과 정확히 대조한다. 목록 밖의 구멍은 실패다.

### 리스크 3. 권리 상태를 잊는다

NIV와 같다. 대응: README·CLAUDE.md에 ESV의 권리 상태를 적고, 적재하면 `attribution`을 비워 두지 않는다.

### 리스크 4. 요청 차단

대응: `--min-delay 30`, 제한 페이지가 반복되면 중단, WEB·ASV 대조와 동시에 돌리지 않는다(9절).

### 리스크 5. 적재본이 낡는다

ESV는 텍스트판이 개정된다(2절, 2025-02-20 변경 이력에 42절). missing-only라 다시 돌려도 고쳐지지 않는다. 대응: 개정이 의심되면 `check_translation_drift.py`로 차이를 찾고 해당 절을 지운 뒤 다시 적재한다.

## 13. 결론

- 기술적으로 ESV는 WEB·ASV·NIV와 같은 어댑터로 수집할 수 있다. 파서 수정은 필요 없다. NIV 때 넣은 `h4` 전체 제거와 small caps 대문자화가 ESV의 시편 표제, 시 119편 자모, 아가 화자 표시, `LORD`를 그대로 처리한다.
- 생략 절은 ASV처럼 스팬이 없어 구멍으로 남는다. 총 31,087절이 예상값이다.
- 코드 변경은 정합성 검증 표 한 행과 엔트리 URL 해석, 그리고 전권 적재용 `--min-delay` 옵션이다.
- ESV 전권 적재는 Crossway의 무허가 인용 한도와 BibleGateway 이용약관을 넘는다. 적재는 사용자가 결정한다.
