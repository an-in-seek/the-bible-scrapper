# 대한성서공회(`bskorea.or.kr`) 성경 본문 스크래핑 개발 설계

## 1. 목적

현재 저장소는 `thekingsbible.com` KJV 본문을 대상으로 동작한다.  
이번 설계의 목적은 아래 대한성서공회 URL 패턴을 대상으로 동일한 방식의 장/절 수집을 가능하게 하는 것이다.

- 예시 URL
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=12&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=13&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=14&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=27&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=num&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=num&chap=2&sec=1&cVersion=&fontSize=15px&fontWeight=normal`

대상 역본 예시는 `GAE`(개역개정)이며, 설계는 다른 역본 코드에도 재사용 가능하도록 구성한다.

권장 기본 엔트리 URL 환경변수:

```env
NKRV_ENTRY_URL=https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal
```

## 2. 대상 페이지 특성

### 2.1 URL 파라미터

예시 URL 기준 파라미터는 아래 의미로 해석할 수 있다.

- `version`
  - 주 역본 코드. 예: `GAE`
- `book`
  - 책 코드. 예: `lev`
- `chap`
  - 장 번호. 예: `11`
- `sec`
  - 시작 절 또는 화면 앵커 역할로 보임. 전체 장 수집은 `1` 고정 사용을 기본값으로 둔다.
- `cVersion`
  - 대조 역본. 비어 있으면 단일 본문
- `fontSize`, `fontWeight`
  - 화면 표시용 옵션. 스크래핑 결과에는 영향 없음

### 2.2 DOM 루트

사용자가 제공한 HTML 예시 기준 본문 루트는 아래와 같다.

```html
<div id="tdBible1" class="bible_read" ...>
```

이 컨테이너 내부에는 다음 요소가 혼재한다.

- 듣기 버튼 영역
- 역본명
- 숨김 책명 `font` (`display:none`)
- 장 번호
- 소제목
- 장 내부에서 반복되는 추가 소제목
- 각 절 본문
- 각주 팝업용 숨김 `div`

따라서 전체 텍스트를 단순 `get_text()`로 추출하면 각주, 버튼, 숨김 설명문이 함께 섞일 가능성이 높다.  
이 사이트는 범용 정규식 파서보다 DOM 특화 파서가 우선되어야 한다.

## 3. 목표 데이터 모델

현재 코드베이스의 DTO를 그대로 사용한다.

- `models.py`
  - `ChapterPayload`
  - `Verse`

필수 산출물은 아래다.

- `book_order`
- `chapter_number`
- `source_url`
- `verses`
  - `verse_number`
  - `text`

`translation_id`는 파싱 결과 DTO의 산출물이 아니라, DB 적재 시 `bible_book` 조회 범위를 결정하는 적재 컨텍스트 값으로 취급한다.

현재 사용자 DB 기준 번역본 메타데이터는 아래와 같다.

```sql
INSERT INTO public.bible_translation
(language_code, translation_order, id, "name", translation_type)
VALUES ('ko', 2, 2, '개역개정', 'NKRV');
```

따라서 대한성서공회 개역개정 적재 대상은 `translation_id=2` 이다.  
단, 구현은 숫자 상수 고정보다 `translation_type='NKRV'`, `name='개역개정'`, `language_code='ko'` 조건으로 `bible_translation.id`를 조회한 뒤 사용하는 방식을 권장한다.

현재 `translation_id=2`에 대한 `bible_book` 66권도 이미 적재되어 있다.  
즉, 대한성서공회 수집기는 `bible_book`을 새로 생성하지 않고 기존 row를 조회해 `bible_chapter.book_id`의 기준으로 사용해야 한다.

핵심 전제:

- `book_order=1..66` 이 정경 순서대로 모두 존재
- `book_key` 는 `GEN`, `EXO`, `LEV`, `NUM` ... `REV` 형태로 채워져 있음
- `id` 는 `67..132` 이지만, 구현은 이 숫자를 하드코딩하지 않고 조회 결과를 사용해야 함

추가로 `bible_chapter`도 일부 또는 전체가 이미 생성되어 있을 수 있다.  
사용자가 제공한 데이터 기준으로는 최소한 아래가 이미 존재한다.

- 창세기(`book_id=67`) 1장~50장
- 출애굽기(`book_id=68`) 1장~40장
- 레위기(`book_id=69`) 1장~27장

따라서 수집기의 chapter 처리 원칙은 다음과 같다.

- 기존 `bible_chapter` row를 우선 조회해 재사용한다.
- `bible_chapter`가 없는 데이터가 있을 경우 해당 chapter를 생성한다.
- 이미 존재하는 chapter는 재생성하지 않고 재사용한다.
- 이미 있는 chapter를 다시 만들지 않는다.
- `bible_verse`도 기존 verse 번호를 우선 조회해 재사용한다.
- `bible_verse`가 없는 데이터가 있을 경우 해당 verse만 생성한다.
- 이미 존재하는 verse는 재삽입하지 않는다.

선택 메타데이터는 이번 1차 범위에서는 저장하지 않는다.

- 역본명 (`개역개정`)
- 장 제목 (`제 11 장`)
- 소제목 (`정한 짐승과 부정한 짐승`)

다만 파서 검증과 디버깅을 위해 내부 로그에는 활용 가능하다.

## 4. 설계 방향

### 4.1 핵심 원칙

- 대한성서공회는 URL 규칙이 결정적이므로 링크 탐색형 수집보다 직접 URL 생성 방식이 안정적이다.
- 본문은 `#tdBible1` 범위로 엄격히 제한한다.
- 절 파싱은 top-level `span` 반복 기반으로 구현한다.
- 숨김 각주, 주석 링크, 숨김 노드는 제거하되 본문을 담은 인라인 `font` 텍스트는 보존한다.
- 현재 저장소의 DB 적재 로직은 재사용하고, 소스 사이트별 URL 생성/파싱만 분리한다.

