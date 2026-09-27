# eBible.org RV1909(Reina Valera 1909) 본문 스크래핑 개발 설계

## 1. 목적

`ebible.org`의 스페인어 역본 **Reina Valera 1909**(`spaRV1909`) 본문을 수집해 **창세기 1장부터 요한계시록 22장까지 66권 전 구절**을 적재한다.

- 예시 URL
  - `https://ebible.org/spaRV1909/GEN01.htm`
  - `https://ebible.org/spaRV1909/GEN02.htm`
  - `https://ebible.org/spaRV1909/PSA023.htm`

이 문서의 모든 DOM·URL 서술은 실제 응답으로 확인한 것이다. 확인 범위는 3절에 있다.

### 1.1 라이선스

RV1909는 **퍼블릭 도메인**이다. 각 장 페이지 하단이 `copyright.htm`으로 링크하며 `Public Domain`으로 표기된다.

- 상업적·비상업적 이용, DB 적재·가공, 재배포에 제약이 없다
- 별도 라이선스 비용이나 허가 절차가 없다

`robots.txt` 실측 결과도 제약이 없다.

```text
User-agent: Baiduspider
Disallow: /index.php/component
```

`/spaRV1909/`는 어떤 봇에도 차단되어 있지 않고, **`Crawl-delay` 선언도 없다.** 요청 간격 정책은 9절에서 따로 정한다.

### 1.2 기존 소스와의 관계

이 저장소는 이미 3개 소스를 지원한다.

| 소스 | 방식 |
| --- | --- |
| `thekingsbible.com` | 경로 기반 URL |
| `bskorea.or.kr` | 쿼리 파라미터 URL |
| `biblegateway.com` | 쿼리 파라미터 URL (WEB / ASV 공용) |

ASV를 추가할 때는 WEB 어댑터를 그대로 재사용해 파서 수정이 전혀 없었다. **eBible은 다르다.** 정적 파일 구조와 DOM이 모두 달라 **전용 파서가 필요하다.** 근거는 4절에 있다.

## 2. 결론 먼저

| 항목 | 상태 |
| --- | --- |
| URL 생성 (`_build_ebible_url`) | **신규 필요** |
| 장 목록 생성 | **신규 필요** (`KJV_CHAPTER_COUNTS` 재사용) |
| 책 코드 매핑 | **기존 `BSKOREA_BOOK_CODES` 대문자화로 충족** (66권 실측 검증) |
| 절 파서 (`_extract_verses_from_ebible_page`) | **신규 필요** |
| 소스 판별 / `get_source_name()` | **신규 필요** |
| HTTP 응답 인코딩 처리 | **공유 코드 수정 필요 — 5.1 참고** |
| 엔트리 URL 해석 / 정합성 검증 | 표에 한 줄 추가 |
| `bible_translation` row | **없음 — 신규 생성 필요** |
| `bible_book` 66권 | **없음 — 시드 필요** |

작업량은 ASV(배선만)와 WEB(파서 신규) 사이에 있다. 파서는 새로 만들어야 하지만, BibleGateway보다 **DOM이 훨씬 단순하다.**

## 3. 실측 검증 범위

아래 9개 장을 수집해 구조를 확인하고 프로토타입 파서를 돌렸다. 장르를 흩어 뽑았다.

| 샘플 | 파일 | 절 수 | 특징 |
| --- | --- | --- | --- |
| 창세기 1장 | `GEN01.htm` | 31 | 기준 (율법) |
| 시편 23편 | `PSA023.htm` | 6 | 표제 포함, 3자리 장 번호 |
| 시편 119편 | `PSA119.htm` | 176 | 최장 장 |
| 욥기 3장 | `JOB03.htm` | 26 | 지혜서 시가 |
| 이사야 1장 | `ISA01.htm` | 31 | 예언서 |
| 마태복음 17장 | `MAT17.htm` | 27 | 17:21 포함 여부 확인 |
| 마가복음 16장 | `MRK16.htm` | 20 | 긴 결말 |
| 사도행전 8장 | `ACT08.htm` | 40 | 8:37 포함 여부 확인 |
| 요한3서 | `3JN01.htm` | 14 | 단일 장, 숫자 시작 책 코드 |

추가로 **66권 × (1장 + 마지막 장) = 132개 URL을 전수 probe** 했다. 실패 0건이다.

## 4. 대상 페이지 특성

### 4.1 URL 규칙

```text
https://ebible.org/spaRV1909/{책코드}{장번호}.htm
```

- 책 코드: USFM 대문자 3자 (`GEN`, `PSA`, `1SA`, `3JN`, `REV` …)
- 장 번호: **0으로 채운 고정 자릿수**

자릿수 규칙이 이 소스의 첫 번째 함정이다.

| URL | 결과 |
| --- | --- |
| `GEN50.htm` | 200 |
| `PSA23.htm` | **404** |
| `PSA023.htm` | 200 |
| `PSA119.htm` | 200 |

**시편만 3자리, 나머지 65권은 2자리다.** 장 수가 100을 넘는 책이 시편(150장)뿐이기 때문이다. 따라서 자릿수는 책의 장 수에서 계산한다.

```python
width = 3 if chapter_count >= 100 else 2
f"{chapter_number:0{width}d}"
```

`PSA09.htm`도 404이고 `PSA009.htm`이 200이므로, 시편은 한 자리 장도 3자리로 채워야 한다.

#### 책 코드는 기존 상수를 재사용할 수 있다

