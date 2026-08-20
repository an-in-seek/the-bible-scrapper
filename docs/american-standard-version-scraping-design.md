# BibleGateway ASV(American Standard Version) 본문 스크래핑 개발 설계

## 1. 목적

`biblegateway.com`의 ASV(American Standard Version, 1901) 본문을 수집해 **창세기 1장부터 요한계시록 22장까지 66권 전 구절**을 적재한다.

- 예시 URL
  - `https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV`
  - `https://www.biblegateway.com/passage/?search=1%20Samuel%201&version=ASV`
  - `https://www.biblegateway.com/passage/?search=Jude%201&version=ASV`

ASV는 이미 구현된 [WEB 설계](world-english-bible-scraping-design.md)와 **같은 소스·같은 URL 규칙**을 쓴다. 따라서 이 문서는 WEB 설계를 처음부터 반복하지 않고, **재사용 가능한 부분과 달라지는 부분**만 다룬다.

WEB 문서에서 그대로 유효한 항목:

- URL 생성 규칙과 66권 영문 책명 매핑 (5절)
- 절 번호를 `span.text` 클래스 토큰에서 읽는 규칙 (2.3 함정 1~3)
- 분할 절 병합, 각주·상호참조 제거 (6절)
- `robots.txt`의 `Crawl-delay: 15` 준수와 전권 약 5시간 (9절)
- `bible_book`을 생성하지 않고 누락분만 insert 하는 적재 계약 (3.2절)
- 전권 적재 운영 계획과 완료 검증 쿼리 (11절)

커밋 단위(장 단위)와 재시도 정책은 WEB 문서가 아니라 [README](../README.md)의 "적재 방식"과 [CLAUDE.md](../CLAUDE.md)에 있다.

## 2. 결론 먼저

**파서 코드는 한 줄도 바꿀 필요가 없다.** 실제 ASV 응답 6건으로 확인했다.

| 항목 | 상태 |
| --- | --- |
| `_extract_verses_from_biblegateway_passage()` | 수정 불필요 |
| `_build_biblegateway_url()` / 장 목록 생성 | 수정 불필요 (`version`을 엔트리 URL에서 승계) |
| `get_source_name()` / crawl-delay 하한 | 수정 불필요 |
| 엔트리 URL 해석 | **수정 필요** |
| 소스/번역본 정합성 검증 | **수정 필요 (현재 구멍 있음)** |
| `bible_book` 준비 | **필요 (현재 0권)** |
| 본문 없는 절 처리 | **미결정 — 7절 참고** |

즉 작업 대부분은 파싱이 아니라 **CLI 배선과 운영**이다.

## 3. 실측 검증 결과

`Crawl-delay: 15`를 지켜 6개 장을 수집한 뒤 현재 파서를 그대로 돌린 결과다.

### 3.1 요소 개수

| 요소 | Gen 1 | Gen 2 | Ps 23 | Matt 5 | Acts 8 | Jude |
| --- | --- | --- | --- | --- | --- | --- |
| `div.passage-text` | 1 | 1 | 1 | 1 | 1 | 1 |
| `span.text` | 31 | 25 | 15 | 48 | 45 | 25 |
| 고유 절 토큰 | 31 | 25 | 6 | 48 | 39 | 25 |
| `span.chapternum` | 1 | 1 | 1 | 1 | 1 | **0** |
| `sup.versenum` | 30 | 24 | 5 | 47 | 39 | 25 |
| `sup.footnote` | 5 | 8 | 4 | 21 | 13 | 20 |
| `sup.crossreference` | 0 | 0 | 0 | 0 | 0 | 0 |
| `div.footnotes` | 1 | 1 | 1 | 1 | 1 | 1 |
| `h4.psalm-title` | 0 | 0 | **1** | 0 | 0 | 0 |
| `h3` | 0 | 0 | **1** | 0 | 0 | 0 |
| `span.woj` | 0 | 0 | 0 | **0** | 0 | 0 |
| `div.poetry` | 0 | 0 | 1 | 0 | 1 | 0 |
| 중첩 `span.text` | 0 | 0 | 0 | 0 | 0 | 0 |

