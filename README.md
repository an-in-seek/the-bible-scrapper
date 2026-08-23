# Bible Scraper to PostgreSQL

성경 본문을 스크래핑해 PostgreSQL의 `bible_chapter`, `bible_verse`에 적재하는 도구입니다.

현재 기준으로 안정적으로 맞춰진 소스는 아래 8개입니다.

- `thekingsbible.com` KJV
- `bskorea.or.kr` NKRV(`version=GAE`)
- `biblegateway.com` WEB(`version=WEB`, World English Bible)
- `biblegateway.com` ASV(`version=ASV`, American Standard Version)
- `ebible.org` RVR1909(`spaRV1909`, Reina Valera 1909 — 스페인어)
- `ebible.org` SBLM(`spablm`, Santa Biblia libre para el mundo — 스페인어)
- `ebible.org` JPNMEB(`jpnm`, フリーダム・バイブル — 일본어)
- `jpn.bible` KOUGO(`kougo`, 口語訳聖書 1954/1955 — 일본어)

설계 문서:

- NKRV: [docs/nkrv-scraping-design.md](docs/nkrv-scraping-design.md)
- WEB: [docs/world-english-bible-scraping-design.md](docs/world-english-bible-scraping-design.md)
- ASV: [docs/american-standard-version-scraping-design.md](docs/american-standard-version-scraping-design.md)
- RVR1909: [docs/reina-valera-1909-scraping-design.md](docs/reina-valera-1909-scraping-design.md)
- SBLM: [docs/santa-biblia-libre-para-el-mundo-scraping-design.md](docs/santa-biblia-libre-para-el-mundo-scraping-design.md)
- JPNMEB: [docs/japanese-public-domain-scraping-design.md](docs/japanese-public-domain-scraping-design.md)
- KOUGO: [docs/japanese-colloquial-1955-scraping-design.md](docs/japanese-colloquial-1955-scraping-design.md)

## 주요 특징

- `bible_book`의 기존 row를 조회해 사용하며 book 자체는 생성하지 않습니다.
- `bible_chapter`, `bible_verse`는 기존 데이터를 재사용하고 없는 데이터만 insert 합니다.
- 장 단위로 `commit` 하며, 실패 시 진행 중이던 장만 `rollback` 하고 책 단위로 재시도합니다.
- 실행 시작 시 `bible_chapter`, `bible_verse`의 ID 시퀀스를 현재 `MAX(id)`에 맞춰 동기화합니다.
- `.env`를 자동 로드하되, 이미 셸에 설정된 환경변수는 덮어쓰지 않습니다.
- 소스와 번역본 메타데이터가 어긋나면 실행 초기에 오류로 중단합니다. 양방향으로 검사합니다.
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
- `scripts/check_translation_drift.py`: 적재된 번역본과 원문을 대조하는 읽기 전용 점검 도구
- `docs/nkrv-scraping-design.md`: NKRV 설계 문서
- `docs/world-english-bible-scraping-design.md`: WEB 설계 문서
- `docs/american-standard-version-scraping-design.md`: ASV 설계 문서
- `docs/reina-valera-1909-scraping-design.md`: RVR1909 설계 문서
- `docs/santa-biblia-libre-para-el-mundo-scraping-design.md`: SBLM 설계 문서
- `docs/japanese-public-domain-scraping-design.md`: JPNMEB(일본어) 설계 문서
- `docs/new-japanese-nt-scraping-design.md`: JPNLOC(일본어 신약) 설계 문서 (미구현)
- `docs/japanese-colloquial-1955-scraping-design.md`: KOUGO(일본어 口語訳 1954/1955) 설계 문서

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
WEB_ENTRY_URL=https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB
ASV_ENTRY_URL=https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV
RVR1909_ENTRY_URL=https://ebible.org/spaRV1909/GEN01.htm
SBLM_ENTRY_URL=https://ebible.org/spablm/GEN01.htm
JPNMEB_ENTRY_URL=https://ebible.org/jpnm/GEN01.htm
KOUGO_ENTRY_URL=https://jpn.bible/kougo/gen#1
```

`--entry-url`를 지정하지 않으면 기본 URL은 아래 순서로 결정됩니다.

1. `BIBLE_TRANSLATION_TYPE`(`KJV` / `NKRV` / `WEB` / `ASV` / `RVR1909` / `SBLM` / `JPNMEB` / `KOUGO`)에 해당하는 환경변수
2. `BIBLE_TRANSLATION_ID=2` 또는 `BIBLE_TRANSLATION_NAME=개역개정`이면 `NKRV_ENTRY_URL`
3. `BIBLE_LANGUAGE_CODE`로 좁혀지는 소스가 하나면 그 값
   - `ko` -> `NKRV_ENTRY_URL`
   - `en` -> `KJV_ENTRY_URL` / `WEB_ENTRY_URL` / `ASV_ENTRY_URL` 중 설정된 것
   - `es` -> `RVR1909_ENTRY_URL` / `SBLM_ENTRY_URL` 중 설정된 것
   - `ja` -> `JPNMEB_ENTRY_URL` / `KOUGO_ENTRY_URL` 중 설정된 것
4. 설정된 엔트리 URL이 하나뿐이면 그 값
5. 여러 개가 남으면 `NKRV` -> `KJV` -> `WEB` -> `ASV` -> `RVR1909` -> `SBLM` -> `JPNMEB` -> `KOUGO` 순으로 선택
6. 아무것도 없으면 내장 기본값 `https://thekingsbible.com/Bible/1/1` 사용