`scraper.py`의 `BSKOREA_BOOK_CODES`는 이미 USFM 코드 66개를 소문자로 담고 있다(`gen`, `exo`, …, `3jn`, `jud`, `rev`). eBible은 같은 코드를 대문자로 쓴다.

**66권 전체를 실제로 probe 해 확인했다.** 1장과 마지막 장 132개 URL이 모두 200이다.

```python
code = BSKOREA_BOOK_CODES[book_order - 1].upper()
```

bskorea 설계 문서는 "다른 소스의 코드 표를 그대로 믿지 말라"고 경고했지만, 여기서는 **추정이 아니라 전수 검증으로 확인**했으므로 재사용이 타당하다. 다만 상수 이름이 `BSKOREA_`로 시작해 오해를 부르므로, 5.2에서 이름 변경을 제안한다.

### 4.2 DOM 구조

9개 샘플 모두 동일하다.

```text
ul.tnav                      (상단 내비게이션 — 본문 아님)
div.main
├ div.mt                     (책 제목. 각 책 1장에만 존재)
├ div.chapterlabel#V0        (장 번호)
├ div.p                      (본문 — 장 전체가 이 블록 하나에 들어간다)
│ ├ span.verse#V1  "1&nbsp;"     <- 번호 마커
│ ├ (텍스트 노드)                 <- 1절 본문
│ ├ span.add                     <- 보충어 (본문이다)
│ ├ span.verse#V2  "2&nbsp;"
│ └ ...
├ ul.tnav                    (하단 내비게이션)
├ div.footnote               (비어 있음 — hr 하나뿐)
└ div.copyright              (Public Domain 링크)
```

관측 결과:

| 요소 | GEN01 | PSA023 | PSA119 | MRK16 | 3JN01 |
| --- | --- | --- | --- | --- | --- |
| `span.verse` | 31 | 6 | 176 | 20 | 14 |
| `div.p` | 1 | 1 | 1 | 1 | 1 |
| `span.add` | 3 | 0 | 18 | 7 | 3 |
| `div.mt` | 1 | **0** | **0** | **0** | 1 |
| `div.q1` / `div.s` / `a.notemark` | 0 | 0 | 0 | 0 | 0 |

BibleGateway와 비교하면 훨씬 단순하다.

- **시가 블록이 없다.** 시편 119편도 `div.p` 하나에 176절이 들어 있다.
- **편집자 소제목이 없다.** ASV에서 필수였던 `h3` 처리가 필요 없다.
- **각주 마커가 없다.** `div.footnote`는 존재하지만 5건 모두 비어 있다.
- **분할 절이 없다.** 한 절이 여러 노드로 쪼개지지 않는다.
- **본문 블록이 항상 `div.p` 하나다.** 율법·시가·지혜·예언·복음서·서신 9개 장에서 예외가 없었다.
- **합본 절(`1-2`)이 없다.** 마커 텍스트가 모두 순수 숫자였다.

### 4.3 함정 1. 절 본문이 스팬 안에 없다

이 소스의 핵심 차이다. BibleGateway는 절 전체가 `<span class="text">` 안에 들어 있어 노드 단위로 추출할 수 있었다.

**eBible의 `span.verse`는 번호 마커일 뿐이고, 본문은 그 뒤에 오는 형제 노드다.**

```html
<span class="verse" id="V1">1&nbsp;</span>EN el principio crió Dios los cielos y la tierra.
<span class="verse" id="V2">2&nbsp;</span>Y la tierra estaba desordenada y vacía...
```

따라서 파서는 "노드를 찾아 텍스트를 꺼내는" 방식이 아니라 **마커와 마커 사이의 텍스트를 누적하는** 방식이어야 한다. 설계는 6절에 있다.

### 4.4 함정 2. 기존 파서 체인이 조용히 틀린 결과를 낸다

이 페이지를 현재 코드에 넣으면 **실패하지 않는다.** 실제 `GEN01.htm` 전체를 넣은 결과는 아래와 같다.

```text
get_source_name() -> "generic"
파싱 결과: 31절, 절 번호 1~31 연속

  1: "1 EN el principio criÃ³ Dios los cielos y la tierra."   <- 번호 혼입 + 인코딩 깨짐
  2: "Y la tierra estaba desordenada y vacÃ­a, ..."
 31: "Y viÃ³ Dios todo lo que habÃ­a hecho, ..."
```

**절 수도 맞고 번호도 연속이다.** 정규식 폴백의 인라인 2차 패스가 절 구분에 성공하기 때문이다. 오염은 두 군데뿐이다.

- 1절 본문 맨 앞에 절 번호가 남는다
- 전 구절의 악센트가 깨진다 (5.1의 인코딩 문제)

**이것이 이 소스에서 가장 위험한 지점이다.** 실패로 드러나지 않고, 검증 3(빈 장)과 검증 4(절 연속성)를 **정상 통과**한다. 잡아내는 것은 검증 5의 `^[0-9]+\s` 패턴(1절 번호 혼입)과 8.1의 mojibake 쿼리뿐이다. 두 검증을 건너뛰면 31,000절이 조용히 오염된 채 적재된다.

시사점은 두 가지다.

- **전용 파서를 폴백 체인 앞에 넣어야 한다.** WEB·ASV와 같은 이유이지만 위험도가 다르다. 그쪽은 "0절이라 실패"였고, 여기는 "31/31로 완주하는 오답"이다.
- `get_source_name()`이 `generic`을 반환하면 `_ensure_navigation_template()`이 링크 크롤링을 시도한다. 소스 판별을 반드시 추가해야 한다.