### 4.2 권장 구조

현재 `HolyBibleScraper`에 사이트별 분기가 계속 누적되면 파서 복잡도가 급격히 커진다.  
따라서 아래 두 계층으로 나누는 방식을 권장한다.

### 옵션 A. 최소 변경

`scraper.py` 내부에 대한성서공회 분기 추가

- `_is_bskorea_source()`
- `_build_bskorea_url(...)`
- `_discover_chapter_urls_for_bskorea(...)`
- `_extract_verses_from_bskorea_read_page(...)`

장점:

- 현재 코드 변경 범위가 작다.

단점:

- `HolyBibleScraper`가 사이트별 책임을 과도하게 갖게 된다.

### 옵션 B. 권장

사이트 어댑터 분리

- `scraper.py`
  - 공통 오케스트레이션, 요청, retry, throttle
- 예: `sources/bskorea.py`
  - URL 생성
  - 책 코드 매핑
  - 대한성서공회 전용 DOM 파싱
- 예: `sources/thekingsbible.py`
  - 기존 KJV 규칙 유지

장점:

- 사이트별 DOM 의존성이 격리된다.
- 테스트를 소스별 fixture 중심으로 작성하기 쉽다.
- 향후 다른 성경 사이트 추가 시 구조가 유지된다.

이번 문서는 옵션 B를 기준안으로 삼는다. 단, 빠른 납품이 우선이면 옵션 A로 시작한 뒤 옵션 B로 리팩터링 가능하다.

## 5. URL 생성 설계

### 5.1 책 코드 매핑

대한성서공회는 `book=lev` 같은 3자리 책 코드를 사용한다.  
DB에는 `book_order`가 있으므로 `book_order -> book_code` 고정 매핑이 필요하다.

현재 DB의 `bible_book.book_key` 는 `LEV`, `NUM` 같은 대문자 코드다.  
대한성서공회 URL은 `lev`, `num` 같은 소문자 코드를 사용하므로, 구현은 아래 둘 중 하나를 택하면 된다.