주의: `BIBLE_LANGUAGE_CODE`만으로는 소스가 특정되지 않습니다.  
`en`(KJV / WEB / ASV), `es`(RVR1909 / SBLM), `ja`(JPNMEB / KOUGO) 모두 소스가 둘 이상이라,  
해당 엔트리 URL이 여러 개 설정된 상태에서 언어 코드만 주면 실행이 중단됩니다.  
이때는 `BIBLE_TRANSLATION_TYPE`을 지정하거나 `--entry-url`을 명시해야 합니다.

`BIBLE_TRANSLATION_ID`는 엔트리 URL 선택에 쓰이지 않습니다.  
ID만 지정하면 경고 없이 다른 소스가 선택될 수 있으므로, `BIBLE_TRANSLATION_TYPE`이나 `--entry-url`을 함께 쓰세요.

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
BIBLE_TRANSLATION_NAME=your_nkrv_translation_name
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
3. 각 chapter를 요청해 절을 파싱합니다.
4. 파싱에 성공한 chapter만 `bible_chapter` row를 확보합니다.
5. 기존 `verse_number`를 조회하고 없는 절만 insert 합니다.
6. **각 chapter가 끝날 때마다 `commit`** 합니다.
7. 실패하면 진행 중이던 chapter만 `rollback` 되고, 책 단위로 재시도합니다.

즉 chapter row와 그 절들은 같은 트랜잭션에서 커밋됩니다.  
책 도중에 실패해도 이미 끝난 chapter는 보존되며, 재시도 시 기존 절은 건너뜁니다.

### 안전 장치

- 절이 하나도 파싱되지 않은 chapter는 **DB에 쓰기 전에** 건너뜁니다. 빈 chapter row가 남지 않습니다.
- chapter의 첫 절 번호가 `1`이 아니면 해당 chapter insert를 건너뜁니다.
- 책 전체에서 절을 하나도 얻지 못하면 오류로 처리합니다. 이 시점에는 커밋된 것이 없습니다.
- 기존 절 번호가 있으면 중복 insert 하지 않습니다.

### 원문이 개정되는 경우

insert가 **없는 절만** 채우는 방식이므로, 원문이 나중에 수정되어도 재실행으로는 반영되지 않습니다.
확정 판본에는 문제가 없지만, 개정이 진행 중인 소스에서는 최초 적재본이 그대로 남습니다.

원문이 바뀌었는지 확인하려면 `scripts/check_translation_drift.py`를 사용합니다. **DB에 쓰지 않습니다.**

```bash
# 1) 서버가 페이지를 언제 재생성했는지만 확인 (요청 1건)
python3 scripts/check_translation_drift.py --entry-url <URL> --head-only

# 2) 원문을 다시 파싱해 DB와 절 단위로 대조 (차이가 있으면 종료 코드 1)
python3 scripts/check_translation_drift.py --translation-id <ID> --entry-url <URL>   --start-book 1 --end-book 1
```

차이가 확인되면 해당 번역본의 `bible_verse`와 `bible_chapter`를 지우고 다시 적재해야 합니다.
`bible_chapter`와 `bible_verse`에는 외래 키 제약이 없으므로 **반드시 절을 먼저 지웁니다.**
장을 먼저 지우면 절이 고아로 남아 책을 경유하는 쿼리로 찾을 수 없게 됩니다.
전체 절차는 [docs/santa-biblia-libre-para-el-mundo-scraping-design.md](docs/santa-biblia-libre-para-el-mundo-scraping-design.md) 9.3절에 정리되어 있습니다.

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