`data-osis`는 6건 모두 존재한다: `Gen.1.1-Gen.1.31`, `Gen.2.1-Gen.2.25`, `Ps.23.1-Ps.23.6`, `Matt.5.1-Matt.5.48`, `Acts.8.1-Acts.8.40`, `Jude.1.1-Jude.1.25`

### 3.2 파싱 결과

| 샘플 | 추출 절 수 | 연속성 | 비고 |
| --- | --- | --- | --- |
| Genesis 1 | 31 | 정상 | |
| Genesis 2 | 25 | 정상 | 1절이 `chapternum`으로 `2`를 표시하지만 절 번호 1로 저장 |
| Psalms 23 | 6 | 정상 | 표제·소제목 제외, 분할 절 병합 |
| Matthew 5 | 48 | 정상 | |
| Acts 8 | 39 | **비연속** | 37절 없음 — 7절 참고 |
| Jude | 25 | 정상 | 단일 장 책, `chapternum` 없음 |

분할 절은 WEB과 동일하게 나타난다. Psalms 23은 15개 스팬이 6절로, Acts 8은 45개 스팬이 39절로 병합된다(`Acts-8-32`는 4조각).

## 4. WEB과 달라지는 지점

### 4.1 편집자 소제목 `h3`가 존재하며 절 클래스를 달고 있다

WEB은 6개 샘플 전부 `h3`가 0개였다. **ASV는 다르다.**

```html
<h4 class="psalm-title"><span class="text Ps-23-1">A Psalm of David.</span></h4>
<h3><span class="text Ps-23-1" id="en-ASV-14237">Jehovah the psalmist's shepherd.</span></h3>
```

`h3` 안의 스팬이 **1절 클래스(`Ps-23-1`)를 그대로 갖는다.** 제거하지 않으면 Psalms 23:1 본문 앞에 소제목이 붙는다.

현재 파서는 `BIBLEGATEWAY_CONTAINER_REMOVABLE_SELECTOR`에 `h3`를 포함하고 있어 이미 올바르게 처리한다. WEB 설계 때 "관측되지 않았지만 사이트 개편 대비로 남긴다"고 적어둔 방어 항목이 ASV에서는 **필수 요건**이 된 셈이다.

`h3` 제거가 절을 통째로 날릴 위험도 확인했다. 6개 샘플 전부에서 제거 전후 절 토큰 집합이 동일했다(소실 0건). 소제목 스팬은 항상 본문 스팬과 공존한다.

이 항목을 "쓰이지 않는 코드"라고 판단해 제거하면 ASV가 조용히 깨진다.

### 4.2 본문 없는 절의 표현 방식이 다르다

WEB은 스팬을 남기고 각주 마커만 넣는다.

```html
<span class="text Acts-8-37"><sup class="versenum">37 </sup><sup class="footnote">[a]</sup></span>
```

**ASV는 스팬 자체가 없다.** 각주 마커가 앞 절 끝에 붙는다.

```text
36  And as they went on the way, ... what doth hinder me to be baptized? [l]
38  And he commanded the chariot to stand still: ...
```

각주 본문은 해당 절 번호를 명시한다.

> Acts 8:36 — Some ancient authorities insert, wholly or in part, verse 37 …

결과적으로 WEB에 넣은 `(omitted)` 마커 조건(`sup.footnote`가 있고 본문이 빈 스팬)이 **ASV에서는 발동하지 않는다.** 처리 방향은 7절에서 다룬다.

### 4.3 그 밖의 차이