### 4.5 함정 3. 시편 표제가 1절 본문에 포함되어 있다

```text
PSA023:1 -> "Salmo de David. JEHOVÁ es mi pastor; nada me faltará."
```

`Salmo de David.`는 표제인데 **별도 마크업 없이 1절 본문 안에 들어 있다.** WEB(`h4.psalm-title`)이나 ASV(`h4` + `h3`)처럼 태그로 분리되어 있지 않다.

이는 히브리어 성경의 절 번호 체계를 따르는 역본에서 흔한 처리다. 제거하려면 "마침표 앞부분을 표제로 간주" 같은 휴리스틱이 필요한데, 본문 첫 문장과 구분할 안전한 기준이 없다.

**결정: 그대로 저장한다.** 근거는 아래와 같다.

- 소스가 절 본문으로 제공하는 것을 임의로 잘라내면 원문 충실성이 깨진다
- WEB/ASV에서 표제를 제외한 것은 **태그로 명확히 분리되어 있었기** 때문이다. 근거가 다르면 결론도 달라야 한다
- 제거 휴리스틱은 오탐 시 본문 첫 문장을 날린다. 복구 불가능한 손실이다

다만 이 결정은 **역본 간 표현 불일치**를 만든다. 시편 23:1을 KJV/WEB/ASV와 나란히 놓으면 RV1909에만 표제가 붙는다. 이 사실을 README에 명시해야 한다.

## 5. 코드 변경 지점

### 5.1 HTTP 응답 인코딩 — 공유 코드 수정 (가장 중요)

**현재 코드로 이 소스를 수집하면 스페인어 악센트가 전부 깨진다.**

```text
r.text          -> "Salmo de David. JEHOVÃ es mi pastor"     (mojibake)
content.decode('utf-8') -> "Salmo de David. JEHOVÁ es mi pastor"  (정상)
```

원인은 응답 헤더다.

| 소스 | `Content-Type` | requests가 고르는 인코딩 |
| --- | --- | --- |
| ebible.org | `text/html` (**charset 없음**) | `ISO-8859-1` -> 깨짐 |
| bskorea.or.kr | `text/html; charset=UTF-8` | `UTF-8` |
| biblegateway.com | `text/html; charset=UTF-8` | `UTF-8` |

HTTP 표준상 `Content-Type`에 charset이 없으면 requests는 `ISO-8859-1`로 가정한다. eBible 페이지는 HTML 안에 `<meta charset="UTF-8" />`를 선언하지만 `response.text`는 이를 보지 않는다.

기존 두 소스는 헤더에 charset을 담아 보내므로 **이 결함이 지금까지 드러나지 않았다.** RV1909가 첫 노출 사례다.

권장 수정 (`scraper._request_html()`):

```python
# Content-Type에 charset이 없으면 requests는 ISO-8859-1로 가정한다.
# 그 경우에만 본문 기반 추정으로 대체한다(ebible.org는 meta charset만 선언).
content_type = response.headers.get("Content-Type", "")
if "charset=" not in content_type.lower():
    response.encoding = response.apparent_encoding or "utf-8"
html = response.text
```

이 조건이면 **charset을 선언하는 기존 소스의 동작은 전혀 바뀌지 않는다.** 헤더에 charset이 없을 때만 개입한다.

실제로 적용해 확인한 결과다.

| 소스 | 수정 전 | 수정 후 | 본문 |
| --- | --- | --- | --- |
| ebible.org | `ISO-8859-1` | `utf-8` | `JEHOVÁ es mi pastor` (정상) |
| biblegateway.com | `UTF-8` | `UTF-8` (변화 없음) | 정상 |

검증 방법은 10절에 둔다. 단위 테스트로 고정해야 하는 항목이다.

### 5.2 `scraper.py` 신규 함수

WEB·ASV와 같은 패턴으로 추가한다.

1. `_is_ebible_source()` — 호스트에 `ebible.org` 포함 여부
2. `_build_ebible_url(book_order, chapter_number)` — 4.1의 자릿수 규칙 적용
3. `_discover_chapter_urls_for_ebible(book_order)` — `KJV_CHAPTER_COUNTS` 재사용
4. `_extract_verses_from_ebible_page(soup)` — 6절
5. `get_source_name()` / `_build_chapter_url()` / `discover_chapter_urls_for_book()` 분기

엔트리 URL에서 역본 경로(`spaRV1909`)를 승계해야 한다. BibleGateway가 `version` 쿼리를 승계하는 것과 같은 이유로, 다른 eBible 역본에 재사용할 수 있게 된다.

```python
# https://ebible.org/spaRV1909/GEN01.htm -> 경로 첫 세그먼트를 역본 코드로 사용
```

#### 상수 이름 정리 제안

`BSKOREA_BOOK_CODES`를 두 소스가 공유하게 되므로 이름이 사실과 어긋난다. `USFM_BOOK_CODES`로 바꾸고 기존 이름은 별칭으로 남기거나, 한 번에 교체한다. 값은 변경하지 않는다.

이름을 그대로 두면 "bskorea 전용 상수를 왜 eBible이 쓰지?"라는 오해가 반복된다.

### 5.3 폴백 체인 삽입 위치

```text
bskorea -> biblegateway -> ebible -> bibletable -> ... -> regex fallback
```