### 3. WEB `biblegateway.com`

- URL 규칙: `https://www.biblegateway.com/passage/?search={영문 책명}%20{장 번호}&version=WEB`
- 책명은 코드 내 66권 영문 책명 상수를 사용합니다. `bible_book.book_key`는 사용하지 않습니다.
- 장 수는 KJV와 동일한 정경 66권 chapter count를 사용합니다.
- `version`은 엔트리 URL의 값을 승계하며, 없으면 `WEB`입니다.

권장 엔트리 URL:

```env
WEB_ENTRY_URL=https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB
```

예:

- 창세기 1장: `https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB`
- 사무엘상 1장: `https://www.biblegateway.com/passage/?search=1%20Samuel%201&version=WEB`
- 유다서: `https://www.biblegateway.com/passage/?search=Jude%201&version=WEB`

저장 규칙:

- 절 번호는 화면 표시 숫자가 아니라 `span.text`의 클래스 토큰(`Gen-2-1`)에서 읽습니다.
- 각주(`[a]`), 상호 참조(`(A)`), 시편 표제(`A Psalm by David.`)는 절 본문에 포함하지 않습니다.
- 시가 본문에서 여러 조각으로 나뉜 절은 하나로 병합합니다.
- WEB이 번역하지 않는 4개 구절(Luke 17:36, Acts 8:37, Acts 15:34, Acts 24:7)은 절 번호를 건너뛰지 않고 `(omitted)`로 저장합니다.
  - 개역개정이 같은 구절을 `(없음)`으로 표기하는 관례를 따른 것입니다.
  - 덕분에 "절 번호는 1부터 연속"이 불변식이 되어, 구멍이 생기면 곧바로 스크래핑 결함으로 판정할 수 있습니다.

### 4. ASV `biblegateway.com`

WEB과 동일한 어댑터를 사용하며 `version`만 다릅니다. 파서는 공유합니다.

권장 엔트리 URL:

```env
ASV_ENTRY_URL=https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV
```

WEB과 다른 점:

- ASV는 편집자 소제목(`h3`)과 시편 표제(`h4.psalm-title`)를 함께 사용하며, 둘 다 1절 클래스를 갖습니다. 파서가 제거하므로 절 본문에 섞이지 않습니다.
- ASV가 본문에서 빼는 절은 스팬 자체가 없어 `(omitted)` 마커가 생성되지 않습니다. 절 번호에 구멍이 생기며, 처리 방향은 설계 문서 7절을 참고하세요.
- 각주가 WEB보다 3~5배 많습니다.

### 5. RVR1909 `ebible.org`

- URL 규칙: `https://ebible.org/{역본코드}/{책코드}{장번호}.htm`
- 책 코드는 USFM 대문자 3자(`GEN`, `PSA`, `3JN`)입니다.
- **장 번호 자릿수가 책마다 다릅니다.** 시편만 3자리(`PSA023`), 나머지는 2자리(`GEN50`)입니다.
- 역본 코드는 엔트리 URL의 첫 경로 세그먼트를 승계하므로 다른 eBible 역본에도 재사용됩니다.

권장 엔트리 URL:

```env
RVR1909_ENTRY_URL=https://ebible.org/spaRV1909/GEN01.htm
```

저장 규칙:

- 절 본문이 스팬 안에 없어, `span.verse` 마커 사이의 텍스트를 누적합니다.
- 절 번호는 표시 텍스트가 아니라 `id` 속성(`V12`)에서 읽습니다.
- 내비게이션(`ul.tnav`), 책 제목(`div.mt`), 저작권 표기는 제외합니다.
- 보충어(`span.add`)는 본문으로 유지합니다.
- **시편 표제는 절 본문에 포함됩니다.** 원문이 별도 마크업 없이 1절 안에 넣기 때문이며, WEB/ASV에서 표제를 제외한 것과 다릅니다.

RV1909는 퍼블릭 도메인입니다.

### 6. SBLM `ebible.org`

Santa Biblia libre para el mundo. RVR1909와 같은 사이트·같은 렌더러라 URL 규칙과 절 마커 구조가 동일하며, 역본 코드만 다릅니다.

```env
SBLM_ENTRY_URL=https://ebible.org/spablm/GEN01.htm
```

RVR1909와 다른 점:

- 한 장이 여러 블록(`div.p`, `div.q`, `div.q2`)으로 쪼개져 있어, 한 절이 블록 경계를 넘어갑니다. 블록이 바뀔 때 공백 하나로 이어 붙입니다.
- 절과 절 **사이**에 표제가 들어갑니다. 시편 이합체 표제(`div.d`)와 아가 화자 표시(`div.sp`)가 그렇습니다. 제거하지 않으면 앞뒤 절 본문에 섞여 들어가는데, 절 수·번호 연속성 검사를 모두 통과하므로 자동 검증으로는 잡히지 않습니다.
- **시편 표제는 저장하지 않습니다.** 원문이 표제를 1절 마커 밖의 별도 블록에 두기 때문이며, KJV/NKRV/WEB/ASV와 같은 처리입니다. RVR1909만 표제를 1절에 담고 있습니다.
- 예수 말씀 서식(`span.wj`)은 본문으로 유지합니다.
- 원문이 비워 둔 네 절(눅 17:36, 행 8:37 · 15:34 · 24:7)은 `(omitted)`로 기록합니다. WEB과 같은 절이며, 절 번호를 연속으로 유지해 진짜 누락이 실패로 드러나게 하기 위함입니다. 판정 근거는 각주의 존재이고, 각주 없이 빈 마커는 그대로 건너뜁니다. RVR1909는 이 네 절을 본문으로 갖고 있어 표기가 생기지 않습니다.
- 각주 마커(`a.notemark`)는 각주 본문(`span.popup`)을 자식으로 품고 있어 함께 제거됩니다.

