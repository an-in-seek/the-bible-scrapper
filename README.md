# Bible Scraper to PostgreSQL

성경 본문을 스크래핑해 PostgreSQL의 `bible_chapter`, `bible_verse`에 적재하는 도구입니다.

현재 기준으로 안정적으로 맞춰진 소스는 아래 2개입니다.

- `thekingsbible.com` KJV
- 대한성서공회 `bskorea.or.kr` 개역개정(NKRV, `version=GAE`)

대한성서공회 설계 문서는 [docs/bskorea_scraping_design.md](docs/bskorea_scraping_design.md)에 있습니다.

## 주요 특징

- `bible_book`의 기존 row를 조회해 사용하며 book 자체는 생성하지 않습니다.
- `bible_chapter`, `bible_verse`는 기존 데이터를 재사용하고 없는 데이터만 insert 합니다.
- 책 단위로 `commit`/`rollback` 하며, 실패 시 책 단위 재시도를 수행합니다.
- 실행 시작 시 `bible_chapter`, `bible_verse`의 ID 시퀀스를 현재 `MAX(id)`에 맞춰 동기화합니다.
- `.env`를 자동 로드하되, 이미 셸에 설정된 환경변수는 덮어쓰지 않습니다.
- KJV/NKRV 소스와 번역본 메타데이터가 어긋나면 실행 초기에 오류로 중단합니다.
- smoke test 경로는 DB 연결 없이 장 파싱만 검증합니다.

## 프로젝트 구조

- `scrape_bible_to_db.py`: 메인 CLI 엔트리포인트
- `scrape_kjv_to_db.py`: 레거시 호환용 래퍼, 내부적으로 `scrape_bible_to_db.py` 실행
- `scraper.py`: HTTP 요청, 소스별 chapter URL 생성, 장/절 파싱
- `db.py`: PostgreSQL 연결 및 repository 쿼리
- `models.py`: `Book`, `ChapterPayload`, `Verse`
- `tests/test_scraper.py`: 파서 단위 테스트
- `tests/test_db.py`: 번역본 식별 로직 테스트
- `tests/test_pipeline.py`: 파이프라인/인자 검증 테스트
- `scripts/run_tests_wsl.sh`: WSL 테스트 실행 스크립트
- `docs/bskorea_scraping_design.md`: NKRV 설계 문서

## 요구 사항

- Python 3.11+
- PostgreSQL
- 대상 번역본에 해당하는 `bible_book` 66권이 DB에 이미 존재해야 함

## 설치

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### WSL / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 환경변수

스크립트는 실행 시작 시 프로젝트 루트의 `.env`를 읽습니다.

### 필수 DB 설정

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=your_db
DB_USER=your_user
DB_PASSWORD=your_password
```

### 소스 엔트리 URL

```env
KJV_ENTRY_URL=https://thekingsbible.com/Bible/1/1
NKRV_ENTRY_URL=https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal
```

`--entry-url`를 지정하지 않으면 기본 URL은 아래 순서로 결정됩니다.

1. `KJV_ENTRY_URL`와 `NKRV_ENTRY_URL`가 둘 다 있으면 번역본 힌트에 따라 선택
2. 둘 중 하나만 있으면 그 값을 사용
3. 둘 다 없으면 내장 기본값 `https://thekingsbible.com/Bible/1/1` 사용

번역본 힌트는 아래 값으로 판단합니다.

- NKRV 힌트: `BIBLE_TRANSLATION_ID=2`, `BIBLE_TRANSLATION_TYPE=NKRV`, `BIBLE_TRANSLATION_NAME=개역개정`, `BIBLE_LANGUAGE_CODE=ko`
- KJV 힌트: `BIBLE_TRANSLATION_TYPE=KJV`, `BIBLE_LANGUAGE_CODE=en`

둘 다 모호하면 NKRV URL을 우선 선택합니다.

### 번역본 선택

CLI는 `BibleRepository()`를 기본 생성자로 사용하므로 번역본은 환경변수로 결정됩니다.

우선순위는 아래와 같습니다.