- 66권 명시 상수 매핑 사용
- 검증이 끝난 경우에 한해 `bible_book.book_key.lower()` 기반 변환 사용

권장 기준안은 66권 명시 상수 매핑이다.  
이유는 `LEV`, `NUM`처럼 단순한 책은 일치하더라도, `1SA`, `2KI`, `1JN`처럼 숫자가 포함된 책이 대한성서공회에서 정확히 같은 규칙을 쓰는지 문서상 아직 검증되지 않았기 때문이다.

`book_key.lower()`는 전체 66권 URL 규칙이 실제 사이트에서 확인된 뒤 최적화로 채택하는 편이 안전하다.

예시:

- `1 -> gen`
- `2 -> exo`
- `3 -> lev`
- `4 -> num`
- ...
- `66 -> rev`

이 매핑은 사이트 의존 상수이므로 `scraper.py`보다는 대한성서공회 전용 모듈에 두는 편이 맞다.

### 5.2 장 URL 생성

장 URL은 탐색 없이 직접 생성한다.

```text
https://www.bskorea.or.kr/bible/korbibReadpage.php
  ?version={version}
  &book={book_code}
  &chap={chapter_number}
  &sec=1
  &cVersion=
  &fontSize=15px
  &fontWeight=normal
```

권장 기본값:

- `sec=1`
- `cVersion=`
- `fontSize=15px`
- `fontWeight=normal`

권장 `.env` 엔트리:

```env
NKRV_ENTRY_URL=https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal
```

표시 옵션은 서버 응답 구조를 바꾸지 않는 한 고정값으로 유지한다.

`version` 우선순위는 아래처럼 정의하는 것이 안전하다.

1. CLI의 `--version`
2. `--entry-url` 또는 `NKRV_ENTRY_URL`에 포함된 `version` 쿼리 파라미터
3. 기본값 `GAE`

즉, `NKRV_ENTRY_URL`에 `version=GAE`가 들어 있어도 CLI에서 다른 역본을 명시하면 최종 요청 URL은 CLI 값을 기준으로 재조합해야 한다.

같은 규칙으로 장 번호만 바뀌는 예:

- 레위기 11장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
- 레위기 12장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=12&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
- 레위기 13장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=13&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
- 레위기 14장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=14&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
- 레위기 27장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=27&sec=1&cVersion=&fontSize=15px&fontWeight=normal`

책이 바뀌면 `book` 코드도 함께 바뀐다.

- 민수기 1장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=num&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
- 민수기 2장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=num&chap=2&sec=1&cVersion=&fontSize=15px&fontWeight=normal`

### 5.3 장 목록 생성

대한성서공회도 정경 66권의 장 수는 KJV와 동일하므로, 현재 `KJV_CHAPTER_COUNTS`와 같은 canonical chapter count를 재사용할 수 있다.  
즉, 이 사이트도 chapter discovery를 크롤링으로 하지 않고 아래 방식으로 생성 가능하다.

- 코드 내부의 canonical chapter count 상수 조회
- `1..chapter_count` 범위 URL 생성

여기서 말하는 chapter count는 DB의 `bible_chapter`를 읽는 것이 아니다.  
DB에 chapter가 누락되어 있어도 생성할 수 있어야 하므로, 장 수 기준은 저장소 내부 상수 또는 검증된 사이트 기준값이어야 한다.

이 방식의 이점:

- 사이트 메뉴 구조 변경에 영향이 적다.
- 불필요한 추가 요청이 없다.
- 테스트가 결정적이다.

## 6. 본문 파싱 설계

### 6.1 파싱 대상 범위

본문 파싱은 반드시 `#tdBible1.bible_read`를 기준으로 한다.

이유:

- 비교 역본이 켜진 경우 `tdBible2` 같은 두 번째 본문 영역이 함께 존재할 가능성이 있다.
- 페이지 전체 텍스트에는 메뉴, 검색, 버튼 라벨이 섞여 있다.

파싱 시작 순서:

1. `soup.select_one("#tdBible1.bible_read")` 탐색
2. 없으면 `div.bible_read` 후보 수를 확인
3. 후보가 정확히 1개일 때만 fallback 사용
4. 후보가 2개 이상이면 `tdBible2` 등 비교 본문 혼입 가능성이 있으므로 실패 처리

### 6.2 메타 요소 식별

본문 컨테이너 안에서 아래 요소는 절 데이터가 아니다.

- 상단 듣기 버튼 `div`
- 역본명 `b`
- 숨김 책명 `font[style*="display:none"]`
- 장 번호 `font.chapNum`
- 소제목 `font.smallTitle`

이 요소는 절 파싱 전에 제거하거나 무시한다.

### 6.3 절 노드 식별 규칙

제공된 HTML 구조 기준으로 각 절은 아래 형태다.

```html
<span>
  <span class="number">1&nbsp;&nbsp;&nbsp;</span>
  절 본문...
</span>
<br>
```

따라서 1차 규칙은 다음과 같다.

- `#tdBible1 > span` 또는 본문 컨테이너의 직계 `span` 반복
- 직계 `span` 안에 `.number`가 있으면 절 후보로 간주
- 장 중간에 다시 나타나는 `font.smallTitle`은 절 후보가 아니므로 건너뛴다
- `br + font.smallTitle + br + br + span` 같은 반복 패턴이 나와도 절 번호 연속성만 기준으로 수집한다

추출 규칙:

1. 직계 `span` 순회
2. 내부 `.number` 텍스트에서 절 번호 숫자 추출
3. 복제한 노드에서 번호 span과 불필요 요소 제거
4. 남은 텍스트를 절 본문으로 정규화

### 6.4 제거해야 하는 불필요 마크업

본문 추출 전 아래 요소는 제거한다.

- `span.number`
  - 절 번호 전용
- `a.comment`
  - 각주 호출 링크
- `div.D2`
  - 숨김 각주 본문
- `font[style*="display:none"]`
  - 책명 등 숨김 텍스트
- `font[size="1"]`
  - 빈 태그면 제거, 텍스트가 있으면 본문으로 유지

제거하지 않고 `get_text()`를 호출하면 아래 문제가 생긴다.

- `1)` 같은 각주 번호가 본문에 붙음
- 숨김 주석 `히, 새의 일종`이 절 본문에 섞임
- `font[size="1"]` 안의 실제 본문 단어가 누락될 수 있음
- 불필요 공백이 증가함

### 6.5 유지해야 하는 인라인 마크업

아래 요소는 텍스트만 유지한다.

- `font.name`
- `font.orgin`
- `font.area`
- `font[size="1"]`의 실제 텍스트
- 일반 `font`

이들은 의미 강조용이지만, 최종 저장값은 plain text여야 하므로 태그는 제거하고 텍스트만 남긴다.

예:

- `<font class="name">모세</font>` -> `모세`
- `<font class="orgin">타흐마스</font>` -> `타흐마스`
- `<font size="1">생물</font>` -> `생물`

### 6.6 절 텍스트 정규화

최종 본문 문자열에 아래 정규화를 적용한다.

- `&nbsp;` 포함 모든 공백을 단일 공백으로 축약
- 앞뒤 공백 제거
- 빈 문자열이면 버림
- 동일 절 번호 중복 시 첫 번째만 채택

권장 정규화:

```python
re.sub(r"\s+", " ", text).strip()
```

### 6.7 예상 파싱 결과 예

레위기 11장 1절:

- 절 번호: `1`
- 본문: `여호와께서 모세와 아론에게 말씀하여 이르시되`

레위기 11장 16절:

- 절 번호: `16`
- 본문: `타조와 타흐마스와 갈매기와 새매 종류와`

여기서 각주 링크 `1)`와 숨김 주석 `히, 새의 일종`은 저장 대상에서 제외한다.

민수기 1장 14절:

- 절 번호: `14`
- 본문: `갓 지파에서는 드우엘의 아들 엘리아삽이요`