**본문이 개정 중인 초안입니다.** 페이지 하단에 `Este es un borrador de traducción`이 표기되어 있고 원문이 수시로 갱신됩니다. 적재 이후의 수정은 재실행으로 반영되지 않으므로, [원문이 개정되는 경우](#원문이-개정되는-경우)의 절차를 따르세요. 퍼블릭 도메인입니다.

### 7. JPNMEB `ebible.org`

フリーダム・バイブル(Japanese Freedom Bible). RVR1909·SBLM과 같은 사이트·같은 렌더러이며 역본 코드만 다릅니다.

```env
JPNMEB_ENTRY_URL=https://ebible.org/jpnm/GEN01.htm
```

일본어 고유의 처리:

- **블록 경계 공백을 넣지 않습니다.** 일본어는 단어 사이를 띄우지 않으므로, 스페인어·영어에 필요한 결합 공백이 여기서는 본문을 오염시킵니다(표본 절의 49%). 양쪽이 모두 CJK 문자일 때만 공백을 제거합니다.
- **한글은 이 규칙에서 제외됩니다.** 한국어는 단어를 띄어 쓰므로, 범위에 포함하면 NKRV 본문이 망가집니다.
- 원문이 비워 둔 다섯 절(눅 17:36, 행 8:37 · 15:34 · 24:7, **롬 16:25**)은 `(omitted)`로 기록합니다. 앞의 넷은 WEB과 같고 롬 16:25는 이 역본에만 있습니다.
- 책명은 `ul.tnav`에서 가져옵니다. `div.mt`는 서수가 빠져 `書` 하나에 5권, `福音書` 하나에 4권이 뭉칩니다.

SBLM과 마찬가지로 **개정 중 초안**(`これは翻訳の草案です`)이므로 [원문이 개정되는 경우](#원문이-개정되는-경우)의 절차가 적용됩니다. 퍼블릭 도메인입니다.

### 8. KOUGO `jpn.bible`

口語訳聖書(신약 1954 / 구약 1955). 일본성서협회 발행분이며 일본 기준 보호기간이 만료된 판본입니다.
자세한 근거와 관할별 차이는 [설계 문서](docs/japanese-colloquial-1955-scraping-design.md) 1장에 있습니다.

```env
KOUGO_ENTRY_URL=https://jpn.bible/kougo/gen#1
```

이 소스만의 처리:

- **페이지가 책 단위입니다.** 장 단위 URL이 없어 장 번호를 프래그먼트(`#3`)로 넘기고, 책 페이지를
  한 번 받아 장별로 쪼개 씁니다. 전권 적재의 HTTP 요청이 **66회**뿐입니다.
- **루비(후리가나)를 제거합니다.** 지우지 않으면 본문이 `はじめに神（かみ）は…`가 됩니다.
  `get_text()`로 보면 멀쩡해 보이는 종류의 오염이라 파서 결과로 확인해야 합니다.
- **병합 절 16건**은 범위의 모든 번호에 같은 본문을 저장합니다(시 132:3-5 등).
- **분할 절 1건**(출 22:3)은 문서 순서가 아니라 `a` → `b` 순서로 합칩니다.
- 문제 구절의 여는 괄호가 앞 절 끝에 남아 있어(19절) 다음 절 앞으로 옮깁니다.
- 시편 표제(`<title type="psalm">`) 138개는 저장하지 않습니다. 다른 역본과 같은 처리입니다.

적재 결과는 66권 / 1,189장 / **31,104절**이며 KJV와는 4개 장(시 47, 고후 13, 요삼 1, 계 12)에서만
절 수가 다릅니다. 원문이 비워 둔 절이 없어 `(omitted)`는 0건입니다.

**본문에 일본성서협회가 이후 訂正한 표현이 그대로 들어 있습니다**(「おしの霊」「らい病人」 등).
만료된 것은 1954/1955 원본이고 訂正된 낱말에는 저작권이 남아 있어, 訂正 후 본문을 쓰려면
협회의 허락 절차가 필요합니다.

## 네트워크와 재시도

- `429`, `502`, `503`, `504` 응답은 자동 재시도합니다.
- `429` 응답에 `Retry-After`가 있으면 해당 값을 우선 사용합니다.
- 본문에 `Too Many Requests`, `429 Error` 같은 마커가 있는 200 응답도 재시도 대상으로 처리합니다.
- 요청 성공 후에는 throttle을 서서히 낮추고, 실패가 누적되면 요청 간 대기 시간을 늘립니다.
- chapter 간에는 scraper 내부의 polite delay가 적용되고, book 간에는 추가로 5초 대기합니다.
- 응답 `Content-Type`에 charset이 없으면 본문 기반 추정으로 디코딩합니다. eBible이 여기 해당하며, 이 처리가 없으면 스페인어 악센트가 전부 깨집니다.
- BibleGateway는 `robots.txt`에 `Crawl-delay: 15`를 명시하므로, 이 소스에서는 요청 간격 하한이 15초로 강제됩니다.
  - 생성자에 더 짧은 값을 넘겨도 15초 미만으로 내려가지 않습니다.
  - 66권 전권 적재는 1,189 요청이며 약 5시간이 걸립니다.

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

### WEB 실행

```bash
export BIBLE_TRANSLATION_TYPE=WEB
export BIBLE_TRANSLATION_NAME="World English Bible"
export BIBLE_LANGUAGE_CODE=en
export WEB_ENTRY_URL="https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB"
python3 scrape_bible_to_db.py --start-book 1 --end-book 5
```

### ASV 실행

```bash
export BIBLE_TRANSLATION_TYPE=ASV
export BIBLE_TRANSLATION_NAME="American Standard Version"
export BIBLE_LANGUAGE_CODE=en
export ASV_ENTRY_URL="https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV"
python3 scrape_bible_to_db.py --entry-url "$ASV_ENTRY_URL" --start-book 1 --end-book 5
```

### WEB smoke test

```bash
export WEB_ENTRY_URL="https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB"
python3 scrape_bible_to_db.py --test-genesis1
python3 scrape_bible_to_db.py --test-book 19 --test-chapter 119
python3 scrape_bible_to_db.py --test-book 65 --test-chapter 1
```

전권 적재 구간 분할과 완료 검증 쿼리는 [설계 문서 11절](docs/world-english-bible-scraping-design.md)에 있습니다.

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

소스와 번역본 메타데이터가 어긋난 경우입니다. 양방향으로 검사합니다.

- 소스가 요구하는 번역본이 아닌 경우 (예: `?version=ASV`에 WEB 메타데이터)
- 번역본이 요구하는 소스가 아닌 경우 (예: `thekingsbible.com`에 ASV 메타데이터)

각 번역본의 소스/버전 요건은 `TRANSLATION_SOURCE_REQUIREMENTS` 표에 정의되어 있습니다.

### `Ambiguous entry URL`

- `KJV_ENTRY_URL`과 `WEB_ENTRY_URL`이 함께 설정된 상태에서 `BIBLE_LANGUAGE_CODE=en`만 준 경우입니다.
- `BIBLE_TRANSLATION_TYPE`을 지정하거나 `--entry-url`을 명시하면 해결됩니다.

### `Parsed 0 verses across all chapters`

- 해당 책에서 유효한 본문을 하나도 추출하지 못한 경우입니다.
- 이 시점에는 커밋된 chapter가 없으며, 빈 스크랩 결과를 남기지 않기 위해 의도적으로 실패 처리합니다.
