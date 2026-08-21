# eBible.org SBLM(Santa Biblia libre para el mundo) 본문 스크래핑 개발 설계

## 1. 목적

`https://ebible.org/spablm/` 의 스페인어 성경 **Santa Biblia libre para el mundo**(이하 SBLM) 창세기~요한계시록 66권 전체를 스크래핑하여 기존 PostgreSQL 스키마(`bible_chapter`, `bible_verse`)에 적재한다.

### 1.1 원본 요청을 이 설계가 어떻게 해석했는가

이 문서의 최초 요청은 **독립 실행형 크롤러**(자체 재시도·진행률·resume를 구현하고 `spablm_bible.json` 또는 `bible.sqlite`로 출력)였다. 그러나 이 저장소에는 이미 동일한 일을 하는 파이프라인이 있고, 직전 작업에서 **eBible.org 어댑터까지 붙어 RV1909 66권 적재를 완료**했다.

따라서 이 설계는 새 프로그램을 만들지 않고 **기존 파이프라인에 역본 하나를 추가**하는 방향으로 잡는다. 요청 항목이 어디에 대응되는지는 [10. 원본 요청 항목 대응표](#10-원본-요청-항목-대응표)에 정리했다. 요약하면 **출력 형식(JSON/SQLite)을 제외한 전 항목이 이미 구현되어 있고**, 출력 형식은 이 저장소의 목적(PostgreSQL 적재)과 상충하므로 채택하지 않는다.

### 1.2 라이선스와 "초안" 표기 — 이 소스의 가장 큰 특징

페이지 하단 `div.copyright` 실측:

```
Este es un borrador de traducción. Está siendo revisado y editado.
Si encuentra algún error, infórmenos en ...  Public Domain
```

- 저작권은 **Public Domain**이므로 수집·적재에 법적 제약이 없다.
- 그러나 본문은 **차기 개정이 예정된 초안(borrador)**이다. eBible.org는 원본이 갱신되면 HTML을 재생성한다.

이 저장소의 삽입은 **missing-only**(이미 있는 절은 건드리지 않음)라서, **초안이 나중에 수정되어도 재실행으로는 반영되지 않는다.** 이것은 버그가 아니라 멱등성 계약의 결과다. 대응은 [9.3 초안 갱신 문제](#93-초안-갱신-문제--missing-only-삽입의-한계)에 기술한다. RV1909(확정된 1909년 판본)와 근본적으로 다른 성격이므로, **적재 여부 자체를 판단할 때 먼저 고려해야 한다.**

### 1.3 기존 소스와의 관계

| 항목 | RV1909 (구현 완료) | SBLM (이 문서) |
| --- | --- | --- |
| 사이트 | ebible.org | ebible.org (동일) |
| 역본 코드(경로 첫 세그먼트) | `spaRV1909` | `spablm` |
| 언어 | es | es (동일) |
| 본문 성격 | 확정 판본(1909) | **개정 중 초안** |
| 렌더러 | Haiola/USFM → HTML | 동일 |

같은 렌더러이므로 URL 규칙과 절 마커 구조는 동일하지만, **USFM 태그 사용 폭이 훨씬 넓다.** 그 차이가 파서 수정을 강제했다([4.3](#43-함정-1-절-사이-표제가-앞-절에-섞여-들어간다)).

---

## 2. 결론 먼저

1. **URL 규칙 변경 불필요.** `_build_ebible_url()`은 엔트리 URL 경로의 첫 세그먼트를 역본 코드로 사용하므로, 엔트리 URL만 `https://ebible.org/spablm/GEN01.htm`으로 주면 66권 전 URL이 그대로 생성된다. 66권 × (첫 장·끝 장) 프로브 결과 **실패 0건**.
2. **소스 판별 변경 불필요.** `_is_ebible_source()`는 netloc 기준이라 `spablm`도 `ebible`로 판정된다.
3. **파서는 수정이 필요했다.** 최초 판단은 "수정 불필요"였으나 오판이었다. RV1909에 없던 `div.d`(시편 표제·이합체 표제)와 `div.sp`(화자 표시)가 **절과 절 사이**에 나타나 앞 절 본문에 섞여 들어간다. 실측 오염: **시편 119편 21개 절, 아가 1장 8개 절**([4.3](#43-함정-1-절-사이-표제가-앞-절에-섞여-들어간다)).
4. **블록 경계 공백 규칙이 여기서 처음 실제로 필요해진다.** RV1909는 장당 `div.p`가 1개라 한 번도 발동하지 않았지만, SBLM은 산문 장이 `div.p` 7~19개, 시가 장이 `div.q`/`div.q2` 수십 개로 쪼개져 있다. 한 절이 두 블록에 걸치는 사례를 실측했다(창세기 3:13).
5. **`bible_book_description`은 추가 작업이 없다.** 이 테이블은 `(book_key, language_code)` 키이고 `es` 66행이 RV1909 작업에서 이미 적재됐다.
6. **정합성 검증에 구멍이 있다.** `TRANSLATION_SOURCE_REQUIREMENTS`의 `version`은 **쿼리스트링에서만** 읽는데 eBible은 역본 코드를 **경로**에 둔다. RV1909와 SBLM 모두 `source="ebible", version=None`이 되어 마지막 방어선이 무력화된다. **SBLM 추가 전에 반드시 고쳐야 한다**([5.4](#54-정합성-검증의-구멍--version이-쿼리스트링에서만-온다)).
7. `bible_translation.translation_type` CHECK 제약에 **29번째 값 `SBLM`** 추가가 필요하다(현재 28개, 실측).
8. **책명을 `div.mt`에서 가져오면 안 된다.** 66권 전수 조사 결과 서수가 빠져 **17권이 8개 이름으로 충돌**한다(`1SA`/`2SA` 모두 `Samuel`). 예레미야는 오타(`Jeramías`)까지 있다([6.4](#64-bible_book-66권-시드)).
9. **미결정: 시편 표제(`div.d`)를 버릴 것인가.** SBLM은 표제를 1절 마커 **앞**의 별도 블록에 두어 파서가 이를 버린다. 반면 이미 적재된 RV1909는 같은 표제를 **1절 본문에 포함**하고 있다. 방치하면 같은 언어의 두 역본이 시편 23:1에서 서로 다른 내용을 담는다([4.7](#47-미결정-시편-표제를-버릴-것인가)).

---

## 3. 실측 검증 범위

이 문서의 모든 구조 주장은 실제 페이지를 받아서 확인했다. 추정으로 쓴 문장은 없다.

| 검증 | 방법 | 결과 |
| --- | --- | --- |
| URL 규칙 | 66권 × 1장/마지막 장 = 132개 HEAD/GET | 실패 0건 |
| 장 번호 패딩 | `PSA23.htm` vs `PSA023.htm` | 전자 404, 후자 200 |
| 파싱 정확도 | 8개 장 표본 파싱 | 아래 표 |
| 표제 오염 | 수정 전/후 파서 결과 diff | 시편 119편 21건, 아가 1장 8건 |
| RV1909 회귀 | RV1909 9개 장 재파싱 | 변화 없음 |
| 인코딩 | `div.copyright`, `div.mt`, 본문 악센트 | 정상(`Génesis`, `Jehová`) |
| 책명 | 66권 1장 전수 조회 → `div.mt`/`ul.tnav`/RV1909 대조 | `div.mt` 사용 불가([7.5](#75-책명-교차-검증-결과)) |
| DB 현황 | `bible_translation`/`bible_book`/CHECK 제약 조회 | [6.1](#61-현재-상태-실측) |

표본 파싱 결과(수정 후):

| 장 | 절 수 | 연속성 | 관측된 특징 클래스 |
| --- | --- | --- | --- |
| `GEN01` | 31 | 1~31 | `div.p`×9, `a.notemark`×2 |
| `GEN03` | 24 | 1~24 | `div.p`×15, `div.q`×10, `div.q2`×13 |
| `PSA023` | 6 | 1~6 | `div.d`×1, `div.q`×8, `div.q2`×8 |
| `PSA119` | 176 | 1~176 | **`div.d`×22**, `div.q`×176 |
| `SNG01` | 17 | 1~17 | **`div.sp`×9**, `div.b`×1 |
| `MRK01` | 45 | 1~45 | **`span.wj`×6**, `a.notemark`×6 |
| `ISA40` | 31 | 1~31 | `div.b`×7, `div.q2`×64 |
| `3JN01` | 14 | 1~14 | `div.p`×7 |

8개 표본 모두 **1번부터 연속**이고 표제 오염 0건이다.

---

## 4. 대상 페이지 특성

### 4.1 URL 규칙 — RV1909와 동일

```
https://ebible.org/spablm/{USFM대문자}{장번호}.htm
```

장 번호는 **책별 자릿수로 0 패딩**한다. 총 장 수가 100 이상인 책(시편)만 3자리, 나머지는 2자리다.

```
https://ebible.org/spablm/GEN01.htm    창세기 1장
https://ebible.org/spablm/PSA023.htm   시편 23편   (PSA23.htm 은 404)
https://ebible.org/spablm/3JN01.htm    요한3서
```

기존 구현이 그대로 적용된다:

```python
@staticmethod
def _build_ebible_chapter_segment(book_order: int, chapter_number: int) -> str | None:
    ...
    width = 3 if chapter_count >= 100 else 2
    return f"{USFM_BOOK_CODES[book_order - 1].upper()}{chapter_number:0{width}d}"
```

역본 코드는 하드코딩되어 있지 않다:

```python
def _get_ebible_translation_code(self) -> str:
    """First path segment of the entry URL, e.g. ".../spaRV1909/GEN01.htm"."""
```

엔트리 URL이 `.../spablm/GEN01.htm`이면 이 함수가 `spablm`을 반환한다. **URL 관련 코드 변경은 0줄이다.**

### 4.2 DOM 구조 — RV1909와 다른 점

공통 골격은 같다.

```html
<div class="main">
  <div class="mt">Génesis</div>
  <div class="chapterlabel">1</div>
  <div class="p">
    <span class="verse" id="V1">1&#160;</span>본문...
    <span class="verse" id="V2">2&#160;</span>본문...
  </div>
</div>
```

절 번호는 `span.verse`의 `id`(`V12`)에서 읽고, **본문은 마커 안이 아니라 마커 뒤 형제 노드**에 있다. 기존 파서가 마커 **사이**의 텍스트를 누적하는 이유다.

차이는 다음과 같다.

| 클래스 | RV1909 | SBLM | 처리 |
| --- | --- | --- | --- |
| `div.p` | 장당 정확히 1개 | 산문 7~19개, **시가 장은 0개** | 블록 경계 공백 필요 |
| `div.q` / `div.q2` | 미관측 | 시가 장 전반(시편 119편 176개) | 블록 경계 공백 필요 |
| `div.b` | 미관측 | 연 구분(빈 줄) | 텍스트 없음, 무해 |
| `div.d` | 미관측 | 시편 표제(1절 앞) · 이합체 표제(절 사이) | **절 사이는 제거 필요**, 1절 앞은 [4.7](#47-미결정-시편-표제를-버릴-것인가) |
| `div.sp` | 미관측 | 아가 화자 표시 | **제거 필요** |
| `a.notemark`+`span.popup` | 관측 | 관측(더 빈번) | 이미 제거 대상 |
| `span.wj` | 미관측 | 예수 말씀 | **유지해야 함** |
| `span.add` | 미관측 | 미관측 | — |
| `ul.tnav` 책명 | 대문자 | 대문자(`GÉNESIS`) | 제거 대상. 책명 대조용으로만 사용 |
| `div.mt` 책명 | 혼합, 역대상만 결함 | 혼합, **17권 서수 누락 + 오타 1건** | 제거 대상. **책명 출처로 사용 금지**([6.4](#64-bible_book-66권-시드)) |

### 4.3 함정 1. 절 사이 표제가 앞 절에 섞여 들어간다

**이 문서에서 가장 중요한 항목이다. 최초에 "파서 수정 불필요"로 판단했으나 오판이었다.**

`div.d`(시편 표제·이합체 문자 표제)와 `div.sp`(화자 표시)는 **절 마커를 동반하지 않는 블록**이다. 파서는 마커 사이의 모든 텍스트를 현재 절에 누적하므로, 제거하지 않으면 이 표제가 **직전 절의 본문**이 된다.

수정 전/후 파서 결과를 diff한 실측:

```
[PSA119] verses=176 contaminated=21 -> [8, 16, 24, 32, ... 160, 168]
   8절 꼬리:  '...é; no me abandones del todo.' + ' BET'
   16절 꼬리: '...me olvidaré de tus palabras.' + ' GUÍMEL'

[SNG01]  verses=17  contaminated=8  -> [1, 4, 7, 10, 11, 14, 15, 16]
   1절 꼬리:  '...ares, el cual es de Salomón.' + ' Amado'
```

시편 119편은 8절 간격의 히브리 알파벳 표제 22개 중 **21개**가 앞 절 끝에 붙는다(첫 표제만 1절 앞이라 무해).

아가 1장은 더 나쁘다. 화자 표시가 **절 중간**에 들어가 본문을 갈라놓는다.

```
4절 정상: ... más que del vino. Con razón te aman.
4절 오염: ... s que del vino. Amado Con razón te aman.
```

**이 오염은 자동 검증을 전부 통과한다.** 절 수도 맞고, 번호도 1부터 연속이고, 빈 절도 없다. 육안 대조 없이는 잡히지 않는다. CLAUDE.md가 경고하는 "조용히 틀린 결과"의 전형이다.

### 4.4 함정 2. 각주 본문이 절 텍스트 안에 있다

```html
<a class="notemark" href="#FN1">*</a><span class="popup">각주 본문</span>
```

각주 마커와 **각주 본문이 절 텍스트 안에 인라인**으로 들어간다. `a.notemark`만 지우고 `span.popup`을 남기면 각주 문장이 본문에 섞인다. 기존 셀렉터가 `a.notemark, span.notemark`를 제거하며 그 자식인 `span.popup`도 함께 사라지므로 현재 구현은 안전하다. **단, 셀렉터를 "정리"하면서 마커만 남기고 본문을 놓치는 변경은 금지한다.**

### 4.5 함정 3. 블록 경계 공백 규칙이 여기서 처음 실제로 쓰인다

기존 파서에는 블록 태그를 지날 때 공백을 하나 넣는 로직이 있다.

```python
elif node.name in EBIBLE_BLOCK_TAGS and current is not None:
    block_changed = True
```

RV1909는 장당 `div.p`가 1개라 **이 코드가 한 번도 발동하지 않았다.** SBLM은 한 절이 두 블록에 걸치는 경우가 흔하다(창세기 3:13은 `div.p` 두 개에 걸침). 이 규칙이 없으면 다음처럼 단어가 붙는다.

```
정상: ... ¿Qué es lo que has hecho? Y dijo la mujer ...
누락: ... ¿Qué es lo que has hecho?Y dijo la mujer ...
```

**즉, 이 소스는 기존 코드의 미검증 경로를 처음으로 실전 검증하는 역할을 한다.** 테스트를 반드시 추가한다([8. 테스트 설계](#8-테스트-설계)).

### 4.6 유지해야 하는 것 — `span.wj`

`span.wj`는 **예수의 말씀**을 표시하는 서식 태그다. 마가복음 1장에서 6개 관측됐다. 제거 대상이 아니라 **텍스트를 살려야 하는** 태그다. 제거 셀렉터에 절대 넣지 않는다. 파서는 태그를 구분하지 않고 텍스트 노드를 누적하므로 별도 처리 없이 그대로 보존된다.

### 4.7 미결정. 시편 표제를 버릴 것인가

`div.d`는 **두 가지 역할을 겸한다.** 이 구분이 [4.3](#43-함정-1-절-사이-표제가-앞-절에-섞여-들어간다)의 결론을 좁힌다.

| 위치 | 내용 | 실측 |
| --- | --- | --- |
| 1절 마커 **앞** | 시편 표제(`Salmo de David.`) | 표본 8편 전부 |
| 절 **사이** | 이합체 문자 표제(`ALEF`, `BET` …) | 시편 119편에만 21개 |

표본 9편(3·23·51·60·90·102·119·120·145) 조사 결과, **시편 119편을 제외한 모든 `div.d`는 1절 마커 앞에 있다.** 파서는 첫 마커 이전 텍스트를 누적하지 않으므로(`current is None`), 이 표제들은 **셀렉터에 넣지 않아도 어차피 버려진다.** 즉 [5.1](#51-scraperpy--제거-셀렉터-확장-유일한-파서-변경)의 셀렉터 확장이 표제를 새로 잃게 만든 것은 아니다.

**문제는 RV1909와의 불일치다.** RV1909는 같은 표제를 별도 블록이 아니라 **1절 본문 안에** 담고 있어서 이미 적재되어 있다.

```
[RV1909 실측]
  시편 3:1   'Salmo de David, cuando huía de delante de Absalom su hijo. ¡OH Jehová, ...'
  시편 23:1  'Salmo de David. JEHOVÁ es mi pastor; nada me faltará.'
  시편 51:1  'Al Músico principal: Salmo de David, cuando después que entró á Bathse...'
[SBLM 현재 파서]
  시편 23:1  'Yahvé es mi pastor; nada me faltará.'      ← 표제 없음
```

같은 `language_code='es'`인 두 역본이 시편 23:1에서 서로 다른 내용을 담게 된다. **이 차이는 [7](#7-검증)의 어떤 검증도 통과한다.** 절 수도 번호도 정상이기 때문이다.

| 안 | 내용 | 평가 |
| --- | --- | --- |
| A | 그대로 버린다 | SBLM의 편집 의도(표제=제목)에 충실. 그러나 RV1909와 조용히 어긋나고, 나중에 비교하는 사람은 스크래핑 실패로 오인한다 |
| **B** | **1절 마커 앞의 `div.d`만 1절 본문 앞에 붙인다** | RV1909와 표현이 일치. 절 사이 `div.d`(이합체 표제)는 그대로 제거하므로 [4.3](#43-함정-1-절-사이-표제가-앞-절에-섞여-들어간다)의 오염과 충돌하지 않는다 |
| C | 별도 컬럼/테이블에 표제 저장 | 스키마 변경. 범위 초과 |

**B를 권고한다.** WEB 적재 때 원문에 없는 절을 조용히 건너뛰지 않고 `(omitted)`로 명시하기로 한 판단과 같은 방향이다 — **내용을 말없이 잃지 않는다.**

B의 구현은 파서에 위치 조건을 하나 더 넣는 것이다. 현재는 `div.d`를 무조건 제거하지만, **첫 `span.verse`보다 앞선 `div.d`는 남겨 1절의 선행 텍스트로 누적**시키면 된다. 다만 `current is None` 구간의 텍스트를 버리는 현재 동작은 메뉴·표제를 걸러내는 안전장치이므로, 예외는 `div.d` 한정으로 좁혀야 한다.

> 이 항목은 본문 내용을 바꾸는 결정이라 **적재 전에 합의가 필요하다.** 적재 후 방침을 바꾸면 missing-only 삽입 때문에 재적재를 해야 한다([9.3](#93-초안-갱신-문제--missing-only-삽입의-한계)).

---

## 5. 코드 변경 지점

### 5.1 `scraper.py` — 제거 셀렉터 확장 (유일한 파서 변경)

```python
EBIBLE_REMOVABLE_SELECTOR = (
    "ul.tnav, div.mt, div.mt1, div.mt2, div.mt3, "
    "div.ms, div.ms1, div.s, div.s1, div.s2, div.sr, div.mr, div.r, "
    # Headings that appear BETWEEN verses: a psalm/acrostic title (div.d, div.qa) or a
    # speaker label (div.sp). They carry no verse marker, so the accumulator folds them
    # into the surrounding verse (spablm Psalms 119 leaks 21, Song of Songs 1 leaks 8).
    "div.d, div.qa, div.qd, div.sp, "
    "div.chapterlabel, div.footnote, div.copyright, div.navbar, "
    # The footnote marker nests the note body in span.popup, inside the verse text.
    "a.notemark, span.notemark, span.footnote, span.crossref"
)
```

추가 항목의 근거:

| 추가 | 근거 |
| --- | --- |
| `div.d`, `div.sp` | **실측 오염 확인**([4.3](#43-함정-1-절-사이-표제가-앞-절에-섞여-들어간다)) |
| `div.qa`, `div.qd` | 동일 성격의 USFM 표제(이합체 표제/시편 후기). 미관측이나 같은 렌더러가 방출 |
| `div.mt3`, `div.sr`, `div.mr`, `div.r` | 기존 `mt/ms/s` 계열의 누락된 형제. 모두 표제·참조 |

`div.q`, `div.q2`, `div.b`는 **제거하지 않는다.** 시가체 본문을 담는 블록이므로 지우면 본문이 사라진다.

### 5.2 `scraper.py` — URL·소스 판별은 변경 불필요

`_is_ebible_source()`(netloc 기준), `_get_ebible_translation_code()`(경로 첫 세그먼트), `_build_ebible_chapter_segment()`, `_discover_chapter_urls_for_ebible()`, 폴백 체인 내 위치 — **전부 그대로 동작한다.** 실행으로 확인했다.

```
source = ebible | code = spablm
sleep floor = 1.0 2.0
```

### 5.3 `scrape_bible_to_db.py` — 역본 등록

CLAUDE.md의 "Adding a new source" 6~8번에 해당한다. 소스는 이미 있으므로 **역본 등록만** 하면 된다.

```python
ENTRY_URL_ENV_BY_TRANSLATION_TYPE = {
    ...,
    "SBLM": "SBLM_ENTRY_URL",
}

TRANSLATION_TYPES_BY_LANGUAGE_CODE = {
    ...,
    "es": ("RVR1909", "SBLM"),
}

ENTRY_URL_PREFERENCE_ORDER = ("NKRV", "KJV", "WEB", "ASV", "RVR1909", "SBLM")

TRANSLATION_SOURCE_REQUIREMENTS = {
    ...,
    "SBLM": {
        "source": "ebible",
        "version": "spablm",          # 5.4 참조
        "name": "Santa Biblia libre para el mundo",
        "language_code": "es",
    },
}
```

`scraper.py`에 기본 엔트리 URL 상수도 추가한다.

```python
DEFAULT_EBIBLE_SBLM_ENTRY_URL = "https://ebible.org/spablm/GEN01.htm"
```

`resolve_default_entry_url()`과 `_translation_type_hint()`는 위 세 상수를 그대로 참조하므로 **함수 본문 수정은 필요 없다.** 코드를 읽어 확인했다.

다만 부작용이 하나 있다. `TRANSLATION_TYPES_BY_LANGUAGE_CODE["es"]`가 둘이 되면, `RVR1909_ENTRY_URL`과 `SBLM_ENTRY_URL`이 **둘 다 설정된 상태에서 `BIBLE_LANGUAGE_CODE=es`만 주면 예외**가 난다.

```
ValueError: Ambiguous entry URL: BIBLE_LANGUAGE_CODE='es' matches
            RVR1909_ENTRY_URL, SBLM_ENTRY_URL.
            Set BIBLE_TRANSLATION_TYPE or pass --entry-url explicitly.
```

영어(`KJV`/`WEB`/`ASV`)에서 이미 겪은 것과 같은 동작이며, **추측으로 고르는 것보다 낫다.** README에 스페인어도 같은 조건이 됨을 명시한다.

### 5.4 정합성 검증의 구멍 — `version`이 쿼리스트링에서만 온다

**SBLM을 추가하기 전에 반드시 고쳐야 하는 결함이다.**

`validate_source_translation_compatibility()`는 `version`을 엔트리 URL의 **쿼리스트링**에서만 읽는다.

```python
query_params = dict(parse_qsl(parsed_entry.query, keep_blank_values=True))
version = query_params.get("version")          # BibleGateway 전용 가정
```

`?version=WEB` / `?version=ASV`를 쓰는 BibleGateway에는 맞지만, **eBible은 역본 코드를 경로에 둔다.** 그래서 RV1909와 SBLM 모두 `version=None`이 되고, 후보를 첫 일치로 고르는 아래 함수가 **항상 먼저 선언된 역본을 반환**한다.

```python
def _expected_translation_type(source_name: str, version: str | None) -> str | None:
    for translation_type, requirement in TRANSLATION_SOURCE_REQUIREMENTS.items():
        if requirement["source"] != source_name:
            continue
        required_version = requirement["version"]
        if required_version is None or required_version == version:
            return translation_type      # ← 첫 일치 반환
    return None
```

결과적으로 **SBLM URL로 실행해도 기대 역본이 `RVR1909`로 판정**된다. 정상적인 SBLM 적재가 오류로 막히거나, 선언 순서를 바꾸면 반대로 RV1909 적재가 막힌다. 어느 쪽이든 "마지막 방어선"이 무력화된다.

수정 방향: `version`을 URL에서 직접 파싱하지 말고 **스크레이퍼에게 묻는다.**

```python
# scraper.py
def get_source_version(self) -> str | None:
    """Source-specific version token used for translation compatibility checks."""
    if self._is_ebible_source():
        return self._get_ebible_translation_code()      # spaRV1909 / spablm
    query = dict(parse_qsl(urlparse(self.entry_url or "").query))
    return query.get("version")
```

```python
# scrape_bible_to_db.py
version = scraper.get_source_version()
```

그리고 `TRANSLATION_SOURCE_REQUIREMENTS["RVR1909"]["version"]`을 `None` → `"spaRV1909"`로 바꾼다. 기존 RV1909 엔트리 URL에서 이 함수가 `spaRV1909`를 반환하므로 **하위 호환이 유지된다.** 비교는 대소문자 무시로 한다(`spaRV1909`는 혼합 대소문자).

> 이 수정은 CLAUDE.md의 "Adding a new source" 7번(양방향 검증)을 **같은 소스에서 역본이 둘 이상 나오는 경우**로 확장하는 것이다. 문서에도 반영한다.

### 5.5 상수 정리

`DEFAULT_EBIBLE_TRANSLATION_CODE = "spaRV1909"`는 엔트리 URL에 경로가 없을 때만 쓰이는 폴백이다. 역본이 둘이 되면 "기본값이 RV1909"라는 암묵 가정이 위험하므로, 폴백을 없애고 **경로 세그먼트가 없으면 예외**로 바꾸는 편이 안전하다. 필수는 아니며 [12. 리스크](#12-리스크)에 남긴다.

---

## 6. DB 준비

### 6.1 현재 상태 (실측)

```
[bible_translation]           28행 (id 1~6, 10~30, 33)
  27 | LBLA    | La Biblia de las Américas | es
  28 | RVR1960 | Reina-Valera 1960         | es
  33 | RVR1909 | Reina Valera 1909         | es   <- 본문 적재 완료
[translation_type CHECK]      28개 값, 'SBLM' 없음
[bible_book_description]      en 66 / es 66 / ko 66
[bible_book]                  translation_id 1, 2, 10, 22, 23, 33 각 66권
```

SBLM용 `bible_translation` 행과 `bible_book` 66행이 **모두 없다.** 스크래퍼는 두 테이블을 **읽기 전용**으로 다루므로(CLAUDE.md 계약), 적재 전에 별도 시드가 필요하다.

### 6.2 `translation_type` CHECK 제약 — 29번째 값

```sql
-- 현재 28개 값만 허용. 'SBLM' 삽입은 bible_translation_translation_type_check 위반.
```

RV1909 때와 동일한 절차를 따른다.

1. `pg_get_constraintdef()`로 **현재 정의를 프로그램으로 읽어** 값 목록을 추출한다. 손으로 다시 타이핑하지 않는다.
2. 목록에 `'SBLM'`을 더해 제약을 재생성한다.
3. 재생성 후 값 개수가 **28 → 29**인지, 기존 28개가 모두 남았는지 확인한다.

> RV1909 때 이 절차로 27 → 28을 검증했다. 값 목록을 수기로 옮기면 기존 역본이 조용히 사라진다.

### 6.3 `bible_translation` row

```sql
INSERT INTO bible_translation (translation_type, name, language_code)
VALUES ('SBLM', 'Santa Biblia libre para el mundo', 'es');
```

- `id`는 identity BY DEFAULT이므로 **지정하지 않는다.**
- `name`, `translation_type`에 UNIQUE 제약이 있다. 기존 `es` 역본(`LBLA`, `RVR1960`, `RVR1909`)과 충돌하지 않는다.
- `language_code` CHECK(`ko,en,zh,ja,es,de,la`)에 `es`는 이미 허용된다.

### 6.4 `bible_book` 66권 시드

**`div.mt`를 책명 출처로 쓰면 안 된다.** RV1909 때는 역대상 한 권만 결함이었지만, SBLM에서는 66권 전수 조사 결과 **17권이 8개 이름으로 충돌**한다. 서수(1/2/3)가 통째로 빠지기 때문이다.

```
'Samuel'            <- 1SA, 2SA
'Reyes'             <- 1KI, 2KI
'Crónicas'          <- 1CH, 2CH
'Corintios'         <- 1CO, 2CO
'Tesalonicenses'    <- 1TH, 2TH
'Timoteo'           <- 1TI, 2TI
'San Pedro Apóstol' <- 1PE, 2PE
'San Juan Apóstol'  <- 1JN, 2JN, 3JN
```

게다가 예레미야의 `div.mt`는 **오타**다(`Jeramías`, `ul.tnav`는 `JEREMÍAS`). 초안이라는 성격이 메타데이터에도 드러난다.

`ul.tnav`는 **66권 전부 고유**하고 서수도 온전하지만 대문자다(`1 SAMUEL`, `GÉNESIS`).

**권고: 이미 적재된 RV1909(`translation_id=33`)의 스페인어 책명 66개를 그대로 재사용하고, `ul.tnav`는 책 식별이 어긋나지 않았는지 확인하는 용도로만 쓴다.** 같은 언어이고 이미 검증된 값이며, 표기도 더 정제되어 있다(`Marcos` / `Apocalipsis` vs `SAN MARCOS` / `EL APOCALIPSIS`). 대안으로 `ul.tnav`를 타이틀 케이스로 변환해 쓸 수 있으나, 그러면 스페인어 역본 간 책명 표기가 갈린다.

실측 교차 검증 결과는 [7.5](#75-책명-교차-검증-결과)에 있다.

`book_key`는 기존 역본과 동일한 USFM 코드(`GEN`, `PSA`, `3JN` …)를, `book_order`는 1~66을 쓴다. 약어(`abbreviation`)는 소스에 없으므로 RV1909와 동일한 값을 재사용한다.

### 6.5 `bible_book_description` — 추가 작업 없음

이 테이블은 `(book_key, language_code)` 키다. **`translation_id`가 아니다.**

```
[bible_book_description by language]  en 66 / es 66 / ko 66
```

`es` 66행이 RV1909 작업에서 이미 적재되어 있고, SBLM도 `language_code='es'`이므로 **그대로 재사용된다. 신규 삽입은 0행이다.**

---

## 7. 검증

### 7.1 구조 검증 (전 소스 공통)

적재 후 다음을 확인한다. 쿼리는 WEB 설계 문서 11.4와 동일하다.

1. 66권 전부 적재
2. 장 수 합계 **1,189**
3. 절이 0개인 장 없음
4. 각 장의 절 번호가 **1부터 연속**
5. 본문 오염 없음(메뉴/각주/표제 문자열 검색)

### 7.2 인코딩 검증 — 이 소스 필수

eBible은 `Content-Type`에 charset을 선언하지 않고 `<meta>`에만 UTF-8을 둔다. `_request_html()`의 `apparent_encoding` 재디코딩이 없으면 **모든 스페인어 악센트가 깨진다.**

```sql
-- 깨짐 문자(U+FFFD) 및 전형적 mojibake 패턴 검출
SELECT COUNT(*) FROM bible_verse v ... WHERE v.text LIKE '%' || U&'\FFFD' || '%'
   OR v.text LIKE '%Ã%' OR v.text LIKE '%Â%';   -- 기대값 0
-- 악센트가 실제로 들어왔는지 (역방향 확인)
SELECT COUNT(*) ... WHERE v.text ~ '[áéíóúñÁÉÍÓÚÑ¡¿]';  -- 0이면 실패
```

두 방향을 **모두** 확인한다. 앞 쿼리만으로는 "악센트가 전부 사라진" 실패를 잡지 못한다.

### 7.3 표제 오염 회귀 검증 — 이 소스 필수

[4.3](#43-함정-1-절-사이-표제가-앞-절에-섞여-들어간다)의 오염은 구조 검증을 전부 통과하므로 **전용 쿼리가 필요하다.**

시편 119편의 표제 22개는 실측한 값을 그대로 쓴다. 추정으로 적으면 검증이 통과해도 의미가 없다(초안 작성 시 `DÁLET`을 `DALET`, `VAV`를 `VAU`로 잘못 적어 두 개를 놓칠 뻔했다).

```sql
-- 1) 히브리 알파벳 표제가 절 끝에 남았는지 (시편 119편, 기대값 0행)
SELECT v.verse_number, RIGHT(v.text, 24) FROM bible_verse v ...
WHERE b.book_key = 'PSA' AND c.chapter_number = 119
  AND v.text ~ '(ALEF|BET|GUÍMEL|DÁLET|HE|VAV|ZAIN|HET|TET|YOD|CAF|LÁMED|MEM|NUN'
            || '|SÁMEC|AYIN|PE|TSADE|COF|RESH|SIN Y SHIN|TAV)\s*$';
```

아가의 화자 표시(`Amado`, `Amante`, `Amigos`)는 **일반 본문에도 등장하는 단어**라 단순 검색은 오탐이 난다. 표제는 문장 중간이나 절 끝에 **홀로** 삽입되므로, 앞뒤 문맥으로 좁힌다.

```sql
-- 2) 화자 표시가 문장 경계에 끼어들었는지 (아가, 기대값 0행)
SELECT v.verse_number, v.text FROM bible_verse v ...
WHERE b.book_key = 'SNG'
  AND v.text ~ '([.!?»]\s+(Amado|Amante|Amigos)\s+[A-ZÁÉÍÓÚÑ¡¿]|(Amado|Amante|Amigos)\s*$)';
```

두 쿼리 모두 **[4.3](#43-함정-1-절-사이-표제가-앞-절에-섞여-들어간다)에서 실제로 관측된 오염 형태**를 그대로 겨냥한다. 오탐이 나오면 해당 절 본문을 눈으로 확인한다.

### 7.4 RV1909 대조

같은 언어의 확정 판본이 이미 적재되어 있으므로, 절 수 차이를 양방향으로 뽑는다.

- RV1909에 있고 SBLM에 없는 (책, 장, 절)
- SBLM에 있고 RV1909에 없는 (책, 장, 절)

**주의:** 차이가 곧 누락은 아니다. RV1909 작업에서 확인했듯 스페인어 역본 간 차이 18건은 대부분 **절 병합·이동**(예: 요나 1:17 ↔ 2:1)이었다. 한쪽 방향이 0이라는 사실만으로 누락을 단정할 수 없으므로, 차이 항목은 **인접 절 본문을 눈으로 확인**해 병합/이동/실제 누락을 분류한다.

### 7.5 책명 교차 검증 결과

66권 1장 페이지를 전수 조회해 `div.mt`, `ul.tnav`, 적재된 RV1909 책명을 대조했다.

| 비교 | 불일치 | 판정 |
| --- | --- | --- |
| `div.mt` 존재 여부 | 0권 결측 | — |
| `div.mt` 이름 고유성 | **17권이 8개 이름으로 충돌** | **사용 불가** |
| `div.mt` vs `ul.tnav` | 20권 불일치 | `div.mt` 결함 |
| `ul.tnav` 이름 고유성 | 0건 충돌 | 사용 가능 |
| `ul.tnav` vs RV1909 (대소문자 무시) | **5권** | 표기 차이, 식별 불일치 0 |

`ul.tnav`와 RV1909의 차이 5건은 전부 표기 스타일이며 **다른 책을 가리키는 경우는 없다.**

| # | USFM | `ul.tnav` | RV1909 |
| --- | --- | --- | --- |
| 22 | SNG | `CANTARES` | `Cantar de los Cantares` |
| 41 | MRK | `SAN MARCOS` | `Marcos` |
| 43 | JHN | `SAN JUAN` | `Juan` |
| 65 | JUD | `SAN JUDAS` | `Judas` |
| 66 | REV | `EL APOCALIPSIS` | `Apocalipsis` |

나머지 61권은 대소문자만 다르다. 따라서 [6.4](#64-bible_book-66권-시드)의 권고대로 RV1909 책명을 재사용해도 **책 식별에 오류가 없음이 확인된다.**

---

## 8. 테스트 설계

`tests/test_scraper.py`에 인라인 HTML 픽스처로 추가한다(**네트워크 접근 금지**).

| 테스트 | 검증 내용 |
| --- | --- |
| `..._drops_headings_between_verses` | `div.d`/`div.sp`가 앞 절에 붙지 않는다 |
| `..._drops_inline_footnote_popup` | `a.notemark` + `span.popup` 본문이 제거된다 |
| `..._keeps_words_of_jesus` | `span.wj` 텍스트가 보존된다 |
| `..._joins_verse_across_blocks` | 두 `div.p`에 걸친 절이 **공백 하나**로 이어진다 |
| `..._builds_spablm_urls` | 엔트리 URL이 `spablm`이면 URL이 `spablm` 경로로 생성된다 |
| `..._rejects_mismatched_ebible_translation` | SBLM URL + RVR1909 메타데이터 조합이 예외를 낸다([5.4](#54-정합성-검증의-구멍--version이-쿼리스트링에서만-온다)) |

앞 세 개는 이미 추가되어 통과한다(전체 87개 통과). 뒤 세 개는 이 설계의 구현 단계에서 추가한다.

> 테스트 헬퍼는 `sleep_min/sleep_max`를 0으로 낮춰야 한다. eBible 지연 하한 1초가 `__init__`에서 강제되기 때문이다.

---

## 9. 운영 계획

### 9.1 요청 간격

`ebible.org/robots.txt`에는 `Crawl-delay` 선언이 없다. 자체 하한 1.0초를 유지한다.

```python
elif self._is_ebible_source():
    self.sleep_min = max(self.sleep_min, EBIBLE_MIN_DELAY_SECONDS)      # 1.0
    self.sleep_max = max(self.sleep_max, EBIBLE_MIN_DELAY_SECONDS + 1.0)
```

1,189장 × 평균 1.5초 + 책 간 5초 × 65 ≈ **35분**. 낮추지 않는다.

### 9.2 실행 예

```bash
# 파서만 확인 (DB 미접속)
SBLM_ENTRY_URL=https://ebible.org/spablm/GEN01.htm \
BIBLE_TRANSLATION_TYPE=SBLM \
python3 scrape_bible_to_db.py --test-book 19 --test-chapter 119

# 창세기만 적재
BIBLE_TRANSLATION_TYPE=SBLM BIBLE_LANGUAGE_CODE=es \
SBLM_ENTRY_URL=https://ebible.org/spablm/GEN01.htm \
python3 scrape_bible_to_db.py --start-book 1 --end-book 1

# 전권
... --start-book 1 --end-book 66
```

`BIBLE_TRANSLATION_ID`만 지정하면 엔트리 URL 선택에 반영되지 않아 **엉뚱한 소스가 선택될 수 있다.** `BIBLE_TRANSLATION_TYPE` 또는 `--entry-url`을 반드시 함께 준다.

### 9.3 초안 갱신 문제 — missing-only 삽입의 한계

SBLM은 **개정 중 초안**이다([1.2](#12-라이선스와-초안-표기--이-소스의-가장-큰-특징)). 이 저장소의 삽입은 missing-only이므로:

- 처음 적재한 본문이 **영구히 남는다.**
- 원문이 수정되어도 재실행은 "이미 있는 절"로 보고 건너뛴다.
- 갱신하려면 해당 역본의 `bible_verse`를 **지우고 다시 적재**해야 한다.

선택지는 셋이다.

| 안 | 내용 | 평가 |
| --- | --- | --- |
| A | 지금 적재하고, 갱신은 수동 재적재 | 단순. 초안임을 DB 밖에서 기억해야 함 |
| B | 적재를 보류하고 확정판을 기다림 | 안전하나 무기한 |
| C | 갱신 감지 후 덮어쓰기 모드 추가 | 멱등성 계약을 바꿔야 함. 범위 초과 |

**A를 권고한다.** 단, `bible_translation.name`에 초안임이 드러나도록 두고, 적재 시점을 커밋 메시지와 이 문서에 남긴다. C는 CLAUDE.md의 "missing-only" 계약을 정면으로 바꾸는 변경이라 별도 설계가 필요하다.

---

## 10. 원본 요청 항목 대응표

| 원본 요청 | 대응 | 상태 |
| --- | --- | --- |
| URL 구조 분석 / 66권 순회 | `_build_ebible_url()` + `KJV_CHAPTER_COUNTS` | **구현됨** |
| Book Code / Name 추출 | `bible_book` 시드([6.4](#64-bible_book-66권-시드)) | 시드 필요 |
| Chapter / Verse / Text 추출 | `_extract_verses_from_ebible_page()` | **구현됨** |
| 각주·태그 제거 | `EBIBLE_REMOVABLE_SELECTOR` | **확장 완료** |
| 출력 `spablm_bible.json` / `bible.sqlite` | **채택하지 않음** — 이 저장소는 PostgreSQL 적재가 목적 | 대체 |
| 요청 딜레이 `0.1~0.3s` | **1.0초로 상향** — 예의상 하한([9.1](#91-요청-간격)) | 강화 |
| 재시도 + 백오프 | `_request_html()` 429/5xx 재시도·스로틀 배수 | **구현됨** |
| User-Agent 헤더 | 세션 기본 헤더 | **구현됨** |
| 진행률 표시 | `[BOOK %02d][CH %03d]` 로그 | **구현됨**(형식 상이) |
| Resume 체크포인트 | `--resume` + 장 단위 커밋 | **구현됨** |
| `requirements.txt` / README | 이미 존재 | **구현됨** |

요청의 딜레이 `0.1~0.3s`는 채택하지 않는다. 1,189장을 3분에 훑는 속도로, 무료 공개 서버에 대한 예의가 아니다.

---

## 11. 구현 순서

0. **선행 합의 두 건** — 시편 표제 처리 A/B([4.7](#47-미결정-시편-표제를-버릴-것인가))와 초안 재적재 방침([9.3](#93-초안-갱신-문제--missing-only-삽입의-한계)). 둘 다 적재 후에 번복하면 재적재가 필요하다
1. `EBIBLE_REMOVABLE_SELECTOR` 확장 + 표제/각주/`wj` 테스트 3종 — **완료**
2. (0번이 B안이면) 1절 앞 `div.d`를 1절에 병합하는 파서 변경 + 테스트
3. `get_source_version()` 도입 및 `RVR1909.version = "spaRV1909"` 변경([5.4](#54-정합성-검증의-구멍--version이-쿼리스트링에서만-온다))
4. 블록 경계 공백 테스트, `spablm` URL 테스트, 정합성 예외 테스트 추가
5. `SBLM` 역본 등록 5곳([5.3](#53-scrape_bible_to_dbpy--역본-등록))
6. `translation_type` CHECK 제약 28 → 29([6.2](#62-translation_type-check-제약--29번째-값))
7. `bible_translation` 행 생성([6.3](#63-bible_translation-row))
8. 책명 교차 검증 후 `bible_book` 66행 시드([6.4](#64-bible_book-66권-시드))
9. 창세기 1장 → 창세기 전권 → 66권 순으로 적재
10. 구조·인코딩·표제 오염·RV1909 대조 검증([7](#7-검증))
11. README / CLAUDE.md 지원 소스 표 갱신

순서에 두 개의 강제 제약이 있다.

- **3번은 5번보다 먼저.** 역본을 먼저 등록하면 `_expected_translation_type()`이 첫 일치를 반환하는 탓에 **기존 RV1909 실행이 깨진다.**
- **0번과 2번은 9번보다 먼저.** missing-only 삽입이라 적재 후 본문 방침을 바꾸면 지우고 다시 넣어야 한다.

---

## 12. 리스크

### 리스크 1. 초안 본문 고착 (가장 큼)

본문이 개정 중인데 missing-only 삽입이라 초기 적재본이 고착된다. → [9.3](#93-초안-갱신-문제--missing-only-삽입의-한계) A안, 재적재 절차를 문서화.

### 리스크 2. 미관측 USFM 클래스

8개 장 표본에서 보지 못한 표제 클래스가 다른 책에 있을 수 있다. `div.d`/`div.sp`와 같은 유형이면 **조용히 오염된다.** → [7.3](#73-표제-오염-회귀-검증--이-소스-필수) 전용 쿼리를 전권 적재 후 실행하고, 표본을 8개 → 전권 스캔으로 확대해 미지 클래스를 열거한다.

### 리스크 3. 정합성 검증 우회

[5.4](#54-정합성-검증의-구멍--version이-쿼리스트링에서만-온다)를 고치지 않고 SBLM을 등록하면 **RV1909 본문이 SBLM 역본에, 또는 그 반대로 적재될 수 있다.** 되돌리는 비용이 크다. → 구현 순서 3번을 선행 조건으로 못박는다.

### 리스크 3-1. 스페인어 역본 간 시편 표제 불일치

[4.7](#47-미결정-시편-표제를-버릴-것인가). RV1909는 1절에 표제를 담고 SBLM은 버린다. 검증을 전부 통과하므로 나중에 발견하면 원인 추적에 시간이 든다. → 적재 **전에** A/B를 결정하고 문서에 남긴다.

### 리스크 4. RV1909 회귀

제거 셀렉터는 두 역본이 **공유**한다. 항목을 추가하면 RV1909 파싱에도 영향이 간다. → RV1909 9개 장 재파싱으로 변화 없음을 확인했고, 셀렉터 변경 시마다 반복한다.

---

## 13. 결론

SBLM 적재는 **소스 추가가 아니라 역본 추가**다. eBible 어댑터가 이미 있으므로 URL·HTTP·인코딩·재시도·resume는 변경 없이 재사용된다.

실제로 필요한 작업은 넷이다.

1. **파서 제거 셀렉터 확장** — `div.d`/`div.sp` 오염이 실측으로 확인됐고(시편 119편 21건, 아가 1장 8건), 이 오염은 자동 검증을 전부 통과하므로 반드시 선행되어야 한다. **완료.**
2. **정합성 검증 수정** — 같은 소스에서 역본이 둘이 되는 첫 사례라 `version` 판별이 깨진다. 역본 등록보다 **먼저** 해야 한다.
3. **시편 표제 방침 결정** — B안이면 파서에 위치 조건을 하나 더 넣는다. 적재 후에는 번복 비용이 크다.
4. **DB 시드** — CHECK 제약 1개, `bible_translation` 1행, `bible_book` 66행(책명은 `div.mt`가 아니라 적재된 RV1909 값을 재사용). `bible_book_description`은 추가 작업 없음.

적재 자체보다 **판단이 필요한 사항 두 가지**가 더 중요하다. 초안 본문을 확정본처럼 저장하게 된다는 점([9.3](#93-초안-갱신-문제--missing-only-삽입의-한계))과, 시편 표제를 버릴지 여부([4.7](#47-미결정-시편-표제를-버릴-것인가))다. 둘 다 missing-only 삽입 때문에 **적재 후 번복하면 지우고 다시 넣어야 한다.** 착수 전에 합의한다.