기존 전용 파서(bskorea, biblegateway) 뒤, 범용 추론 파서 앞에 넣는다. 4.4에서 확인했듯 뒤에 두면 정규식 폴백이 먼저 성공해 잘못된 값을 만든다.

파서는 자기 소스가 아니면 `[]`를 반환해야 한다(`div.main`과 `span.verse`가 모두 없으면 즉시 반환).

### 5.4 엔트리 URL 해석과 정합성 검증

ASV 작업에서 도입한 표에 한 줄을 더한다.

```python
ENTRY_URL_ENV_BY_TRANSLATION_TYPE = {..., "RVR1909": "RVR1909_ENTRY_URL"}
TRANSLATION_TYPES_BY_LANGUAGE_CODE = {..., "es": ("RVR1909",)}
ENTRY_URL_PREFERENCE_ORDER = (..., "RVR1909")

TRANSLATION_SOURCE_REQUIREMENTS = {
    ...,
    "RVR1909": {
        "source": "ebible",
        "version": None,
        "name": "Reina Valera 1909",
        "language_code": "es",
    },
}
```

`es`는 현재 후보가 하나뿐이라 `BIBLE_LANGUAGE_CODE=es`만으로 소스가 결정된다. 다만 나중에 다른 스페인어 역본이 추가되면 영어와 같은 모호성이 생기므로, 실행 시에는 `BIBLE_TRANSLATION_TYPE`을 함께 지정하는 편이 안전하다.

`version` 개념이 없는 소스이므로 `None`으로 둔다. `thekingsbible`(KJV)과 같은 형태다.

## 6. 파서 설계

### 6.1 파싱 대상 범위

`div.main`을 기준으로 하고, 아래를 먼저 제거한다.

| 제거 대상 | 이유 |
| --- | --- |
| `ul.tnav` | 내비게이션. `Génesis`, `<`, `1`, `>` 같은 텍스트가 섞인다 |
| `div.mt` | 책 제목 (각 책 1장에만 존재) |
| `div.chapterlabel` | 장 번호 |
| `div.footnote` | 각주 영역 (현재는 비어 있음) |
| `div.copyright` | 저작권 표기 |

`div.s`, `div.ms`, `a.notemark`는 5개 샘플에서 관측되지 않았지만, 같은 렌더러가 쓰는 USFM 클래스이므로 방어적으로 제거 목록에 포함한다.

ASV의 `h3` 사례가 근거다. WEB에서 관측되지 않아 "방어적으로" 남겨둔 규칙이 ASV에서 필수 요건이 되었다. **다른 역본에 재사용될 파서라면 관측되지 않은 USFM 클래스도 미리 막아 두는 편이 옳다.**

### 6.2 절 추출 규칙

마커 사이의 텍스트를 누적한다.

1. `div.main`을 복제하고 6.1의 제거를 수행한다
2. 문서 순서로 모든 노드를 순회한다
3. `span.verse`를 만나면 `id="V{n}"`에서 절 번호를 읽고 현재 절을 전환한다
4. 텍스트 노드를 만나면 현재 절에 누적한다
   - `span.verse` 내부의 텍스트(번호 자체)는 제외한다
   - `span.add` 내부 텍스트는 **포함한다** (보충어는 본문이다)
5. 블록 요소 경계를 넘을 때만 공백 하나를 삽입한다

절 번호는 마커의 표시 텍스트가 아니라 **`id` 속성**에서 읽는다. BibleGateway에서 `chapternum`이 장 번호를 표시하던 함정과 같은 이유로, 표시 텍스트보다 구조화된 속성이 안전하다. `div.chapterlabel`이 `id="V0"`을 쓰므로 `V0`은 자연히 절에서 제외된다.

블록 경계 공백 처리는 한 절이 문단을 걸치는 경우를 위한 것이다. 블록 안에서는 원본 공백을 그대로 쓰고(구분자 없이 이어붙임), 블록이 바뀔 때만 공백을 넣는다.

**이 규칙은 9개 샘플 어디에서도 실행되지 않았다.** 모든 장이 `div.p` 하나이기 때문이다. 즉 방어 코드이며 실측으로 검증되지 않은 유일한 파싱 규칙이다.

주의할 점은 **이 규칙이 틀려도 검증 쿼리에 걸리지 않는다는 것**이다. 블록 경계에서 공백이 빠지면 `팔복이라했다`처럼 단어가 붙는데, 절 번호는 연속이고 각주·번호 잔존도 없으므로 검증 3·4·5를 모두 통과한다. 다른 eBible 역본으로 이 파서를 재사용할 때는 다중 블록 장을 찾아 별도로 확인해야 한다.

### 6.3 정규화

- `&nbsp;`(U+00A0)를 일반 공백으로 치환
- 연속 공백을 단일 공백으로 축약, 앞뒤 공백 제거
- 빈 문자열이면 해당 절 제외

### 6.4 프로토타입 검증 결과

위 설계대로 구현한 프로토타입을 실제 5개 장에 돌린 결과다.

| 샘플 | 추출 | 기대 | 연속성 |
| --- | --- | --- | --- |
| GEN01 | 31 | 31 | 정상 |
| PSA023 | 6 | 6 | 정상 |
| PSA119 | 176 | 176 | 정상 |
| MRK16 | 20 | 20 | 정상 |
| 3JN01 | 14 | 14 | 정상 |

절 번호가 본문에 섞이지 않고, `span.add`의 보충어도 유실되지 않는다.

## 7. DB 준비

