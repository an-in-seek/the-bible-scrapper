# Bible Scraper to PostgreSQL

성경 본문을 스크래핑해 PostgreSQL의 `bible_chapter`, `bible_verse`에 적재하는 도구입니다.

현재 저장소 상태:

- 구현 완료
  - `thekingsbible.com` KJV 스크래퍼
  - 대한성서공회(`bskorea.or.kr`) 개역개정(NKRV) 스크래퍼
- 설계 문서 유지
  - 대한성서공회(`bskorea.or.kr`) 개역개정(NKRV) 스크래핑 설계 문서

대한성서공회 개역개정 설계 문서:

- [docs/bskorea_scraping_design.md](/mnt/c/workspace/python/BibleScrapper/docs/bskorea_scraping_design.md)

## 개요

- 대상 DB 테이블
  - `bible_book`
  - `bible_chapter`
  - `bible_verse`
- 공통 특징
  - 중복 삽입 방지
  - book 단위 트랜잭션(commit/rollback)
  - HTTP 재시도(backoff)
  - 기존 chapter/verse 재사용, missing 데이터만 insert

## 프로젝트 구조

- `scrape_bible_to_db.py`
  - CLI 진입점, book 루프, 트랜잭션/재시도
- `scraper.py`
  - HTTP 요청, 링크 자동 탐색, 장/절 파싱
- `db.py`
  - DB 연결 및 repository 쿼리
- `models.py`
  - DTO (`Book`, `ChapterPayload`, `Verse`)
- `tests/test_scraper.py`
  - 파서 단위 테스트
- `tests/test_db.py`
  - 번역본 식별 단위 테스트
- `docs/bskorea_scraping_design.md`
  - 대한성서공회 개역개정 설계 문서
- `scripts/run_tests_wsl.sh`
  - WSL 테스트 실행 스크립트

## 설치

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### WSL / Linux (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 환경변수

스크립트 실행 시 프로젝트 루트의 `.env`를 자동 로드합니다.

기본 DB 연결:

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=your_db
DB_USER=your_user
DB_PASSWORD=your_password
```

소스별 엔트리 URL:

```env
KJV_ENTRY_URL=https://thekingsbible.com/Bible/1/1
NKRV_ENTRY_URL=https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal
```

번역본 선택 방식은 둘 중 하나를 사용합니다.

### 1. `translation_id` 직접 지정

```env
BIBLE_TRANSLATION_ID=10
```

### 2. 번역본 메타데이터로 조회

```env
BIBLE_TRANSLATION_TYPE=KJV
BIBLE_TRANSLATION_NAME=King James Version
BIBLE_LANGUAGE_CODE=en
```

## 개역개정(NKRV) 기준 설정 예시

현재 사용자 DB 상태 기준으로 아래 translation row가 존재합니다.

```sql
INSERT INTO public.bible_translation
(language_code, translation_order, id, "name", translation_type)
VALUES ('ko', 2, 2, '개역개정', 'NKRV');
```

이 경우 권장 설정 예시는 아래와 같습니다.

### 방법 1. ID 직접 지정

```env
BIBLE_TRANSLATION_ID=2
```

### 방법 2. 메타데이터로 조회

```env
BIBLE_TRANSLATION_TYPE=NKRV
BIBLE_TRANSLATION_NAME=개역개정
BIBLE_LANGUAGE_CODE=ko
```

## DB 전제

### KJV 실행 시

- 대상 번역본에 대응하는 `bible_book` 66권이 이미 존재해야 합니다.
- 현재 KJV 스크래퍼는 `thekingsbible.com`를 소스로 사용합니다.

### 개역개정(NKRV) 기준 사용자 DB 상태

- `bible_translation.id = 2`
- `translation_type = 'NKRV'`
- `name = '개역개정'`
- `language_code = 'ko'`
- `bible_book(translation_id=2)` 66권이 이미 존재
- `bible_chapter`도 일부 또는 전체가 이미 존재할 수 있음

중요 동작 원칙:

- `bible_book`은 재생성하지 않고 기존 row를 조회해 사용
- `bible_chapter`가 있으면 재사용, 없으면 생성
- `bible_verse`가 있으면 재사용, 없으면 생성
- 이미 존재하는 verse 번호는 다시 insert하지 않음

## 현재 구현된 실행 방법

현재 엔트리포인트는 `scrape_bible_to_db.py` 이며, `--entry-url` 또는 환경변수에 따라 KJV / NKRV 소스를 모두 처리할 수 있습니다.

```bash
python3 scrape_bible_to_db.py
python3 scrape_bible_to_db.py --start-book 1 --end-book 66
python3 scrape_bible_to_db.py --resume
python3 scrape_bible_to_db.py --test-genesis1
python3 scrape_bible_to_db.py --test-book 3 --test-chapter 11
python3 scrape_bible_to_db.py --start-book 3 --end-book 3 --start-chapter 11 --end-chapter 11
```

`--test-genesis1`는 레거시 smoke test로 창세기 1장을 검증합니다.  
임의 chapter smoke test는 `--test-book` / `--test-chapter`를 사용합니다.  
`--start-chapter` / `--end-chapter`는 `--resume` 없이 단일 책 선택에서만 사용할 수 있습니다.

KJV 기본 엔트리 URL:

```env
KJV_ENTRY_URL=https://thekingsbible.com/Bible/1/1
```

KJV URL 규칙 예:

```text
https://thekingsbible.com/Bible/{book_order}/{chapter_number}
```

예:

- 창세기 1장
  - `https://thekingsbible.com/Bible/1/1`