여기서 각주 링크 `1)`와 숨김 주석 `2:14 '르우엘'`은 저장 대상에서 제외한다.

민수기 1장은 장 내부에 `레위 지파는 계수하지 말라` 같은 `font.smallTitle`이 다시 등장한다.  
이 값은 절 본문이 아니라 소제목이므로 독립 verse로 파싱하면 안 된다.

레위기 27장은 `서원 예물의 값`, `처음 난 가축`, `여호와께 온전히 바친 것`, `십분의 일은 여호와의 것`처럼 장 내부 소제목이 여러 번 반복된다.  
이 역시 모두 구조용 텍스트일 뿐이므로 verse 본문에 포함하거나 독립 verse로 만들면 안 된다.

### 6.8 예외 처리

다음 경우를 방어해야 한다.

- 절 수가 0개
  - 파서 실패로 간주
- 첫 절 번호가 1이 아님
  - 현재 적재 로직과 동일하게 경고 후 skip 가능
- 번호만 있고 텍스트가 비어 있음
  - 해당 절 제외
- 숨김 각주가 절 span 내부에 중첩됨
  - clone 후 제거 처리 필요
- 장 중간에 소제목이 다시 등장함
  - `font.smallTitle`은 verse로 만들지 않음
- 장 중간에 소제목이 여러 번 반복됨
  - 절 번호 연속성만 유지하고 소제목은 모두 무시
- 숨김 책명 노드가 존재함
  - `display:none` 노드를 제거해야 함
- 작은 글씨 `font`가 실제 본문을 담고 있음
  - 빈 태그만 제거하고 텍스트가 있으면 유지해야 함

## 7. 코드 통합 설계

### 7.1 번역본 식별

DB 적재 전 `bible_book` 조회는 올바른 번역본을 기준으로 해야 한다.

권장 우선순위:

1. `BIBLE_TRANSLATION_ID`
2. `BIBLE_TRANSLATION_TYPE`, `BIBLE_TRANSLATION_NAME`, `BIBLE_LANGUAGE_CODE` 조합 조회
3. 레거시 기본값 fallback

대한성서공회 개역개정 기준 실제 대상은 아래와 같다.

- `translation_id = 2`
- `translation_type = 'NKRV'`
- `name = '개역개정'`
- `language_code = 'ko'`

### 7.2 chapter 재사용 정책

현재 저장소의 DB 로직처럼 `bible_chapter`는 book별로 먼저 조회하고, 누락된 chapter만 보충하는 방식이 맞다.

권장 동작:

1. `book_id` 기준 기존 chapter map 조회
2. 스크래핑 대상 chapter 번호 목록 생성
3. map에 없는 chapter 번호가 있으면 해당 chapter를 insert
4. chapter map 재조회 또는 보강
5. 각 chapter의 기존 verse 번호를 조회
6. 없는 verse 번호만 insert

이 방식이면 사용자가 이미 생성해 둔 chapter row와 충돌하지 않고, 재실행도 안전하다.

### 7.3 권장 인터페이스

현재 `scrape_bible_to_db.py`는 `HolyBibleScraper(entry_url=...)`에 강하게 결합돼 있다.  
대한성서공회 추가 시 아래 수준의 인터페이스를 권장한다.

```python
class BibleSourceAdapter(Protocol):
    def build_chapter_url(self, book_order: int, chapter_number: int) -> str: ...
    def discover_chapter_urls_for_book(self, book_order: int) -> dict[int, str]: ...
    def parse_chapter_html(
        self,
        book_order: int,
        chapter_number: int,
        html: str,
        source_url: str,
    ) -> ChapterPayload: ...
```

공통 스크래퍼는 다음만 담당한다.

- HTTP 요청
- retry / throttle
- HTML 수신
- 캐시
- adapter 호출

대한성서공회 어댑터는 다음만 담당한다.

- 책 코드 매핑
- URL 생성
- DOM 파싱

### 7.4 CLI 확장안