### 7.1 현재 상태 (실측)

| translation_id | language_code | name | type | bible_book |
| --- | --- | --- | --- | --- |
| 27 | es | La Biblia de las Américas | LBLA | 0권 |
| 28 | es | Reina-Valera 1960 | RVR1960 | 0권 |

**RV1909에 해당하는 row가 없다.** 스페인어 row는 두 개뿐이며 둘 다 다른 역본이다.

`RVR1960`(28) 재사용은 **금지한다.** 1909년 본문을 1960년 개정판으로 표기하는 것은 데이터 오염이다. 두 역본은 본문이 다르다.

### 7.2 스키마 제약 — 먼저 확인해야 한다

`bible_translation`은 단순한 데이터 테이블이 아니다. **`translation_type`이 CHECK 제약으로 27개 값에 제한되어 있다.**

```sql
CHECK (translation_type::text = ANY (ARRAY[
  'KRV','NKRV','RNKSV','KOERV','KLB','NLTNK','NIV','ESV','KJV','NASB','NLT','CSB',
  'GNT','CEV','MSG','NRSV','AMP','HCSB','WEB','ASV','DBY','BBE','YLT',
  'LBLA','RVR1960','LUTH1545','VUL']))
```

`RVR1909`는 이 목록에 없다. 따라서 **INSERT가 바로 실패한다.**

```text
psycopg2.errors.CheckViolation: new row for relation "bible_translation"
violates check constraint "bible_translation_translation_type_check"
```

허용된 스페인어 값은 `LBLA`와 `RVR1960`뿐이며, 둘 다 다른 역본이다. 7.1에서 정한 대로 `RVR1960` 재사용은 금지이므로, **선택지는 스키마 변경뿐이다.**

이는 데이터 삽입이 아니라 DDL이며 DB 전체에 영향을 준다. 실행 주체의 승인이 필요한 항목이다.

관련 제약도 함께 확인했다.

| 제약 | 내용 | RV1909 영향 |
| --- | --- | --- |
| `translation_type` CHECK | 27개 값 허용 | **차단됨 — 추가 필요** |
| `language_code` CHECK | `ko`, `en`, `zh`, `ja`, `es`, `de`, `la` | `es` 허용, 문제없음 |
| `name` UNIQUE | 역본명 중복 불가 | 새 이름이므로 문제없음 |
| `translation_type` UNIQUE | 타입당 1개 row | 새 타입이므로 문제없음 |

#### 제약 확장 방법

기존 27개 값을 손으로 옮겨 적으면 오타 하나로 기존 역본이 막힌다. **살아 있는 제약 정의에서 값을 추출해 재생성한다.**

```sql
-- 개념: 아래를 스크립트로 수행한다
--   1. pg_get_constraintdef()로 현재 정의를 읽는다
--   2. 허용값 목록을 파싱한다
--   3. 'RVR1909'를 더해 DROP + ADD 한다
--   4. 재조회해 기존 값이 하나도 빠지지 않았는지 확인한다
ALTER TABLE public.bible_translation DROP CONSTRAINT bible_translation_translation_type_check;
ALTER TABLE public.bible_translation ADD  CONSTRAINT bible_translation_translation_type_check
  CHECK (translation_type::text = ANY (ARRAY[<기존 27개>, 'RVR1909']));
```

4번 확인 단계를 생략하면 안 된다. 파싱이 어긋나 값이 누락돼도 DDL 자체는 성공하며, 해당 역본을 다음에 적재할 때에야 드러난다.

실측 결과: 27개 -> 28개, 기존 값 유실 0건.

### 7.3 `bible_translation` row 생성

```sql
INSERT INTO public.bible_translation (language_code, translation_order, "name", translation_type)
VALUES ('es', <order>, 'Reina Valera 1909', 'RVR1909');
```

컬럼 구성은 실측으로 확인했다. `id`는 identity(`BY DEFAULT`)이므로 생략하면 자동 채번된다. `language_code`, `translation_order`, `name`, `translation_type`은 모두 `NOT NULL`이며 기본값이 없으므로 반드시 지정해야 한다.

채번된 `id`는 조회해서 쓰고, 코드에 하드코딩하지 않는다.

### 7.4 `bible_book` 66권 시드

`book_order`, `book_key`(USFM 대문자), `testament_type`은 KJV(10) 행에서 가져오고 `name`만 스페인어로 채운다.

#### 책명 수집 — `div.mt`를 단독으로 믿으면 안 된다

각 책 1장의 `div.mt`에 책 제목이 있지만, **66권 중 1권에서 원문 데이터가 어긋난다.**

| 위치 | 1 Chronicles | 2 Chronicles |
| --- | --- | --- |
| `div.mt` | `Crónicas` (틀림) | `2 Crónicas` |
| `ul.tnav` 첫 링크 | `1 Crónicas` | `2 Crónicas` |
| `<title>` | `1 Crónicas 1` | `2 Crónicas 1` |

한 권만 손으로 고치면 같은 유형의 다른 결함을 놓친다. 세 위치를 66권 전수 비교해 불일치를 확정하는 편이 옳다.

실측 결과:

- 세 위치 불일치: **1건** (위 1 Chronicles)
- `ul.tnav` 누락: 0건 -> **정본으로 채택**
- USFM 릴리스(`spaRV1909_usfm.zip`)의 `toc1`/`toc2`와 교차 검증: **66권 전부 일치, 불일치 0건**