- **각주가 훨씬 많다.** Genesis 1 기준 WEB 2개 / ASV 5개, Jude 기준 WEB 4개 / ASV 20개. 각주 제거가 제대로 되지 않으면 오염이 WEB보다 크게 드러난다.
- **`span.woj`가 없다.** Matthew 5에서 WEB은 62개였으나 ASV는 0개다. BibleGateway가 ASV를 red-letter로 조판하지 않는다.
- **`sup.crossreference`가 없다.** 6건 모두 0개다. WEB은 Matthew 5에 9개가 있었다.
- 본문 표기가 다르다. ASV는 `LORD` 대신 `Jehovah`를 쓴다. 파싱에는 영향이 없다.

## 5. 코드 변경 지점

### 5.1 엔트리 URL 해석 (`scrape_bible_to_db.py`)

```python
ENTRY_URL_ENV_BY_TRANSLATION_TYPE = {
    "KJV": "KJV_ENTRY_URL",
    "NKRV": "NKRV_ENTRY_URL",
    "WEB": "WEB_ENTRY_URL",
    "ASV": "ASV_ENTRY_URL",      # 추가
}
TRANSLATION_TYPES_BY_LANGUAGE_CODE = {
    "ko": ("NKRV",),
    "en": ("KJV", "WEB", "ASV"),  # 3종으로 확대
}
ENTRY_URL_PREFERENCE_ORDER = ("NKRV", "KJV", "WEB", "ASV")
```

`en` 후보가 3종이 되므로 `BIBLE_LANGUAGE_CODE=en`만으로는 소스가 결정되지 않는 경우가 더 늘어난다. 현재 구현은 후보가 2개 이상이면 `Ambiguous entry URL` 오류로 중단하므로 동작은 그대로 안전하다.

**단, `BIBLE_TRANSLATION_ID`는 소스를 지시하지 못한다.** `_translation_type_hint()`가 참조하는 `LEGACY_TRANSLATION_TYPE_BY_ID`에는 `{"2": "NKRV"}`만 있어, ASV의 `23`은 힌트가 되지 않는다. 실제로 확인한 동작은 아래와 같다.

```text
BIBLE_TRANSLATION_ID=23 (ASV), KJV_ENTRY_URL + WEB_ENTRY_URL 설정
-> 타입 힌트 None -> 선호 순위 fallback -> KJV_ENTRY_URL 선택 (오류 없음)
```

즉 **경고 없이 엉뚱한 소스가 선택된다.** 이 함정은 WEB 적재 때 실제로 발생했다(그때는 NKRV가 선택됐고 정합성 검증이 막았다).

대응은 둘 중 하나다.

- `BIBLE_TRANSLATION_TYPE=ASV`를 함께 설정한다 (권장)
- `--entry-url`을 명시한다

`LEGACY_TRANSLATION_TYPE_BY_ID`에 `23`을 추가하는 방법은 권하지 않는다. `translation_id`는 환경마다 다른 값이라 코드에 고정하면 다른 DB에서 틀린다.

권장 `.env`:

```env
ASV_ENTRY_URL=https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV
```

### 5.2 소스/번역본 정합성 검증 — **현재 구멍이 있다**

`validate_source_translation_compatibility()`는 `biblegateway` + `version=WEB`만 엄격히 검사한다. `version=ASV`는 그 분기를 타지 않고, 아래 일반 규칙만 적용된다.

```python
if source_name == "biblegateway" and translation_type in ("KJV", "NKRV"):
    raise RuntimeError(...)
```

즉 **`version=ASV` 소스에 WEB 번역본 메타데이터를 붙이면 검증을 통과한다.** ASV 본문이 `translation_id=22`(WEB) 아래로 적재될 수 있다는 뜻이다. 되돌리는 비용이 크므로 반드시 막아야 한다.

권장 구조는 버전별 분기를 늘리는 대신 표로 일반화하는 것이다.

```python
BIBLEGATEWAY_VERSION_TO_TRANSLATION = {
    "WEB": ("WEB", "World English Bible"),
    "ASV": ("ASV", "American Standard Version"),
}
```