현재 CLI는 KJV 전용 이름과 기본값을 사용한다.  
대한성서공회를 함께 지원하려면 아래 중 하나가 필요하다.

### 단기안

- 기존 스크립트 유지
- 별도 엔트리포인트 추가
  - 예: `scrape_bskorea_to_db.py`

### 중장기안

- 공통 엔트리포인트로 통합
  - `--source thekingsbible`
  - `--source bskorea`
  - `--version GAE`
  - `--entry-url` 기본값으로 `NKRV_ENTRY_URL` 사용

문서 기준 권장안은 중장기안이지만, 빠른 납품만 보면 별도 엔트리포인트가 더 단순하다.

## 8. 테스트 설계

### 8.1 단위 테스트 우선

현재 저장소 테스트 스타일과 동일하게 inline HTML fixture 기반 테스트를 작성한다.

필수 테스트:

- 정상 절 파싱
  - `1..47` 절이 모두 추출되는지
- 정상 절 파싱
  - 민수기 1장 `1..54` 절이 모두 추출되는지
- 정상 절 파싱
  - 레위기 27장 `1..34` 절이 모두 추출되는지
- 번역본 식별
  - `NKRV` / `개역개정` / `ko` 조건으로 `translation_id=2`를 찾는지
- missing chapter 생성
  - `bible_chapter`에 없는 chapter 번호가 있으면 새로 insert하는지
- chapter 재사용
  - 이미 존재하는 `bible_chapter`는 재삽입하지 않고 그대로 사용하는지
- 메타 요소 제외
  - `개역개정`, `제 11 장`, `정한 짐승과 부정한 짐승`이 절 본문에 섞이지 않는지
- 메타 요소 제외
  - `민수기`, `제 1 장`, `싸움에 나갈 만한 자를 계수하다`, `레위 지파는 계수하지 말라`가 절 본문에 섞이지 않는지
- 메타 요소 제외
  - `서원 예물의 값`, `처음 난 가축`, `여호와께 온전히 바친 것`, `십분의 일은 여호와의 것`이 절 본문에 섞이지 않는지
- 각주 제거
  - `1)`와 `히, 새의 일종` 제거 여부
- 각주 제거
  - `1)`와 `2:14 '르우엘'` 제거 여부
- 인라인 태그 평탄화
  - `font.name`, `font.orgin`, `font.area` 텍스트 유지 여부
- `font size="1"` 처리
  - 빈 태그는 제거되고 실제 텍스트는 유지되는지
- 중복 절 번호 방지
- idempotency
  - 이미 존재하는 chapter/verse가 있을 때 재실행해도 중복 insert가 발생하지 않는지

### 8.2 추천 테스트 케이스 예시

### 케이스 1. 기본 절 파싱

- 입력: 레위기 11장 예시 HTML
- 기대:
  - 총 절 수 `47`
  - 1절, 16절, 47절 본문 검증

### 케이스 2. 각주 제거

- 입력: 16절에 `a.comment`와 `div.D2` 포함
- 기대:
  - 본문에 `1)` 없음
  - 본문에 `히, 새의 일종` 없음

### 케이스 3. 비교 역본 컨테이너 무시

- 입력: `tdBible1`, `tdBible2`가 함께 있는 HTML
- 기대:
  - `tdBible1`만 수집

### 케이스 4. 메타 정보 비혼입

- 입력: 상단 `b`, `chapNum`, `smallTitle` 포함
- 기대:
  - verse text에 메타 문자열이 없음

### 케이스 5. 장 중간 소제목 무시

- 입력: 민수기 1장처럼 `smallTitle`이 장 내부 중간에 다시 등장하는 HTML
- 기대:
  - 소제목은 verse로 생성되지 않음
  - 46절 다음 절은 47절로 이어짐

### 케이스 6. 숨김 책명 제거

- 입력: `font style="display:none;" size="2">민수기</font>` 포함 HTML
- 기대:
  - verse text에 `민수기`가 섞이지 않음

### 케이스 7. 반복 소제목 무시