- 출애굽기 1장
  - `https://thekingsbible.com/Bible/2/1`

## 개역개정(NKRV) 상태

대한성서공회 개역개정 수집기 지원이 추가되었습니다.  
실행 시 `NKRV_ENTRY_URL` 또는 `--entry-url`로 대한성서공회 URL을 지정하고, 번역본은 `BIBLE_TRANSLATION_ID=2` 또는 `NKRV` 메타데이터로 맞추면 됩니다.

- [docs/bskorea_scraping_design.md](/mnt/c/workspace/python/BibleScrapper/docs/bskorea_scraping_design.md)

예시 URL:

- 레위기 11장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
- 레위기 27장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=27&sec=1&cVersion=&fontSize=15px&fontWeight=normal`
- 민수기 1장
  - `https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=num&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal`

개역개정 기본 엔트리 URL 환경변수는 아래 값을 기준으로 사용할 수 있습니다.

```env
NKRV_ENTRY_URL=https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal
```

예:

```bash
BIBLE_TRANSLATION_ID=2 \
NKRV_ENTRY_URL="https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal" \
python3 scrape_bible_to_db.py --start-book 1 --end-book 1
```

레위기 11장만 적재:

```bash
BIBLE_TRANSLATION_ID=2 \
NKRV_ENTRY_URL="https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal" \
python3 scrape_bible_to_db.py --start-book 3 --end-book 3 --start-chapter 11 --end-chapter 11
```

레위기 11장 smoke test만 실행:

```bash
NKRV_ENTRY_URL="https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal" \
python3 scrape_bible_to_db.py --test-book 3 --test-chapter 11
```

## 동작 요약

1. 설정된 번역본의 `bible_book(translation_id=...)`를 `book_order ASC`로 조회합니다.
2. chapter 목록을 생성하거나 발견합니다.
3. 기존 `bible_chapter`를 조회하고, 없는 chapter만 insert합니다.
4. 각 chapter의 기존 verse 번호를 조회하고, 없는 verse만 insert합니다.
5. book 단위로 commit하며, 실패 시 rollback 후 재시도합니다.

## 테스트

### 일반

```bash
python3 -m pytest -q
```

### WSL 전용 스크립트

```bash
bash scripts/run_tests_wsl.sh
bash scripts/run_tests_wsl.sh -k fallback
```

참고:

- 현재 환경에 `pytest`가 설치되어 있어야 합니다.
- Windows `.venv`와 WSL 환경은 분리해서 사용하는 것이 안전합니다.

## 네트워크 안정성

- `429/502/503/504` 응답은 자동 재시도합니다.
- `429`의 `Retry-After` 헤더가 있으면 해당 시간만큼 대기 후 재시도합니다.
- 429 발생 시 요청 속도를 자동으로 낮추고, 성공 시 점진적으로 복원합니다.
- 429 에러 페이지가 200으로 내려오는 경우도 감지해 재시도합니다.
- 비정상 verse(예: `429 Error`)는 삽입하지 않습니다.

## 성능 권장 인덱스

```sql
CREATE INDEX idx_chapter_book_id ON bible_chapter(book_id);
CREATE INDEX idx_verse_chapter_id ON bible_verse(chapter_id);
```