- 엔트리 URL의 `version`이 표에 있으면, 해당 `translation_type`이어야 통과
- `translation_type`이 비어 있고 `name` + `language_code='en'`이 일치하면 경고 후 통과
- 표에 있는 다른 버전의 타입이면 오류

이렇게 하면 이후 역본을 추가할 때 표 한 줄만 늘어난다.

#### 역방향 구멍도 함께 막아야 한다

현재 검증은 다른 소스가 ASV 메타데이터를 쓰는 것도 막지 못한다.

```python
if source_name == "thekingsbible":
    if translation_type in ("NKRV", "WEB"):   # ASV 없음
        raise RuntimeError(...)
...
if source_name == "bskorea" and translation_type == "WEB":   # ASV 없음
    raise RuntimeError(...)
```

`thekingsbible` 소스에 `translation_type='ASV'`를 붙이면 통과한다. 5.1의 엔트리 URL 함정과 결합하면 실제로 도달 가능한 경로다.

```text
BIBLE_TRANSLATION_ID=23 만 설정 -> 엔트리 URL이 KJV로 선택됨
-> 소스=thekingsbible, 번역본=ASV -> 검증 통과 -> KJV 본문이 ASV로 적재됨
```

따라서 표를 "역본 타입 -> 허용 소스" 방향으로도 쓰거나, 각 소스 분기의 금지 타입 목록에 `ASV`를 추가해야 한다. 역본이 늘어날 때마다 모든 분기를 손대야 하는 구조이므로, **표 하나로 양방향을 판정하는 형태가 낫다.**

### 5.3 파서 — 변경 없음

`_extract_verses_from_biblegateway_passage()`는 그대로 동작한다. ASV 전용 분기를 만들면 안 된다. 두 역본의 DOM 계약이 동일하므로 분기는 중복만 늘린다.

### 5.4 `resolve_book_code_for_source()` — 변경 없음

`get_source_name()`이 `biblegateway`를 반환하는 순간 영문 책명 상수를 쓰므로 ASV도 그대로 적용된다.

## 6. DB 준비

현재 상태(실측):

| translation_id | type | name | bible_book |
| --- | --- | --- | --- |
| 10 | KJV | King James Version | 66권 |
| 22 | WEB | World English Bible | 66권 |
| **23** | **ASV** | **American Standard Version** | **0권** |

`bible_translation` row는 이미 있으나 `bible_book`이 비어 있다. 스크래퍼는 `bible_book`을 생성하지 않으므로 적재 전에 66권을 만들어야 한다.

WEB 때와 동일하게 KJV(10) 행을 복사하면 된다. 영문 역본이라 `book_key` / `name` / `abbreviation` / `testament_type`을 그대로 쓸 수 있다.

```sql
-- identity가 BY DEFAULT이므로 시퀀스를 먼저 맞춘다
SELECT setval('public.bible_book_id_seq', (SELECT COALESCE(MAX(id), 0) FROM public.bible_book), true);

INSERT INTO public.bible_book
    (translation_id, book_order, book_key, name, abbreviation, testament_type)
SELECT 23, src.book_order, src.book_key, src.name, src.abbreviation, src.testament_type
FROM public.bible_book src
WHERE src.translation_id = 10
  AND NOT EXISTS (
      SELECT 1 FROM public.bible_book dst
      WHERE dst.translation_id = 23 AND dst.book_order = src.book_order
  )
ORDER BY src.book_order;
```

시퀀스 동기화를 건너뛰면 중복 PK 오류가 난다. WEB 적재 때 실제로 시퀀스가 `MAX(id)`보다 뒤처져 있었다.

## 7. 미결정 사항 — 본문 없는 절 처리

이 문서에서 유일하게 결론이 열려 있는 항목이다.

### 7.1 문제

ASV는 KJV에 있는 여러 절을 본문에서 빼고 각주로 처리한다. WEB과 달리 **스팬 자체가 없어** 스크래핑 시점에는 그 절의 존재를 알 수 없다. 그대로 적재하면 `bible_verse`에 절 번호 구멍이 생긴다.