- 입력: 레위기 27장처럼 장 내부에 `smallTitle`이 여러 번 반복되는 HTML
- 기대:
  - 소제목은 verse로 생성되지 않음
  - 최종 절 수는 `34`
  - 25절 다음 절은 26절, 27절 다음 절은 28절, 29절 다음 절은 30절로 정상 연결됨

### 케이스 8. 작은 글씨 본문 보존

- 입력: `font size="1"` 안에 `생물`, `주검은`, `자손이` 같은 실제 본문 단어가 들어 있는 HTML
- 기대:
  - 해당 단어가 verse text에서 사라지지 않음

### 케이스 9. 번역본 ID 조회

- 입력: `bible_translation(id=2, name='개역개정', translation_type='NKRV', language_code='ko')`
- 기대:
  - 대한성서공회 적재 대상 translation id를 `2`로 결정함

### 케이스 10. missing chapter 생성

- 입력: 대상 책의 일부 chapter가 `bible_chapter`에 없는 상태
- 기대:
  - 누락된 chapter 번호만 insert
  - 이미 있는 chapter는 건드리지 않음

### 케이스 11. 기존 chapter 재사용

- 입력: `bible_chapter`에 레위기(`book_id=69`) 1장~27장이 이미 존재하는 상태
- 기대:
  - chapter insert가 발생하지 않음
  - 기존 chapter id를 기준으로 verse insert만 수행함

### 케이스 12. 재실행 idempotency

- 입력: 이미 일부 verse가 저장된 chapter
- 기대:
  - 기존 verse 번호는 skip
  - missing verse만 insert

### 8.3 통합 테스트

네트워크 의존 테스트는 기본 CI 대상에서 제외하고, 선택 실행으로 둔다.

예:

- 실제 URL 1장 fetch smoke test
- 응답 상태 확인
- 최소 1개 이상 절 파싱 확인

단, 외부 사이트 변경과 차단 가능성이 있으므로 단위 테스트를 품질 기준으로 삼는다.

## 9. 리스크 및 대응

### 리스크 1. DOM 구조 변경

대응:

- `#tdBible1` 기준 범위를 강하게 고정
- 절 후보 탐색 규칙을 1개 더 둠
  - 예: `.number` 포함 span 탐색 fallback

### 리스크 2. 각주/숨김 텍스트 혼입

대응:

- 파싱 전 clone 후 `a.comment`, `div.D2` 제거
- 숨김 요소는 class 기반으로 제거

### 리스크 3. 비교 역본 기능으로 컨테이너 다중화

대응:

- 기본 컨테이너를 `tdBible1`로 고정
- `cVersion`은 빈 값 유지

### 리스크 4. 사이트 차단 또는 요청 제한

대응:

- 현재 retry/throttle 로직 재사용
- 요청 사이 sleep 유지
- 장 수 생성형 접근으로 불필요 요청 최소화

## 10. 구현 순서 제안

1. 대한성서공회용 책 코드 상수 정의
2. 장 URL 생성 함수 구현
3. `#tdBible1` 전용 절 파서 구현
4. inline HTML fixture 테스트 추가
5. 기존 공통 스크래퍼에 adapter 연결
6. 실제 1개 장 smoke test 수행
7. DB 적재 경로 연결

## 11. 결론

대한성서공회 페이지는 링크 크롤링형 사이트가 아니라, 결정적인 쿼리 파라미터 URL과 비교적 안정적인 본문 DOM을 가진다.  
따라서 이 저장소에 붙일 때 핵심은 "자동 링크 탐색"이 아니라 아래 두 가지다.

- `book_order -> bskorea book code` 매핑 기반 URL 생성
- `#tdBible1` 범위에서 각주/보조 마크업을 제거한 절 단위 DOM 파싱

이 방식으로 구현하면 현재 DB 적재 구조와 retry 로직은 대부분 재사용하면서, 대한성서공회용 한국어 본문 수집 기능을 안정적으로 추가할 수 있다.