즉 책명은 서로 독립적인 두 출처(HTML 페이지, USFM 파일)로 검증된 값이다.

#### 약어는 소스에 없다

`abbreviation` 컬럼은 `NOT NULL`인데 **eBible은 약어를 제공하지 않는다.** USFM의 `toc3`(약어) 필드가 66권 전부 비어 있고, HTML에도 약어 표기가 없다.

따라서 이 컬럼만은 소스 근거 없이 사람이 채워야 한다. 관례적인 Reina-Valera 약어(`Gn`, `Éx`, `Sal`, `Cnt`, `Ap` …)를 사용한다.

**문서화가 필요한 이유**: 다른 모든 값은 소스에서 왔지만 약어만 입력값이다. 나중에 표기를 바꾸려면 `UPDATE` 한 번이면 되고, 잘못돼도 본문 데이터와 무관하다는 점을 알고 있어야 한다.

#### 실측 결과

| 항목 | 값 |
| --- | --- |
| `translation_id` | 33 |
| `translation_order` | 31 |
| `bible_book` | 66권 (구약 39 / 신약 27) |
| 책명 출처 | eBible `ul.tnav` (USFM `toc1` 교차 검증) |
| 약어 출처 | 관례 표기 (입력값) |

### 7.5 `bible_book_description` — 언어 단위 테이블

적재 자체와는 무관하지만, 앱이 책 소개를 보여준다면 이 테이블도 채워야 한다.

```text
(language_code, book_key) UNIQUE
컬럼: author, background, content, historical_period, summary, written_year (모두 NOT NULL)
```

**키가 `translation_id`가 아니라 `language_code`다.** 따라서 역본이 아니라 **언어 단위로 한 번만** 채우면 되고, 이후 추가되는 모든 스페인어 역본(`LBLA`, `RVR1960` 등)이 같은 66행을 공유한다.

적재 전 상태는 `en` 66행, `ko` 66행, `es` 0행이었다.

#### 출처 문제

이 테이블의 내용은 성경 본문이 아니라 **편집 메타데이터**다. eBible은 이런 정보를 제공하지 않으므로 스크래핑으로 얻을 수 없다.

채택한 방법은 **기존 영어 행 66개를 스페인어로 옮기는 것**이다. 새로 쓰지 않은 이유는 `author`, `historical_period`, `written_year` 같은 사실 정보가 언어별로 어긋나면 안 되기 때문이다.

```text
창세기 저자:  en "Moses"  /  ko "모세"  /  es "Moisés"
기록 연대:    en "c. 1445–1405 BC"  ->  es "c. 1445–1405 a. C."
```

#### 검증

| 항목 | 결과 |
| --- | --- |
| `es` 행 수 | 66 / 66 |
| 설명이 없는 책 | 0건 |
| 빈 필드 | 0건 |
| mojibake | 0건 |

삽입은 `(book_key, language_code)` 기준 `NOT EXISTS` 조건이므로 재실행해도 중복되지 않는다.

## 8. 검증

WEB 설계 11.4의 검증 1~5를 `:tid`만 바꿔 그대로 쓴다.

| 검증 | 기대값 |
| --- | --- |
| 1. 절이 적재된 책 수 | 66 |
| 2. 총 장 수 | 1,189 |
| 3. 빈 장 | 0건 |
| 4. 절 번호 연속성 위반 | 9절 참고 |
| 5. 본문 오염 | 0건 |

### 8.1 인코딩 검증 — 이 소스 전용

가장 중요한 추가 검증이다. 5.1의 수정이 실제로 적용됐는지 DB에서 확인한다.

```sql
-- mojibake 탐지: UTF-8이 latin-1로 해석되면 Ã, Â 조합이 나타난다
SELECT COUNT(*) FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b    ON b.id = c.book_id
WHERE b.translation_id = :tid
  AND (v.text LIKE '%Ã%' OR v.text LIKE '%Â%');
-- 기대값: 0
```

```sql
-- 반대 방향: 스페인어 악센트가 실제로 저장됐는지
SELECT COUNT(*) FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b    ON b.id = c.book_id
WHERE b.translation_id = :tid
  AND v.text ~ '[áéíóúñÁÉÍÓÚÑ¿¡]';
-- 기대값: 수천 건 (0이면 인코딩이 깨졌거나 문자가 소실된 것)
```

두 쿼리를 **함께** 봐야 한다. 첫 번째만 보면 악센트가 통째로 사라진 경우를 놓친다.

### 8.2 KJV 대조

ASV에서 유용했던 양방향 대조를 그대로 적용한다. `translation_id`를 서로 바꿔 두 번 실행하고 아래로 분류한다.

- 두 방향에서 같은 책의 다른 장이 같은 건수로 짝을 이룸 -> **절 구분 차이**
- 한 방향에서만 나오고 짝이 없음 -> **진짜 누락 후보**

#### 실측 결과

| 방향 | 건수 |
| --- | --- |
| KJV에 있고 RVR1909에 없음 | **18건** |
| RVR1909에 있고 KJV에 없음 | **0건** |

18건은 모두 **각 장의 마지막 절**이다.

민수기 12:16, 29:40 / 사무엘상 23:29 / 사무엘하 20:26 / 역대하 33:25 / 욥기 35:16, 38:39-41, 40:20-24 / 호세아 11:12 / 요나 1:17 / 사도행전 19:41 / 고린도후서 13:14

**한 방향에서만 나왔다고 누락으로 단정하면 안 된다.** 실제 본문을 확인하면 내용은 모두 존재한다.