같은 DB의 개역개정은 이런 구절을 `(없음)`으로, WEB은 `(omitted)`로 명시하고 있다. ASV만 구멍을 내면 역본 간 표현이 어긋나고, **구멍이 역본의 의도인지 스크래핑 실패인지 DB만 봐서 구분할 수 없다.**

확인된 사례는 Acts 8:37 하나다. ASV는 개정역(Revised Version) 계열이라 Matthew 17:21, 18:11, 23:14, Mark 7:16, 9:44, 9:46, 11:26, 15:28, Luke 17:36, 23:17, John 5:4, Acts 15:34, 24:7, 28:29, Romans 16:24 등도 같은 처리를 할 가능성이 높으나, **이 목록은 추정이며 8.2의 대조 쿼리로 확정해야 한다.**

### 7.2 선택지

**옵션 A. 구멍을 그대로 둔다**

- 장점: 구현 없음
- 단점: 다른 두 역본과 표현이 어긋난다. 검증 4가 항상 N건을 반환해 예외 목록을 들고 다녀야 하고, 진짜 누락이 묻힌다

**옵션 B. 파서가 절 번호 구멍을 감지해 마커를 채운다**

- 장점: 자동
- 단점: **위험하다.** 파싱 실패로 절 하나가 유실된 경우와 구분되지 않는다. WEB에서 "각주 스팬이라는 양성 증거가 있을 때만 마커를 넣는다"는 원칙을 세운 이유가 그대로 적용된다. 여기엔 그 증거가 DOM에 없다

**옵션 C. 적재 후 대조로 목록을 확정하고 일회성 스크립트로 채운다 — 권장**

1. 먼저 그대로 적재한다
2. 8.2 쿼리를 **양방향으로** 돌려 차이 좌표를 열거한다
3. 절 구분 차이와 진짜 누락 후보를 분류한다 (8.2의 분류 기준)
4. 후보를 육안 검토한다 (각주가 해당 절을 언급하는지 확인)
5. 확정된 목록만 `(omitted)`로 채운다

- 장점: 채워 넣는 절이 전부 사람이 확인한 목록이다. 파서는 계속 "모르는 구멍은 실패로 남긴다"는 성질을 유지한다
- 단점: 수동 단계가 한 번 들어간다

권장은 옵션 C다. 자동화의 편의보다 **오탐이 조용히 쌓이지 않는 성질**이 중요하다.

각주 본문에서 `verse 37` 같은 표현을 파싱해 자동 판정하는 방법도 있으나, 영어 산문 표현에 의존하므로 채택하지 않는다.

## 8. 검증

WEB 설계 11.4의 검증 1~5를 그대로 쓰되(`:tid`를 23으로), ASV에는 아래 대조 검증을 추가한다.

### 8.1 기본 검증

| 검증 | 기대값 |
| --- | --- |
| 1. 절이 적재된 책 수 | 66 |
| 2. 총 장 수 | 1,189 |
| 3. 빈 장 | 0건 |
| 4. 절 번호 연속성 위반 | 7절의 처리 방향에 따름 |
| 5. 본문 오염 | 0건 |

검증 5의 각주 잔존 패턴(`\[[a-z]\]`)은 ASV에서 특히 중요하다. 각주 수가 WEB의 3~5배라 파서가 어긋나면 즉시 대량으로 잡힌다.

### 8.2 KJV 대조 — ASV 전용

같은 DB에 KJV(10)가 66권 31,102절로 이미 적재되어 있으므로, ASV에 없는 절 좌표를 열거할 수 있다.