1. `BIBLE_TRANSLATION_ID`
2. `BIBLE_TRANSLATION_TYPE`, `BIBLE_TRANSLATION_NAME`, `BIBLE_LANGUAGE_CODE` 조합으로 `public.bible_translation` 조회
3. 아무 값도 없으면 레거시 기본값 `translation_id=10`

메타데이터 조회 시에는 지정한 조건만 `AND`로 묶어 검색하고, 일치하는 row 중 `id ASC` 첫 번째를 사용합니다.

예시:

```env
BIBLE_TRANSLATION_ID=10
```

또는

```env
BIBLE_TRANSLATION_TYPE=KJV
BIBLE_TRANSLATION_NAME=King James Version
BIBLE_LANGUAGE_CODE=en
```

NKRV 예시:

```env
BIBLE_TRANSLATION_ID=2
```

또는

```env
BIBLE_TRANSLATION_TYPE=NKRV
BIBLE_TRANSLATION_NAME=개역개정
BIBLE_LANGUAGE_CODE=ko
```

`translation_id=10`은 코드의 레거시 fallback일 뿐이므로, 실제 DB 값이 다르면 반드시 명시적으로 설정해야 합니다.

## DB 전제와 동작 방식

### 필수 전제

- `public.bible_translation`에 대상 번역본 row가 존재해야 합니다.
- `public.bible_book`에 대상 `translation_id` 기준 66권이 존재해야 합니다.

### 적재 방식

1. 대상 `bible_book`을 `book_order ASC`로 조회합니다.
2. 소스별 규칙으로 chapter URL 목록을 만듭니다.
3. 기존 `bible_chapter`를 조회하고 없는 chapter만 insert 합니다.
4. 각 chapter에서 절을 파싱합니다.
5. 기존 `verse_number`를 조회하고 없는 절만 insert 합니다.
6. 각 책이 끝나면 `commit`, 실패하면 해당 책만 `rollback` 후 재시도합니다.

### 안전 장치

- 어떤 chapter에서도 절이 하나도 파싱되지 않으면 해당 책 전체는 커밋하지 않습니다.
- chapter의 첫 절 번호가 `1`이 아니면 해당 chapter insert를 건너뜁니다.
- 기존 절 번호가 있으면 중복 insert 하지 않습니다.

## 지원 소스

### 1. KJV `thekingsbible.com`

- 기본 URL 규칙: `https://thekingsbible.com/Bible/{book_order}/{chapter_number}`
- 장 수는 코드에 내장된 정경 66권 chapter count를 사용합니다.

예:

- 창세기 1장: `https://thekingsbible.com/Bible/1/1`
- 창세기 50장: `https://thekingsbible.com/Bible/1/50`
- 출애굽기 1장: `https://thekingsbible.com/Bible/2/1`

### 2. NKRV `bskorea.or.kr`

- `korbibReadpage.php` URL을 기준으로 chapter URL을 생성합니다.
- book 코드는 `bible_book.book_key`가 있으면 우선 사용하고, 없으면 코드 내 canonical code를 사용합니다.
- 장 수는 KJV와 동일한 정경 66권 chapter count를 사용합니다.

권장 엔트리 URL:

```env
NKRV_ENTRY_URL=https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal
```

예:

- 레위기 11장: `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
- 레위기 27장: `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=27&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
- 민수기 1장: `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=num&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal`

## 네트워크와 재시도

- `429`, `502`, `503`, `504` 응답은 자동 재시도합니다.
- `429` 응답에 `Retry-After`가 있으면 해당 값을 우선 사용합니다.
- 본문에 `Too Many Requests`, `429 Error` 같은 마커가 있는 200 응답도 재시도 대상으로 처리합니다.
- 요청 성공 후에는 throttle을 서서히 낮추고, 실패가 누적되면 요청 간 대기 시간을 늘립니다.
- chapter 간에는 scraper 내부의 polite delay가 적용되고, book 간에는 추가로 5초 대기합니다.

## 실행 방법

### 전체 실행

```bash
python3 scrape_bible_to_db.py
```