| 사례 | KJV | RVR1909 |
| --- | --- | --- |
| 요나 1:17 | 1장 마지막 절 | **2:1로 이동** (히브리어 절 구분) |
| 고린도후서 13:14 | 별도 절(축도) | **13:13에 병합** |
| 사도행전 19:41 | 별도 절 | 19:40에 병합 |

즉 **절 구분 차이이며 본문 손실이 아니다.** 검증 4(절 연속성)가 0건인 것과도 일관된다. 각 장이 1부터 N까지 연속이고, 다만 N이 KJV보다 작을 뿐이다.

#### 분류 기준 보완

ASV 설계 문서는 "방향2가 0이면 진짜 누락"이라고 적었지만, RVR1909가 반례다. 방향2가 0이어도 두 경우가 가능하다.

- **병합**: 두 절의 내용이 한 절에 합쳐짐 (좌표는 하나 줄지만 내용은 있음)
- **진짜 누락**: 본문 자체가 없음

구분하려면 **인접 절의 본문을 직접 확인**해야 한다. ASV의 16건은 각주가 `Some ancient authorities insert ... verse 37`처럼 명시해 누락임이 확인됐고, RVR1909의 18건은 인접 절에 내용이 있어 병합·이동임이 확인됐다.

### 8.3 경계 구절 육안 확인

- `Génesis 1:1` — 절 번호가 본문에 섞이지 않았는지
- `Salmos 23:1` — 표제 `Salmo de David.`가 포함되어 있는지 (4.5의 결정대로면 포함이 정상)
- `Salmos 119:176` — 최장 장의 마지막 절
- `3 Juan 1:14` — 단일 장 책의 마지막 절
- `Apocalipsis 22:21` — 전권 마지막 절
- 악센트가 포함된 임의의 절 — `á`, `ñ`, `¿` 등이 정상 표시되는지

## 9. 미결정 사항

### 9.1 본문 없는 절 처리

**결론: RVR1909에는 처리할 항목이 없다.** 8.2의 대조 결과 본문이 빠진 절은 0건이며, 18건의 차이는 모두 절 구분(병합·이동)이다. 따라서 `(omitted)` 마커를 넣을 대상이 없고, 검증 4도 0건이다.

아래는 결정 근거로 남긴다.

표본 2건은 실제로 확인했다. ASV와 WEB이 본문에서 빼는 절이 RV1909에는 **있다**.

| 구절 | ASV | WEB | RV1909 |
| --- | --- | --- | --- |
| 마태복음 17:21 | 없음 | 있음 | **있음** |
| 사도행전 8:37 | 없음 | `(omitted)` | **있음** |

두 장 모두 절 번호가 1부터 끝까지 연속이다(마태 17장 27절, 사도행전 8장 40절).

Textus Receptus 계열이라는 성격과 일치하며, 전권 적재 후 8.2 대조로 확정했다.

만약 구멍이 나온다면 WEB에서 채택한 기준을 따른다.

- 소스 DOM에 양성 증거가 있으면 마커 저장
- 증거가 없으면 대조로 목록을 확정한 뒤 사람이 검토해 반영

### 9.2 스페인어 책명

**결정: 옵션 B(스페인어 책명)로 적용 완료.** 수집 방법과 검증은 7.4에 있다.

## 10. 테스트 설계

inline HTML fixture 기반이며 네트워크를 타지 않는다.

필수:

- **URL 생성** — `GEN01`, `GEN50`, `PSA023`(3자리), `PSA119`, `3JN01`, `REV22`
- **자릿수 규칙** — 시편만 3자리인지, 다른 책은 2자리인지
- **소스 판별** — `get_source_name()`이 `ebible`을 반환
- **장 목록 생성** — 창세기 50, 시편 150, 유다서 1
- **절 파싱** — 마커 사이 텍스트 누적, 번호 미혼입
- **`span.add` 보존** — 보충어가 유실되지 않는지
- **내비게이션 제외** — `ul.tnav`의 `Génesis`, `<`, `>`가 절에 섞이지 않는지
- **`div.mt` 제외** — 책 제목이 1절에 붙지 않는지
- **폴백 미개입** — eBible HTML에서 정규식 폴백이 호출되기 전에 전용 파서가 반환하는지
- **다른 소스 무영향** — 기존 fixture가 그대로 통과하는지
- **인코딩** — charset 없는 응답에서 `apparent_encoding`으로 대체되는지, charset 있는 응답은 건드리지 않는지

인코딩 테스트는 `requests` 응답을 흉내 낸 가짜 객체로 작성해 네트워크 없이 검증한다. 5.1의 수정은 모든 소스가 지나는 경로이므로 회귀 방지 장치가 반드시 필요하다.

## 11. 운영 계획

### 11.1 요청 간격

`robots.txt`에 `Crawl-delay` 선언이 없다. 그렇다고 무제한으로 받아도 된다는 뜻은 아니다.

- eBible.org는 비영리 배포 사이트이며 정적 파일을 제공한다
- BibleGateway처럼 명시적 제한은 없으나, 1,189회 요청을 몰아치는 것은 예의에 어긋난다

권장: **요청 간 1~2초**. 현재 기본값(`sleep_min=0.3`, `sleep_max=1.0`)보다 약간 높인다.

- 1,189장 × 1.5초 ≈ **30분** (BibleGateway의 5시간과 대조된다)
- BibleGateway처럼 코드에 하한을 강제할 근거(사이트의 명시적 선언)는 없으므로, 생성자 기본값으로 두고 문서로 안내한다