```sql
SELECT kb.book_order, kb.name, kc.chapter_number, kv.verse_number
FROM public.bible_verse kv
JOIN public.bible_chapter kc ON kc.id = kv.chapter_id
JOIN public.bible_book kb    ON kb.id = kc.book_id
WHERE kb.translation_id = 10
  AND NOT EXISTS (
      SELECT 1
      FROM public.bible_verse av
      JOIN public.bible_chapter ac ON ac.id = av.chapter_id
      JOIN public.bible_book ab    ON ab.id = ac.book_id
      WHERE ab.translation_id = 23
        AND ab.book_order    = kb.book_order
        AND ac.chapter_number = kc.chapter_number
        AND av.verse_number   = kv.verse_number
  )
ORDER BY kb.book_order, kc.chapter_number, kv.verse_number;
```

이 결과를 그대로 "누락 목록"으로 쓰면 안 된다. **절 구분(versification) 차이가 섞여 나온다.**

WEB(22)으로 이 쿼리를 자기검증한 결과가 근거다. WEB은 검증 1~5를 모두 통과했고 총 절 수도 KJV와 같은 31,102절인데, 쿼리는 3건을 반환한다.

| | Romans 14 | Romans 16 |
| --- | --- | --- |
| KJV | 23절 | 27절 |
| WEB | **26절** | **24절** |

송영을 KJV는 Romans 16:25-27에, WEB은 Romans 14:24-26에 둔다. 내용은 양쪽 모두 있고 좌표만 다르므로 누락이 아니다. 반대 방향 쿼리도 정확히 3건을 반환해 대칭을 이룬다.

따라서 **반드시 양방향으로 실행한다.** `translation_id` 10과 23을 서로 바꿔 두 번 돌린 뒤 아래로 분류한다.

- 두 방향에서 같은 책의 다른 장이 같은 건수로 짝을 이룸 -> **절 구분 차이**. 그대로 둔다
- 한 방향에서만 나오고 짝이 없음 -> **진짜 누락 후보**. 7.2 옵션 C의 입력이 된다

후보로 분류된 절은 해당 장의 각주를 확인해 ASV가 의도적으로 뺀 것인지 검증한다(4.2의 `verse 37` 형태).

### 8.3 경계 구절 육안 확인

- `Genesis 2:1` — `chapternum`이 `2`인데 절 번호가 `1`인지
- `Psalms 23:1` — 표제(`A Psalm of David.`)와 소제목이 본문에 섞이지 않았는지 (**ASV 최대 함정**)
- `Psalms 119:176` — 최장 장의 마지막 절
- `Acts 8:36` — 각주 마커 `[l]`이 제거됐는지
- `Jude 1:25`, `Revelation 22:21` — 마지막 절

## 9. 테스트 설계

기존 BibleGateway 테스트가 대부분 커버하므로 추가는 최소한으로 한다. inline HTML fixture 기반이며 네트워크를 타지 않는다.

필수 추가:

- **`h3` 소제목 제외** — `h3 > span.text.Ps-23-1`과 본문 스팬이 함께 있을 때 소제목이 1절에 섞이지 않는지
  - 현재 파서가 이미 통과하지만, 회귀 방지를 위해 명시적 테스트가 필요하다. `h3` 제거를 "쓰이지 않는 코드"로 오해해 지우는 것을 막는 장치다
- ~~ASV 엔트리 URL로 version 승계~~ — `test_build_biblegateway_url_inherits_version_from_entry_url`이 이미 `version=ASV`로 검증하고 있다. 추가 불필요
- **정합성 검증** — `version=ASV` + WEB 메타데이터 조합에서 오류가 나는지 (5.2의 구멍을 막았는지)
- **엔트리 URL 해석** — `ASV_ENTRY_URL`만 설정 시 선택되는지, `KJV`/`WEB`/`ASV`가 함께 있고 `en`만 주면 중단되는지

기존 테스트 중 ASV로도 유효해 재작성이 불필요한 것:

- 절 번호를 클래스 토큰에서 읽는지
- 분할 절 병합
- 각주·상호참조 제거
- 첫 `passage-text`만 사용

## 10. 운영 계획

WEB 설계 11절과 동일하다.

- 66권 / 1,189장 / 요청 1,189회
- `Crawl-delay: 15` 준수로 **약 5시간**
- 장 단위 커밋이므로 중간에 끊겨도 완료된 장은 보존된다
- 재개는 `--resume`이 아니라 `--start-book` 명시로 한다