### 책 범위 실행

```bash
python3 scrape_bible_to_db.py --start-book 1 --end-book 3
```

### 특정 책의 특정 장 범위만 실행

`--start-chapter`, `--end-chapter`는 아래 조건에서만 사용할 수 있습니다.

- `--resume` 없이
- `--start-book`과 `--end-book`이 같은 경우

```bash
python3 scrape_bible_to_db.py --start-book 3 --end-book 3 --start-chapter 11 --end-chapter 11
```

### 재개 실행

```bash
python3 scrape_bible_to_db.py --resume
```

주의:

- `--resume`은 "완전히 끝난 책"이 아니라 `bible_verse`가 하나라도 존재하는 가장 큰 `book_order` 다음 책부터 시작합니다.
- 부분 적재 상태가 남아 있는 책도 이미 완료된 책으로 간주될 수 있습니다.

### smoke test

아래 경로는 DB에 insert 하지 않습니다.

```bash
python3 scrape_bible_to_db.py --test-genesis1
python3 scrape_bible_to_db.py --test-book 3 --test-chapter 11
```

`--test-genesis1`는 `book_order=1`, `chapter=1`에 대한 편의 옵션입니다.

### 재시도와 로그

```bash
python3 scrape_bible_to_db.py --book-retries 5 --verbose
```

- `--book-retries`: 책 단위 실패 재시도 횟수, 기본값 `3`
- `--verbose`: `DEBUG` 로그 활성화

## 실행 예시

### KJV 실행

```bash
export BIBLE_TRANSLATION_TYPE=KJV
export BIBLE_TRANSLATION_NAME="King James Version"
export BIBLE_LANGUAGE_CODE=en
export KJV_ENTRY_URL="https://thekingsbible.com/Bible/1/1"
python3 scrape_bible_to_db.py --start-book 1 --end-book 1
```

### NKRV 실행

```bash
export BIBLE_TRANSLATION_ID=2
export NKRV_ENTRY_URL="https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
python3 scrape_bible_to_db.py --start-book 1 --end-book 1
```

### NKRV 특정 장만 실행

```bash
export BIBLE_TRANSLATION_ID=2
export NKRV_ENTRY_URL="https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
python3 scrape_bible_to_db.py --start-book 3 --end-book 3 --start-chapter 11 --end-chapter 11
```

### NKRV 특정 장 smoke test

```bash
export NKRV_ENTRY_URL="https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
python3 scrape_bible_to_db.py --test-book 3 --test-chapter 11
```

## 테스트

### 기본 실행

```bash
pytest -q
```

또는

```bash
python3 -m pytest -q
```

### WSL 스크립트

```bash
bash scripts/run_tests_wsl.sh
bash scripts/run_tests_wsl.sh -k fallback
```

`scripts/run_tests_wsl.sh`는 아래 작업을 자동으로 수행합니다.

- `.venv-wsl`이 없으면 생성
- `pip`이 없으면 `ensurepip` 실행
- `requirements.txt` 설치
- `pytest -q` 실행

## 성능 권장 사항

대량 적재 시 아래 인덱스를 권장합니다.

```sql
CREATE INDEX idx_chapter_book_id ON bible_chapter(book_id);
CREATE INDEX idx_verse_chapter_id ON bible_verse(chapter_id);
```

## 트러블슈팅

### `No target books found. Nothing to do.`

- 대상 번역본의 `bible_book`이 없거나
- `start-book`/`end-book` 범위가 비어 있거나
- `--resume` 기준 다음 책이 범위 밖인 경우입니다.

### `Source/translation mismatch`

- `thekingsbible.com`에 NKRV 번역본 메타데이터를 붙였거나
- `bskorea.or.kr?version=GAE`에 KJV 메타데이터를 붙인 경우입니다.

### `Parsed 0 verses across all chapters`

- 해당 책에서 유효한 본문을 하나도 추출하지 못한 경우입니다.
- 빈 스크랩 결과를 커밋하지 않기 위해 의도적으로 실패 처리합니다.