### 11.2 대안 — 파일 다운로드

eBible은 전체 역본을 **단일 zip/USFM 파일로 배포**한다. 1,189회 요청 대신 1회 다운로드로 끝난다. 실제로 확인했다.

```text
https://ebible.org/Scriptures/spaRV1909_usfm.zip   -> 200, 약 2.4MB
```

WEB 설계 13절에서 지적한 것과 같은 트레이드오프다. 이번에는 소스 자체가 eBible이므로 더 직접적이다.

- 장점: 요청 1회, DOM 변경 리스크 없음, 결정적
- 단점: USFM 파서를 새로 만들어야 한다. HTML 파서보다 작업량이 크다

**이번 설계는 요청받은 HTML 스크래핑 방식으로 완결되게 작성했다.** 다만 전권 적재가 목적이라면 파일 기반이 우월하다는 점은 기록해 둔다. 30분이면 감내할 만한 수준이므로 HTML 방식으로 진행해도 무리는 없다.

### 11.3 실행 예

```bash
export BIBLE_TRANSLATION_TYPE=RVR1909
export BIBLE_LANGUAGE_CODE=es
export RVR1909_ENTRY_URL="https://ebible.org/spaRV1909/GEN01.htm"
python3 scrape_bible_to_db.py --entry-url "$RVR1909_ENTRY_URL" --start-book 1 --end-book 5
```

smoke test(DB 미접속):

```bash
python3 scrape_bible_to_db.py --entry-url "https://ebible.org/spaRV1909/GEN01.htm" --test-genesis1
python3 scrape_bible_to_db.py --entry-url "https://ebible.org/spaRV1909/GEN01.htm" --test-book 19 --test-chapter 119
```

시편 119편을 smoke test에 넣는 이유는 3자리 자릿수 규칙과 최장 장(176절)을 한 번에 검증하기 때문이다.

## 12. 구현 순서

1. `_request_html()` 인코딩 대체 로직 추가 + 테스트 (5.1)
2. `_is_ebible_source()`, `get_source_name()` 확장
3. `_build_ebible_url()`, `_discover_chapter_urls_for_ebible()` 구현
4. `_extract_verses_from_ebible_page()` 구현 및 체인 삽입 (5.3)
5. `BSKOREA_BOOK_CODES` 이름 정리 (5.2)
6. 단위 테스트 추가 (10절)
7. 엔트리 URL 해석 / `TRANSLATION_SOURCE_REQUIREMENTS` 확장 (5.4)
8. `bible_translation` row 생성, `bible_book` 66권 시드 (7절)
9. smoke test — 창세기 1장, 시편 119편
10. 단일 책 적재 후 검증 (인코딩 검증 포함)
11. 구간 분할로 전권 적재
12. 검증 1~5 + 8.1 인코딩 + 8.2 KJV 대조
13. 9절 미결정 사항 결정 및 반영
14. README / CLAUDE.md 갱신

1번을 먼저 하는 이유는, 인코딩이 깨진 채 적재하면 전권을 다시 받아야 하기 때문이다.

## 13. 리스크

### 리스크 1. 인코딩 회귀

가장 비용이 큰 실패다. 깨진 채 적재하면 31,000절을 다시 받아야 한다.

대응: 12절 1번을 선행하고, 단일 책 적재 직후 8.1 쿼리를 돌린다. 전권 적재는 그 이후에 시작한다.

### 리스크 2. 전용 파서 없이 적재

4.4에서 확인했듯 기존 체인은 실패하지 않고 틀린 값을 만든다. 파서 없이 실행하면 오염을 눈치채기 어렵다.

대응: 소스 판별과 파서를 함께 넣는다. 소스 판별만 있고 파서가 없으면 URL은 맞고 본문은 틀린 최악의 조합이 된다.

### 리스크 3. 관측되지 않은 USFM 클래스

5개 샘플에 시가 블록·소제목·각주가 없었다고 66권 전체에 없다는 보장은 없다. RV1909는 시편도 산문 블록으로 렌더링하므로 가능성은 낮지만 단정할 수 없다.

대응: 6.1에서 USFM 클래스를 미리 제거 목록에 넣는다. 적재 후 검증 5(본문 오염)로 잔존물을 잡는다.

### 리스크 4. 잘못된 번역본으로 적재

`RVR1960`(28) row가 이미 존재하므로, 실수로 그쪽에 적재할 여지가 있다.

대응: 5.4의 표에 `RVR1909`를 등록해 정합성 검증이 양방향으로 막게 한다. `translation_type='RVR1960'`으로 eBible 소스를 실행하면 오류로 중단된다.

## 14. 결론

eBible RV1909는 **URL 규칙이 결정적이고 DOM이 단순한** 소스다. BibleGateway보다 파싱이 쉽다.

핵심 작업은 세 가지다.

- **응답 인코딩 처리 수정** — 공유 코드이며, 고치지 않으면 스페인어 본문이 전부 깨진다
- **마커 사이 텍스트를 누적하는 전용 파서** — 절 본문이 스팬 안에 없는 구조 때문이다
- **`bible_translation` row 생성** — 다른 소스와 달리 대상 역본이 DB에 아직 없다

시편 표제를 절 본문에 포함하는 결정(4.5)은 WEB·ASV와 다른 처리이므로, 역본 간 비교 기능이 있다면 미리 인지해야 한다.