실행 예:

```bash
export BIBLE_TRANSLATION_ID=23
export BIBLE_TRANSLATION_TYPE=ASV
export ASV_ENTRY_URL="https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV"
python3 scrape_bible_to_db.py --entry-url "$ASV_ENTRY_URL" --start-book 1 --end-book 5
```

`.env`에 다른 `*_ENTRY_URL`이 함께 있으면 `--entry-url`을 명시하는 편이 안전하다. WEB 적재 때 `BIBLE_TRANSLATION_ID`만 지정했다가 엔트리 URL이 NKRV로 해석되어 실행이 중단된 사례가 있다(정합성 검증이 막아냈다).

smoke test(DB 미접속):

```bash
export ASV_ENTRY_URL="https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV"
python3 scrape_bible_to_db.py --entry-url "$ASV_ENTRY_URL" --test-genesis1
python3 scrape_bible_to_db.py --entry-url "$ASV_ENTRY_URL" --test-book 19 --test-chapter 23
```

Psalms 23을 smoke test 대상에 넣는 이유는 표제와 `h3` 소제목이 함께 나타나는 검증 지점이기 때문이다.

## 11. 구현 순서

1. `ENTRY_URL_ENV_BY_TRANSLATION_TYPE` 등 엔트리 URL 해석에 ASV 추가
2. `validate_source_translation_compatibility()`를 버전 표 기반으로 일반화 (5.2)
3. 테스트 추가 (9절)
4. `bible_book` 66권 시드 (6절)
5. smoke test — Genesis 1, Psalms 23, Jude
6. 단일 책 적재 후 검증
7. 구간 분할로 전권 적재
8. 검증 1~5 + 8.2 KJV 대조
9. 7.2 옵션 C에 따라 본문 없는 절 처리 결정 및 반영
10. README 지원 소스 표와 CLAUDE.md 갱신 (WEB 추가 때와 동일)

## 12. 리스크

### 리스크 1. `h3` 제거 코드가 삭제된다

WEB만 보면 `h3`는 한 번도 등장하지 않아 불필요해 보인다. 지우면 ASV의 시편·예언서 소제목이 절 본문에 섞인다.

대응: 9절의 `h3` 회귀 테스트와 이 문서의 4.1을 근거로 남긴다.

### 리스크 2. ASV가 WEB 번역본으로 적재된다

5.2의 검증 구멍이 그대로 있으면 발생한다. 적재 후 발견하면 되돌리는 비용이 크다.

대응: 구현 순서 2번을 전권 적재 이전에 반드시 끝낸다.

### 리스크 3. 절 번호 구멍의 성격을 잃는다

7절 처리를 미루면 시간이 지날수록 "이 구멍이 원래 그런 것인지" 판단할 근거가 사라진다.

대응: 적재 직후 8.2 대조 결과를 문서에 기록한다.

### 리스크 4. 요청 차단

전권 5시간 동안 단일 IP에서 1,189회 요청한다.

대응: crawl-delay 하한은 코드에서 강제되고 있다. 구간을 나눠 실행하고, 429가 반복되면 중단한다.

## 13. 결론

ASV는 WEB과 같은 어댑터로 **파서 수정 없이** 수집할 수 있다. 실제 응답 6건으로 확인했다.

실제 작업은 세 가지다.

- 엔트리 URL 해석과 정합성 검증에 ASV를 배선한다 (특히 5.2의 검증 구멍)
- `bible_book` 66권을 준비한다
- 본문 없는 절을 어떻게 표기할지 결정한다 (7절, 권장은 옵션 C)

WEB 설계에서 "관측되지 않았지만 방어적으로 남긴다"고 했던 `h3` 제거가 ASV에서는 필수 요건이 되었다는 점이, 소스별 방어 항목을 성급히 정리하면 안 되는 이유를 보여준다.
