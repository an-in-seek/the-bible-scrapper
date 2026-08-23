# 口語訳聖書(1954/1955) 본문 스크래핑 개발 설계

## 1. 목적

일본성서협회 『口語訳聖書』(신약 1954 / 구약 1955) 66권 전체를 스크래핑하여 기존 PostgreSQL 스키마(`bible_chapter`, `bible_verse`)에 적재한다.

### 1.1 이 문서가 다루는 범위

이 판본은 [일본어 퍼블릭 도메인 설계](japanese-public-domain-scraping-design.md)에서 **한 번 배제된 적이 있다.** 그 문서는 배포처(일본어 위키문헌)가 저작권 침해 여부를 심사 중이라는 이유로 채택하지 않았다. 이번 요청은 같은 판본을 다시 검토해 달라는 것이므로, 이 문서는 **그때 판단을 뒤집을 근거가 있는지부터** 확인한다([1.2](#12-제시된-근거-검토)).

결론부터 말하면 두 판단은 **서로 모순되지 않는다.** 관할이 다르다.

### 1.2 제시된 근거 검토

요청과 함께 제시된 표는 이렇게 적고 있다.

```
口語訳聖書 (Kougo-yaku)  JapKougo / japkougo  1954/1955  구약+신약
✅ Public Domain*   1954 신약 + 1955 구약. CrossWire도 PD 모듈로 배포
```

**별표가 핵심이다.** 세 배포처의 표기를 각각 조회한 결과는 다음과 같다.

| 확인처 | 표기 (실측) |
| --- | --- |
| CrossWire `JapKougo` 모듈 | `Distribution License: Public Domain` / `The copyright for the source text "is expired at 1 Jan 2006"` |
| 일본성서협회 (권리자 본인) | 「1955年に発行した『口語訳聖書』は、著作権法に基づき、その著作権の保護期間が終了しています」 |
| 일본어 위키문헌 삭제 심의 | 「1954年発表の作品であれば、日本においては2004年に保護期間満了となりますが、1996年時点では保護期間中ですので、アメリカ合衆国で著作権が復活します。現行の著作権法では2049年まで著作権の保護期間となり」 |

세 표기가 모두 사실이다. 정리하면:

| 관할 | 상태 | 근거 |
| --- | --- | --- |
| **일본** | **만료** — 신약 2005-01-01, 구약 2006-01-01 | 단체명의 저작물 공표 후 50년. 2018년 70년 연장 이전에 이미 만료되어 부활하지 않는다. 권리자 본인이 만료를 명시 |
| **미국** | **존속** — 2049/2050년까지 | URAA 복원. 1996-01-01 기준 본국에서 보호 중이었으므로 공표 후 95년으로 복원 |
| **한국** | 일본을 따라 **만료** | 저작권법 제3조 제4항: "제1항 및 제2항에 따라 보호되는 외국인의 저작물이라도 그 외국에서 보호기간이 만료된 경우에는 이 법에 따른 보호기간을 인정하지 아니한다" |

앞 문서가 위키문헌을 근거로 배제한 것은 **위키미디어가 미국 서버에서 운영되어 미국 기준 퍼블릭 도메인만 수록**하기 때문이다. 실제로 본문 문서는 현재 **본문이 삭제된 상태**다(2026-08-23 조회). 즉 그 판단은 "위키문헌에서 가져올 수 없다"는 뜻이었고, 이 판본 자체가 어디서도 쓸 수 없다는 뜻은 아니었다.

이 프로젝트의 DB와 사용자는 한국에 있으므로 위 표의 세 번째 줄이 적용된다. 다만:

> 이 문서는 법률 자문이 아니다. 위 내용은 배포처·권리자·심의 기록의 표기를 조회한 결과이며, 실제 채택 판단은 사용자 몫이다. **미국에 서비스를 배포할 계획이 있다면 위 표의 두 번째 줄이 그대로 문제가 된다.**

### 1.3 권리자가 붙인 두 가지 단서

일본성서협회는 만료를 인정하면서 같은 문장에 두 가지를 덧붙였다. 둘 다 **적재 대상을 좌우한다.**

```
しかし、著作者人格権は失われませんので、勝手に改変、訂正をすることはできません
また、下記の表にある訂正された単語や文章の著作権は保護されています。
改訂された単語や文章を含む口語訳聖書の使用に関しては … 使用許諾を申請していただきますようお願いいたします。
```

1. **동일성유지권**은 만료되지 않는다 → 본문을 임의로 수정하지 않는다. 이 설계가 파서에서 하는 일은 마크업 제거와 절 경계 정리뿐이고, 낱말을 바꾸지 않는다([4.6](#46-괄호가-앞-절-끝에-달린다)의 괄호 이동이 유일한 문자 단위 조작이며, 문자를 지우지 않고 옮기기만 한다).
2. **1975/1984/2002년에 고친 낱말·문장은 여전히 저작권이 있다.** 협회가 공개한 訂正一覧에는 **132행**이 있다. 따라서 **訂正 이후 본문을 올린 사이트를 소스로 삼으면 허락이 필요하다.** 만료된 것은 1954/1955 원본뿐이다.

두 번째 단서가 소스 선택을 사실상 결정한다([1.4](#14-후보-소스-비교)).

| 협회 訂正 예시 (실측) | 訂正前 | 訂正後 |
| --- | --- | --- |
| マコ 9:17 | おしの霊 | 口をきけなくする霊 |
| マコ 9:25 | おしとつんぼの霊 | 言うことも、聞くこともさせない霊 |
| マコ 1:40 | らい病人 | 重い皮膚病にかかった人 |

> **적재되는 본문에는 위 왼쪽 열의 표현이 그대로 들어간다.** 권리 관계가 깨끗한 판본이 곧 협회가 공개적으로 고친 차별 표현을 담고 있는 판본이라는 뜻이다. 서비스에 노출할 때 이 점을 알고 있어야 한다. 訂正 후 본문을 쓰려면 협회 허락 절차를 밟아야 하며, 그것은 이 문서의 범위 밖이다.

### 1.4 후보 소스 비교

**eBible.org에는 口語訳이 없다.** `translations.csv`(731KB, 실측)에서 `jpn` 행은 `jpn1965`와 `jpnm` **둘뿐**이다. 즉 기존 eBible 어댑터를 그대로 재사용하는 길은 없고, **소스를 하나 새로 붙여야 한다.**

| 후보 | 판본 | 상태 (실측) | 판정 |
| --- | --- | --- | --- |
| **jpn.bible/kougo** | 원본 1954/1955 | 66개 책 페이지, 절 번호 결함 0 | **채택** |
| bible.religious-life.com | 원본 1954/1955 | 1,189개 장 페이지, 절 번호 결함 12개 장 | 제2 증인([7.6](#76-제2-증인-대조)) |
| baiburu.com | 원본 1954/1955 | 1,189개 장 페이지, **출 22:3 본문 소실** | 제외([1.5](#15-추가-검토-baiburucom-과-stepbible)) |
| stepbible.org (`JapKougo`) | 원본 1954/1955 | REST API, **시 130~133 빈 응답** | 제외([1.5](#15-추가-검토-baiburucom-과-stepbible)) |
| wordproject.org/bibles/jp | **2002 訂正 후** | 절 번호 정상 | **제외** — 협회가 저작권을 주장하는 訂正 본문 |
| ja.wikisource | 원본 | **본문 삭제됨** (저작권 심의) | 제외 |
| bible.salterrae.net | 원본 | **DNS 응답 없음** — 기본/8.8.8.8/1.1.1.1 모두 `SERVFAIL` | 제외 (사이트 소멸) |
| CrossWire `JapKougo` 모듈 | 원본 | SWORD 모듈(zip), HTML 아님 | 제외 — 스크래퍼의 대상이 아니다 |

판본 판별은 협회 訂正一覧과 대조해서 한다. wordproject는 マコ 9:17이 「口をきけなくする霊」인데, 이는 訂正一覧의 **訂正後** 문구와 정확히 일치한다. 나머지 네 곳(jpn.bible, religious-life, baiburu, STEPBible)은 전부 「おしの霊」이고 マコ 9:25도 「おしとつんぼの霊」이므로 **원본 판본**이다.

### 1.5 추가 검토: baiburu.com 과 STEPBible

둘 다 원본 판본을 싣고 있고 절 번호도 대체로 깨끗하다. 그런데 병합·분할·절 구분이 갈리는 지점만 골라 실측하면 **양쪽 모두 본문이 빈다.**

**baiburu.com** — 장 단위 URL(`/books/{book}/{n}/`)이라 구조 변경이 필요 없고, `div.verse-row[data-verse-number]`로 절 번호가 속성에 들어 있다. 여기까지는 이 저장소에 가장 잘 맞는다. 그러나:

| 장 | 절 번호 (실측) | 문제 |
| --- | --- | --- |
| 출 22 | `1, 2, 4, 5 …` (30절) | **3절이 통째로 없다.** 「しかし日がのぼって後ならば」「身を売られる」「必ず償わなければ」 세 문구 모두 페이지 전체에서 **검색되지 않는다** |
| 롬 16 | `… 23, 24, 26, 27` | 병합 절을 **범위의 뒤 번호**에만 싣는다. 25가 사라진다 |
| 시 132 | `1, 2, 5, 6 …` | 3-5 병합 → 3과 4가 사라진다 |

본문이 실제로 사라지는 것은 출 22:3 하나지만, **자동 검사로는 잡히지 않는다.** 연속성 검사는 병합 16건 때문에 어차피 걸리므로 "출 22도 병합이겠거니" 하고 묻힌다. 이 한 절을 찾으려면 다른 소스와 대조하는 수밖에 없다.

절 구분은 jpn.bible과 일치한다(시 47 = 10, 계 12 = 18, 요삼 = 15, 고후 13 = 13). 페이지가 장당 104~136 KB로 무거워 전권이 약 133 MB다(jpn.bible은 66요청 25 MB, 둘 다 비압축 기준). `robots.txt`에는 Cloudflare Content-Signal이 있어 `ai-train=no, use=reference`를 선언한다. 적재는 학습이 아니지만, **운영자가 권리를 유보한다고 밝힌 사이트**라는 점은 아무 제한도 걸지 않은 jpn.bible과 다르다.

**STEPBible** — 화면은 자바스크립트로 그려지므로 HTML에는 본문이 없다. 실제로 쓸 수 있는 것은 REST 엔드포인트다.

```
https://www.stepbible.org/rest/bible/getBibleText/JapKougo/Gen.1/V
→ {"value": "<span class='verse'><a name='Gen.1.1' class='verseLink'>
             <span class='verseNumber'>1</span></a>はじめに神は天と地とを創造された。</span> …"}
```

`a.verseLink[name]`이 OSIS 참조(`Gen.1.1`)라 절 번호가 기계 판독 가능하고, 루비가 없어 본문이 깨끗하다. 여기까지는 좋다. 그러나:

- **시편 130·131·132·133이 빈 응답이다.** `<h2>Psalms 132</h2>` 뒤에 아무 절도 없다. 절 하나만 요청해도(`Ps.131.1`) 마찬가지다. 시 3·47·49·89·105·106·119는 정상이므로 특정 구간의 문제다.
- **절 구분이 인쇄본 口語訳과 다른 곳이 있다.** 시 47 = 9절(사이트들은 10), 계 12 = 17절(18), 요삼 = 14절(15). CrossWire 모듈이 표준 절 구분으로 맞춰져 있기 때문으로 보인다. 어느 쪽이 맞다기보다 **다른 체계**이며, 이 문서가 기준으로 삼은 [7.4](#74-kjv-대조--네-개-장)의 기대값이 통째로 달라진다.
- 정적 페이지가 아니라 **연구 서비스의 API**다. 1,189회를 때리는 용도로 공개된 것이 아니다.

**두 후보는 증인으로도 쓸 수 없다.** 처음에는 계보가 다르니 표본 판정에 쓸 수 있으리라 보고 실제로 시도했는데, 그 전제가 틀렸다. jpn.bible 본문에 있는 디지털화 흔적이 **두 곳에 똑같이** 남아 있다.

```
2사무 19:32   jpn.bible  … 年老いた人で八十{歳であった …   ← 여는 중괄호
              STEPBible  … 年老いた人で八十{歳であった …
              baiburu    … 年老いた人で八十{歳であった …
              religious-life … 年老いた人で八十歳であった …
요한 1:27     jpn.bible / STEPBible / baiburu  … わたしのあとにあとにおいでになる …   ← 중복
              religious-life                    … わたしのあとにおいでになる …
```

인쇄본에 중괄호가 있을 리 없다. **jpn.bible·baiburu·CrossWire 모듈은 하나의 디지털 원본에서 갈라져 나온 것**이고, 셋이 일치한다는 사실은 옳다는 증거가 되지 않는다. 이 계보 밖에 있는 것은 religious-life뿐이다([7.6](#76-제2-증인-대조)).

---

## 2. 결론 먼저

1. **새 소스 어댑터가 필요하다.** eBible에 이 판본이 없으므로 `_is_jpnbible_source()` 이하 한 벌을 추가한다. 기존 소스 코드 경로는 건드리지 않는다.
2. **URL 규칙이 지금까지와 다르다. 페이지가 책 단위다.** `https://jpn.bible/kougo/gen` 하나에 창세기 50장이 모두 들어 있다. 장 단위 URL은 **존재하지 않는다**(`/kougo/ps/3`, `/kougo/ps3`, `/kougo/ps.3` 모두 404 실측). 따라서 **책 페이지 캐시 + 장 분리**가 이 설계의 핵심 구조 변경이다([5.1](#51-scraperpy--책-페이지-캐시와-장-분리)).
3. **요청 수가 1,189회에서 66회로 줄어든다.** 캐시 적중 시 HTTP 요청이 없으므로 `_request_html()` 안의 지연도 발생하지 않는다. 전권 적재의 네트워크 부하가 다른 어떤 소스보다 낮다.
4. **DOM은 지금까지 본 소스 중 가장 규칙적이다.** 66권 전체 태그 조사 결과 나오는 태그 이름이 12종(`main h1 div h2 p span ruby rt rp br a title`)뿐이고, `div` 개수가 **1,189개**로 `KJV_CHAPTER_COUNTS` 합계와 정확히 일치한다. 각주·상호참조·소제목이 아예 없다.
5. **가장 큰 파서 함정은 루비(후리가나)다.** 지우지 않으면 절 본문이 「はじめに神（かみ）は天（てん）と…」가 된다. 확인이 까다로운 이유는 `get_text()`로 보면 멀쩡하기 때문이다 — bs4는 루비 문자열을 별도 타입으로 분류해 `get_text()`에서 빼지만, 그 타입이 `NavigableString`의 하위 클래스라 **이 저장소 파서들이 쓰는 `descendants` 순회는 그대로 통과시킨다**([4.3](#43-함정-1-루비를-지우지-않으면-읽기가-본문에-섞인다)).
6. **병합 절 16건, 분할 절 1건이 있다.** 소스가 기계 판독 가능한 형태로 표기한다(`id="16:25 Rom.16.26"`, `id="22:3!a"`). 저장 방식은 [jpn1965 설계 §4.4](new-japanese-nt-scraping-design.md)와 같은 결정이며 **B안(범위 전체에 같은 본문)** 을 권고한다.
7. **적재 예상치는 66권 / 1,189장 / 31,104절이다.** 프로토타입으로 66권 전체를 파싱해 얻은 값이며, 연속성이 깨진 장 0개, 빈 절 0개다. KJV(31,102)와는 **4개 장에서만** 다르다([7.4](#74-kjv-대조--네-개-장)).
8. **기존 동작이 하나 바뀐다.** `ja` 역본이 둘이 되므로 `BIBLE_LANGUAGE_CODE=ja`만으로는 엔트리 URL이 정해지지 않고 **예외가 난다.** `en`에서 이미 겪은 것과 같은 모호성이며, 실행해서 확인했다([5.4](#54-기존-동작이-바뀐다--일본어-역본이-둘이-된다)).
9. **DB 작업은 SBLM/JPNMEB와 같은 양이다.** CHECK 제약 1개 값, `bible_translation` 1행, `bible_book` 66행. `bible_book_description`의 `ja` 66행은 이미 있으므로 추가 작업이 없다.

---

## 3. 실측 검증 범위

이 문서의 모든 수치는 실제로 페이지를 받아 확인했다. 추정으로 쓴 문장은 없다.

| 검증 | 방법 | 결과 |
| --- | --- | --- |
| 판본 권리 관계 | CrossWire 모듈 정보, 일본성서협회 訂正一覧, 위키문헌 삭제 심의 원문 | [1.2](#12-제시된-근거-검토) |
| 판본 동일성 | 訂正一覧 대조 (マコ 9:17 / 9:25 / 1:40) | 원본 판본 확인, wordproject는 訂正 후 |
| eBible 미보유 | `ebible.org/Scriptures/translations.csv` 전체 조회 | `jpn` 행 2개(`jpn1965`, `jpnm`)뿐 |
| 소스 생존 | salterrae DNS 조회 (3개 리졸버) | 전부 `SERVFAIL` |
| 추가 후보 | baiburu.com 14개 장, STEPBible REST 20개 응답 | [1.5](#15-추가-검토-baiburucom-과-stepbible) |
| 소스 계보 | 네 소스의 동일 흔적(`八十{歳` 등) 대조 | jpn.bible·baiburu·CrossWire가 한 계보 |
| 불일치 판정 | 표기 차이 25건을 계보 밖 증인으로 판정 | jpn.bible 16 / religious-life 5 / 구두점 4 |
| 문자 검사 | 있을 수 없는 문자·중복 구두점 전권 스캔 | jpn.bible 4절, religious-life 2절 |
| URL 규칙 | `sitemap.xml` 전량 + 장 단위 URL 3가지 시도 | 책 66개 + 색인, 장 URL 404 |
| DOM 구조 | **66권 전권** 태그/클래스 집계 | [4.2](#42-dom-구조) |
| 절 구조 | **1,189장 전체** 프로토타입 파싱 | 31,104절, 결함 0 |
| 루비 처리 | bs4 4.14.3 노드 타입 확인 + 본문 대조 | [4.3](#43-함정-1-루비를-지우지-않으면-읽기가-본문에-섞인다) |
| 병합·분할 | 전권 `id` 속성 조사 | 병합 16, 분할 1 |
| 괄호 위치 | 전권 절 말미 문자 조사 | 19절 |
| 제2 증인 대조 | religious-life **1,189장 전량** 크롤 후 절 단위 비교 | 일치 30,983 / 불일치 122 |
| 대조 기준 | KJV·JPNMEB 장별 절 수 비교(DB 질의) | 차이 4개 장 / 6개 장 |
| DB 현황 | `bible_translation`, CHECK 제약, `bible_book_description` 조회 | [6.1](#61-현재-상태-실측) |

### 3.1 확인하지 못한 것

같은 무게로 적어 둔다.

1. **아직 구현하지 않았고 한 번도 실행하지 않았다.** 위 수치는 전부 별도로 만든 프로토타입 파서의 결과다. 저장소 코드 경로(`_extract_verses` → `_sanitize_verses` → DB)로 돌린 값이 아니다. 적재 전까지 31,104는 **예측**이다.
2. **인쇄본을 보지 못했다.** 세 소스가 공유하는 읽기(「人人」, 「主に宮」 등)가 1955년 인쇄본에 그대로 있는 것인지, 공통 조상의 디지털화 흔적인지 **가릴 수 없다.** [7.6](#76-제2-증인-대조)의 판정은 "계보 밖 증인이 다르게 읽는다"까지이고 그 이상은 아니다.
3. **법적 성격 판단은 하지 않았다.** 이 판본이 단체명의 저작물이라 공표 후 50년이 적용되는지는 확인 대상이 아니었다. [1.2](#12-제시된-근거-검토)는 권리자·배포처·심의 기록이 **그렇게 적고 있다**는 사실만 옮긴 것이다.
4. **책 페이지 캐시가 `--resume`·장 범위 지정·책 재시도와 어떻게 맞물리는지 실행으로 확인하지 않았다.** 설계상 문제가 없어야 하지만 근거는 코드를 읽은 것뿐이다.
5. **religious-life 결함 12개 장은 라벨 이상으로만 찾은 것이다.** 라벨이 정상인 채 본문 경계만 어긋난 경우는 라벨 검사로 잡히지 않고, 두 증인 대조에서 44건이 따로 나왔다.

---

## 4. 대상 페이지 특성

### 4.1 URL 규칙 — 책 단위 한 페이지

```
https://jpn.bible/kougo/{book_slug}       # 책 전체 (장은 #{chapter} 앵커)
```

| 항목 | 값 (실측) |
| --- | --- |
| `robots.txt` | `User-agent: *` / `Disallow:` (전면 허용), `Sitemap: https://jpn.bible/sitemap.xml` |
| 사이트맵 | 색인 1 + 역본 색인 1 + **책 66개** = 68 URL |
| 응답 헤더 | `Server: Netlify`, `ETag` 있음, **`Last-Modified` 없음** |
| 최대 페이지 크기 | 시편 1.80 MB (`ps`), 사도행전 0.80 MB, 마가 0.47 MB |
| 인코딩 | `Content-Type: text/html; charset=UTF-8` — 헤더에 charset이 있으므로 `_request_html()`의 `apparent_encoding` 경로가 타지 않는다 |
| 이용약관 | **없음.** 사이트 전체가 색인 + 66개 책 페이지뿐이고 저작권/약관 페이지가 없다 |

책 슬러그는 OSIS 계열이며 `bible_book.book_key`(USFM 계열)와 다르다. 66개 전부:

```
gen exod lev num deut josh judg ruth 1sam 2sam 1kgs 2kgs 1chr 2chr ezra neh esth job
ps prov eccl song isa jer lam ezek dan hos joel amos obad jonah mic nah hab zeph hag
zech mal matt mark luke john acts rom 1cor 2cor gal eph phil col 1thess 2thess 1tim
2tim titus phlm heb jas 1pet 2pet 1john 2john 3john jude rev
```

**장 수는 `KJV_CHAPTER_COUNTS`와 정확히 일치한다.** 66권 전권에서 `div[id]` 개수를 세면 1,189개이고, 책별 최대 `id`가 모두 상수표와 같다. 따라서 `_discover_chapter_urls_for_jpnbible()`은 프로브 요청 없이 상수표만으로 만들 수 있다.

### 4.2 DOM 구조

66권 전체에서 나오는 태그 이름은 **12종뿐이다**(실측). `main h1 div h2 p span ruby rt rp br a title` — 클래스까지 구분해도 16가지다.

| 태그 | 개수 | 역할 |
| --- | ---: | --- |
| `main.book` | 66 | 본문 루트 |
| `h1` | 66 | 책명 |
| `div[id="{n}"]` | **1,189** | 장 컨테이너 |
| `h2.chapter-title` | 1,189 | 장 제목(第一章) |
| `p` | 5,045 | 문단 |
| `span.lg` / `span.l` | 1,214 / 22,148 | 시가 행 묶음 / 행 |
| `span.verse` | 38,694 | 절 마커(시작 31,088 + 끝 7,606) |
| `span.verse-number` | 31,088 | 절 번호 표시 |
| `span.verse-content` | 31,088 | 산문 절 본문 |
| `ruby` / `rt` / `rp` | 278,970 / 278,970 / 557,940 | 후리가나 |
| `br` | 23,362 | 행 바꿈 |
| `title` | **138** | 시편 표제 — 전부 시편에만 있다 |

각주·상호참조·소제목·`span.wj`가 **하나도 없다.** eBible에서 골라내야 했던 `div.d`/`div.qa`/`div.sp` 같은 오염원이 없다.

절 표기는 **두 가지 형태**를 쓴다. 파서는 둘 다 처리해야 한다.

```html
<!-- (가) 산문: 본문이 span.verse-content 안에 있다 -->
<span class="verse" id="1:1">
  <span class="verse-number"><a href="#1:1">1</a></span>
  <span class="verse-content">はじめに<ruby>神<rp>（</rp><rt>かみ</rt><rp>）</rp></ruby>は…</span>
</span>

<!-- (나) 시가: verse-content 가 비어 있고 본문이 형제 노드로 이어진다 -->
<span class="l">
  <span class="verse" id="3:1" data-s-id="3:1">
    <span class="verse-number"><a href="#3:1">1</a></span><span class="verse-content"/>
  </span>主よ、わたしに敵する者のいかに多いことでしょう。<br/>
</span>
<span class="l">わたしに逆らって立つ者が多く、<span class="verse" data-e-id="3:1"/><br/></span>
```

(나)가 eBible과 다른 점은 **끝 마커가 명시적으로 있다는 것**이다(`data-e-id`). eBible에서는 다음 시작 마커를 만날 때까지 누적하는 수밖에 없었지만, 여기서는 절의 끝이 문서에 적혀 있다. 따라서 절 사이에 낀 요소가 앞 절에 흡수될 여지가 구조적으로 없다.

### 4.3 함정 1. 루비를 지우지 않으면 읽기가 본문에 섞인다

278,970개 한자에 후리가나가 붙어 있다. 문제는 **지워야 한다는 사실 자체가 잘 드러나지 않는다**는 데 있다.

```python
>>> frag = '<p>はじめに<ruby>神<rp>（</rp><rt>かみ</rt><rp>）</rp></ruby>は</p>'
>>> s = BeautifulSoup(frag, 'html.parser')
>>> s.get_text('')
'はじめに神は'                       # ← 깨끗해 보인다
>>> ''.join(str(n) for n in s.descendants if isinstance(n, NavigableString))
'はじめに神（かみ）は'                # ← 이 저장소 파서가 실제로 하는 일
>>> [(type(n).__name__, str(n)) for n in s.descendants if isinstance(n, NavigableString)]
[('NavigableString', 'はじめに'), ('NavigableString', '神'),
 ('RubyParenthesisString', '（'), ('RubyTextString', 'かみ'),
 ('RubyParenthesisString', '）'), ('NavigableString', 'は')]
```

`get_text()`는 bs4가 루비 문자열을 별도 타입(`RubyTextString`, `RubyParenthesisString`)으로 분류해 기본 추출에서 제외하기 때문에 깨끗하다. 그러나 **두 타입 모두 `NavigableString`의 하위 클래스**이므로, `_extract_verses_from_ebible_page()`가 쓰는 `isinstance(node, NavigableString)` 검사는 그대로 통과시킨다. 이 저장소의 절 누적 파서는 전부 그 방식이다.

- 잘못된 결과: `はじめに神（かみ）は天（てん）と地（ち）とを創造（そうぞう）された。`
- 올바른 결과: `はじめに神は天と地とを創造された。`

**대응은 순회 전에 `rt, rp`를 `decompose()` 하는 것이다.** bs4 동작에 기대지 않아야 하는 이유가 하나 더 있다. 이 분류는 트리 빌더/버전에 딸린 동작이고(현재 4.14.3), 이 저장소의 파서는 `get_text()`가 아니라 직접 순회를 쓴다. **지우는 쪽이 어느 경로로든 같은 결과를 준다.**

오염을 검산할 수 있는 형태라는 점도 기록해 둔다. 누출되면 본문에 `한자（히라가나）` 패턴이 남으므로 [7.3](#73-루비-누출-검증)의 질의로 0건임을 확인할 수 있다.

### 4.4 함정 2. 병합 절 16건

소스는 병합을 `id` 속성에 **OSIS 참조를 덧붙여** 표기한다.

```html
<span class="verse" id="16:25 Rom.16.26">        <!-- 롬 16:25-26 -->
<span class="verse" id="132:3 Ps.132.4 Ps.132.5"> <!-- 시 132:3-5, 토큰 3개 -->
```

전권 조사 결과 **16건**이며, 그중 하나(시 132)는 세 절 병합이다.

```
민 15:4-5      대상 16:12-13   시 49:8-9     시 58:4-5     시 63:5-6
시 65:2-3      시 76:8-9       시 89:50-51   시 105:5-6    시 106:21-22
시 132:3-5     잠 26:18-19     사 4:3-4      롬 1:9-10     롬 2:19-20
롬 16:25-26
```

**첫 토큰만 읽으면 안 된다.** 시 132는 토큰이 세 개이므로 두 번째 토큰까지만 보면 5절이 통째로 사라진다. 프로토타입 1차 구현에서 실제로 그렇게 만들었고, 전권 연속성 검사가 `ps 132 missing [5]`를 잡아 드러났다. **범위의 끝은 마지막 OSIS 토큰의 절 번호다.**

저장 방식은 [jpn1965 설계 §4.4](new-japanese-nt-scraping-design.md)와 동일한 결정이다. **B안 — 범위의 모든 번호에 같은 본문을 저장** 을 권고한다. 근거도 같다. 절 번호 연속이라는 저장소 불변식을 지키면서 어떤 번호로 조회해도 올바른 본문이 나오고, 원문이 그 범위를 한 단위로 조판했다는 사실과 어긋나지 않는다. `(omitted)` 표기는 "원문에 본문이 없다"는 뜻이므로 여기에는 맞지 않는다.

> 두 문서가 같은 결정을 공유하므로 **한쪽만 다르게 정하면 안 된다.** B안이면 총 절 수가 31,104이고, 병합 뒤 번호를 버리는 A안이면 31,087이다.

### 4.5 함정 3. 분할 절 1건과 문서 순서 역전

출애굽기 22장에만 있다. 한 절이 `!a` / `!b`로 쪼개져 있고, **문서에 실린 순서가 절 번호 순서가 아니다.**

```
문서 순서 : 22:1  22:3!b  22:4  22:2  22:3!a  22:5 …
```

口語訳이 출 22:2-4를 삽입절로 조판했기 때문이다. 두 가지를 처리해야 한다.

1. `!a`/`!b` 접미사를 절 번호에서 떼어내고 **같은 절로 합친다.**
2. 합칠 때 **문서 순서가 아니라 접미사 순서(a → b)** 로 이어붙인다.

프로토타입 1차 구현은 문서 순서로 이어붙였고 결과가 이렇게 나왔다.

```
(문서 순서) 彼は必ず償わなければならない。… 身を売られるであろう。しかし日がのぼって後ならば、その人に血を流した罪がある。
(접미사 순서) しかし日がのぼって後ならば、その人に血を流した罪がある。彼は必ず償わなければならない。もし彼に何もない時は、彼はその盗んだ物のために身を売られるであろう。
```

절 개수도, 연속성도, 빈 절 검사도 전부 통과하는 오류다. **뒤에 것이 맞다**(제2 증인 religious-life도 `3a`/`3b` 라벨로 같은 분할을 표기하며 순서가 같다).

### 4.6 괄호가 앞 절 끝에 달린다

**19개 절이 여는 괄호로 끝난다**(`〔` 18, `（` 1). 인쇄본이 절 번호 앞에서 괄호를 열기 때문에 마크업이 앞 절 끝에 붙인 것이다.

```
마 17:20  … 移るであろう。そして、あなたがたにできない事は、何もないであろう。〔
마 17:21  しかし、このたぐいは、祈と断食とによらなければ、追い出すことはできない〕」。
```

절 단위로 보면 양쪽 다 괄호가 맞지 않는다. **여는 괄호를 다음 절 앞으로 옮기는 것을 권고한다.**

- 제2 증인(religious-life)은 19곳 모두 여는 괄호를 **뒤 절 앞**에 붙인다. 두 소스의 차이 122건 중 36건이 이 한 가지에서 나온다([7.6](#76-제2-증인-대조)).
- 이동 전후로 `〔〕` 짝이 맞지 않는 절이 **115개에서 83개로** 준다(실측). 남는 83개는 막 16:9-20처럼 괄호가 여러 절에 걸치는 정상 사례다.
- 문자를 지우지 않고 옮기기만 하므로 [1.3](#13-권리자가-붙인-두-가지-단서)의 동일성유지권 문제와 무관하다.

해당 19곳은 전부 열거된다(마 17:20, 18:10, 23:13, 막 7:15, 9:43, 9:45, 11:25, 15:27, 16:8, 눅 17:35, 23:16, 24:11, 24:39, 요 7:52, 행 1:17, 8:36, 15:33, 28:28, 롬 16:23). 테스트로 고정하기 좋은 크기다.

### 4.7 시편 표제 138개

`<title type="psalm" canonical="true">`로 표기되며 **전부 시편에만** 있다. 그중 21개는 시편 119편의 히브리 문자 이름(アレフ, ベス …)이라 **절과 절 사이에** 놓인다.

이 저장소의 관례는 표제를 **저장하지 않는 것**이다(KJV·NKRV·WEB·ASV·JPNMEB 모두 동일, RVR1909만 소스가 1절에 붙여 놓아 분리할 수 없는 예외).

정직하게 적으면, **[5.1](#51-scraperpy--책-페이지-캐시와-장-분리)처럼 장을 먼저 잘라내는 구현에서는 `title` 제거가 결과를 바꾸지 않는다.** 장 단위로 잘라 파싱한 1,189장 전부에서 제거 전후 본문이 **완전히 동일**했다. 표제는 첫 절 마커 앞에 있거나(→ 누적 대상이 아님) 앞 절의 `data-e-id` 뒤에 있기(→ 마찬가지) 때문이다.

그러나 **책 페이지를 통째로 파싱하면 4개 절이 오염된다**(실측).

```
시 24:10  この栄光の王とはだれか。万軍の主、これこそ栄光の王である。〔セラ + ダビデの歌
시 72:20  エッサイの子ダビデの祈は終った。                          + アサフの歌
시 84:12  万軍の主よ、あなたに信頼する人はさいわいです。              + 聖歌隊の指揮者によってうたわせたコラの子の歌
시 124:8  われらの助けは天地を造られた主のみ名にある。                + 都もうでの歌
```

즉 **다음 편의 표제가 앞 편 마지막 절에 붙는다.** 장 분리를 먼저 하면 막히지만, 그 순서에 의존하는 방어다. 제거 규칙을 함께 두고 이 이유를 주석으로 남긴다.

---

## 5. 코드 변경 지점

### 5.1 `scraper.py` — 책 페이지 캐시와 장 분리

이 설계에서 가장 큰 변경이며, **다른 소스에 영향이 없어야 한다.**

문제: 파이프라인은 장 단위로 URL을 만들고 장 단위로 커밋한다. 그런데 이 소스는 페이지가 책 단위다. 그대로 두면 시편 한 권에 1.8 MB짜리 같은 페이지를 **150번** 받는다(270 MB).

해결: 책 페이지를 한 번 받아 장별 HTML로 쪼개 들고 있는다. 캐시는 **직전 책 하나만** 유지한다(책 단위 루프이므로 적중률 100%, 상주 메모리 최대 1.8 MB).

```python
DEFAULT_JPNBIBLE_KOUGO_ENTRY_URL = "https://jpn.bible/kougo/gen#1"
JPNBIBLE_MIN_DELAY_SECONDS = 1.0

def _fetch_soup(self, url: str) -> BeautifulSoup:
    # jpn.bible serves a whole book per page and has no per-chapter URL, so the
    # chapter comes from the fragment. Refetching the page per chapter would pull
    # 1.8MB x 150 for Psalms; one page per book is both correct and politer.
    if self._is_jpnbible_source():
        return self._fetch_jpnbible_chapter_soup(url)
    html = self._request_html(url)
    return BeautifulSoup(html, "html.parser")

def _fetch_jpnbible_chapter_soup(self, url: str) -> BeautifulSoup:
    page_url, _, fragment = url.partition("#")
    if self._jpnbible_page_url != page_url:
        html = self._request_html(page_url)          # the only HTTP call per book
        self._jpnbible_chapters = self._split_jpnbible_book(html)
        self._jpnbible_page_url = page_url
    # The fragment is a string; _split_jpnbible_book keys by the same string, not
    # by int. Mixing the two makes every lookup miss and every chapter come back
    # empty, which surfaces only as "book yielded no verses" once per book.
    chapter_html = self._jpnbible_chapters.get(fragment, "")
    return BeautifulSoup(chapter_html, "html.parser")
```

`_split_jpnbible_book()`은 `main.book` 바로 아래 `div[id]`를 장 번호로 삼아 `{"1": HTML, "2": HTML, …}`을 만든다. **키는 `div`의 `id` 문자열 그대로 쓴다.** 파싱은 책당 한 번이고, 이후 장마다 작은 조각만 다시 파싱한다.

- 캐시가 비었거나 해당 장이 없으면 **빈 soup**을 돌려준다. 절 0개 → 기존 빈 데이터 가드가 그대로 잡아 **쓰기 전에** 건너뛴다. 프래그먼트가 없는 URL(`.../kougo/gen`)도 같은 경로로 빈 soup이 되므로, 일반 탐색 경로가 이 소스로 들어오지 않게 `_build_chapter_url()`과 `discover_chapter_urls_for_book()` 양쪽에 분기를 둔다.
- `_request_html()` 안의 예의 지연은 실제 요청이 있을 때만 실행되므로, 캐시 적중 장에서는 지연이 없다.
- 재시도로 같은 책을 다시 처리해도 `page_url`이 같으면 재요청하지 않는다.

### 5.2 `scraper.py` — 파서

체인의 위치는 **eBible 파서 뒤, `bibletable` 앞**이다. 이 소스 페이지가 다른 소스 파서에 걸릴 일은 없지만(선택자가 전부 다르다), 일반 추론 파서보다는 반드시 앞이어야 한다. 일반 파서에 넘어가면 루비가 섞인 채로 연속된 절 목록이 나와 **어떤 검사도 통과한다.**

```python
JPNBIBLE_VERSE_ID_PATTERN = re.compile(r"^(\d{1,3}):(\d{1,3})(?:!([ab]))?$")
JPNBIBLE_OSIS_REF_PATTERN = re.compile(r"^[A-Za-z0-9]+\.(\d{1,3})\.(\d{1,3})$")
# Ruby readings must go before the walk: bs4 keeps them out of get_text(), but
# RubyTextString/RubyParenthesisString are NavigableString subclasses, so the
# descendants walk this parser uses would fold 神（かみ） into the verse text.
JPNBIBLE_REMOVABLE_SELECTOR = "rt, rp, h1, h2, title"
```

**다른 소스 페이지에서는 `[]`를 돌려줘야 한다**(체인 규약). 판별자는 `span.verse-content`다.

```python
if soup.select_one("span.verse-content") is None:
    return []
```

`main.book`을 쓸 수 없다는 점에 주의한다 — [5.1](#51-scraperpy--책-페이지-캐시와-장-분리)이 넘겨주는 것은 이미 잘라 낸 `div[id]` 조각이라 `main`이 없다. `span.verse-content`는 eBible(`span.verse` + `id="V1"`)·bskorea·BibleGateway(`span.text`)·religious-life(`span.section`) 어디에도 없다.

반대 방향도 확인했다. eBible 파서는 `div.main`을 찾는데 이 소스는 `<main class="book">`이므로 걸리지 않는다.

절 조립 규칙:

| 노드 | 처리 |
| --- | --- |
| `span.verse[id]` | 절 시작. `id` 첫 토큰이 번호(`c:v`, `c:v!a`), 나머지 OSIS 토큰의 **최댓값**이 범위 끝 |
| `span.verse[data-e-id]` (id 없음) | 절 끝 → 누적 중지 |
| `span.verse-number` 내부 텍스트 | 절 번호 표시이므로 **본문 아님** |
| 그 밖의 텍스트 | 현재 절에 누적. 블록 경계에서 공백 하나, 그 뒤 `CJK_JOIN_PATTERN`으로 제거 |

마무리 두 가지:

- `!a`/`!b`는 접미사 순서로 합친다([4.5](#45-함정-3-분할-절-1건과-문서-순서-역전)).
- 절 본문이 여는 괄호로 끝나면 그 문자를 다음 절 앞으로 옮긴다([4.6](#46-괄호가-앞-절-끝에-달린다)).

`CJK_JOIN_PATTERN`은 JPNMEB 작업에서 이미 들어가 있으므로 **재사용이고 신규 변경이 아니다.** 전권 프로토타입에서 CJK 사이 공백이 남은 절은 0건이다.

병합 절을 B안으로 저장할 때 `_sanitize_verses()`가 걸림돌이 되지 않는지도 확인했다. 이 함수는 **절 번호로만 중복을 거른다**(`seen_numbers`). 본문이 같아도 번호가 다르면 그대로 통과하므로, 범위의 모든 번호에 같은 본문을 넣는 방식이 파이프라인 앞단에서 잘리지 않는다.

### 5.3 `scrape_bible_to_db.py` — 역본 등록

```python
ENTRY_URL_ENV_BY_TRANSLATION_TYPE = { ..., "KOUGO": "KOUGO_ENTRY_URL" }
TRANSLATION_TYPES_BY_LANGUAGE_CODE = { ..., "ja": ("JPNMEB", "KOUGO") }
ENTRY_URL_PREFERENCE_ORDER = (..., "JPNMEB", "KOUGO")
TRANSLATION_SOURCE_REQUIREMENTS = {
    ...,
    "KOUGO": {
        "source": "jpnbible",
        "version": "kougo",      # from the URL path, like eBible
        "name": "口語訳聖書",
        "language_code": "ja",
    },
}
```

- `get_source_name()`에 `jpnbible` 분기, `get_source_version()`에 경로 첫 세그먼트(`kougo`)를 돌려주는 분기를 추가한다. eBible과 같은 이유다 — 한 사이트가 여러 역본을 서비스하게 되면 `version`이 `None`인 행이 그 사이트의 모든 역본을 먹어 버린다.
- `resolve_book_code_for_source()`는 이 소스에서 `None`을 돌려준다. 책 슬러그는 `bible_book.book_key`(USFM 계열)와 다르므로 **DB 값이 아니라 상수표**(`USFM_BOOK_CODES` 옆에 두는 `JPNBIBLE_BOOK_SLUGS`, [4.1](#41-url-규칙--책-단위-한-페이지)의 66개)를 써야 한다. bskorea처럼 `book_key`를 소문자로 바꿔 쓰면 `gen`은 통하지만 나머지는 아니다 — 실측으로 `/kougo/sng`, `/kougo/ezk`, `/kougo/phm`이 전부 404이고 `/kougo/song`이 200이다.

`translation_type`을 **`KOUGO`** 로 권고하는 이유:

- 배포처 공식 ID가 없다. `JPNMEB`/`JPNLOC`은 eBible이 부여한 ID를 그대로 쓴 것인데, jpn.bible에는 그런 식별자가 경로(`/kougo/`) 말고 없다.
- CrossWire 모듈명 `JapKougo`에서 딴 `JAPKOUGO`도 가능하지만, **적재 소스가 CrossWire가 아니다.** 쓰지 않는 배포처의 ID를 붙이면 나중에 소스를 되짚을 때 오해를 만든다.
- `KOUGO`는 이 판본을 가리키는 보편적 호칭(口語訳)이고, 기존 30개 값 및 널리 쓰이는 영어 약칭과 충돌하지 않는다.

### 5.4 기존 동작이 바뀐다 — 일본어 역본이 둘이 된다

**이 등록은 기존 JPNMEB 실행을 깨뜨릴 수 있다.** 지금까지 `ja`는 역본이 하나뿐이라 `BIBLE_LANGUAGE_CODE=ja`만으로 엔트리 URL이 정해졌다. `KOUGO`가 들어가면 `en`(KJV/WEB/ASV)에서 이미 겪은 모호성이 `ja`에도 생긴다. 실제로 실행해 확인했다.

```
JPNMEB_ENTRY_URL 만 설정 + BIBLE_LANGUAGE_CODE=ja
  현재      → https://ebible.org/jpnm/GEN01.htm
  등록 후   → ValueError: Ambiguous entry URL: BIBLE_LANGUAGE_CODE='ja'
              matches JPNMEB_ENTRY_URL, KOUGO_ENTRY_URL.
```

`KOUGO_ENTRY_URL`을 함께 설정한 환경에서만 발생한다. 회피책 두 가지를 모두 확인했다.

| 조치 | 결과 |
| --- | --- |
| `BIBLE_TRANSLATION_TYPE=JPNMEB` 추가 | JPNMEB URL로 정상 해석 |
| `KOUGO_ENTRY_URL`을 그 실행에서 빼기 | JPNMEB URL로 정상 해석 |

조용히 잘못된 소스를 고르는 대신 **예외를 던지는 쪽이 설계 의도대로**이므로 코드를 바꿀 일은 아니다. 다만 이것은 **문서화해야 할 파급**이고, `.env`에 두 URL을 함께 두는 순간 기존 명령이 실패한다. README의 실행 예에 `BIBLE_TRANSLATION_TYPE`을 명시하는 작업이 함께 가야 한다.

---

## 6. DB 준비

### 6.1 현재 상태 (실측)

```
[bible_translation]           30행, 최대 translation_order = 33 (JPNMEB)
[translation_type CHECK]      30개 값, 'KOUGO' 없음
[language_code CHECK]         ko,en,zh,ja,es,de,la — 'ja' 허용됨
[bible_book_description]      en/es/ja/ko 각 66행 — ja 이미 있음
[적재 완료 역본]               KRV, NKRV, KJV, WEB, ASV, RVR1909, SBLM, JPNMEB (8개)
```

`bible_translation`/`bible_book`/`bible_chapter`/`bible_verse`의 `id`는 모두 `GENERATED BY DEFAULT AS IDENTITY`다.

### 6.2 `translation_type` CHECK 제약 — 31번째 값

```sql
-- 현재 30개 값만 허용. 'KOUGO' 삽입은 bible_translation_translation_type_check 위반.
ALTER TABLE public.bible_translation DROP CONSTRAINT bible_translation_translation_type_check;
ALTER TABLE public.bible_translation ADD CONSTRAINT bible_translation_translation_type_check
  CHECK (translation_type IN (
    'KRV','NKRV','RNKSV','KOERV','KLB','NLTNK','NIV','ESV','KJV','NASB','NLT','CSB',
    'GNT','CEV','MSG','NRSV','AMP','HCSB','WEB','ASV','DBY','BBE','YLT','LBLA',
    'RVR1960','LUTH1545','VUL','RVR1909','SBLM','JPNMEB','KOUGO'));
```

### 6.3 `bible_translation` row

```sql
INSERT INTO public.bible_translation (translation_type, name, language_code, translation_order)
SELECT 'KOUGO', '口語訳聖書', 'ja',
       COALESCE(MAX(translation_order), 0) + 1
FROM public.bible_translation;
```

- **`translation_order`는 NOT NULL이고 기본값이 없다.** 빠뜨리면 삽입이 거부된다(SBLM 때 실제로 여기서 막혔다).
- `translation_order`는 `id`를 따라가지 않는다. 현재 최대값이 33이므로 **34**가 된다.
- `name`, `translation_type`에 UNIQUE 제약이 있다. 기존 `ja` 역본(`JPNMEB` = フリーダム・バイブル)과 충돌하지 않는다.

### 6.4 `bible_book` 66권 시드

**도구는 `bible_book`을 만들지 않는다.** 적재 전에 66행이 있어야 한다.

책명은 소스 색인을 그대로 쓰면 안 된다. 두 소스와 위키문헌 목차(본문과 달리 삭제되지 않았다)를 3자 대조한 결과 **어느 한쪽도 완전하지 않다.**

| 구분 | jpn.bible | religious-life | 위키문헌 목차 | 채택 |
| --- | --- | --- | --- | --- |
| 사무엘기 등 6권 | サムエル記上 | サムエル記 上 | サムエル記上 | 공백 없음 |
| 열왕기 2권 | 列王紀上/下 | 列王記 上/下 | 列王紀上/下 | **紀** |
| 느헤미야 | ネヘミヤ**書** | ネヘミヤ記 | ネヘミヤ記 | **記** |
| 디모데/디도/빌레몬 4권 | テモテ**ヘ**の … | テモテ**へ**の … | テモテへの … | **へ**(히라가나) |

즉 **jpn.bible 색인을 기준으로 하되 5곳(ネヘミヤ記, テモテへ×2, テトスへ, ピレモンへ)을 고친다.** 나머지 61권은 세 곳이 모두 같다.

`book_key`/`abbreviation`/`testament_type`은 기존 일본어 역본에서 그대로 가져온다.

```sql
INSERT INTO public.bible_book (translation_id, book_order, book_key, abbreviation, name, testament_type)
SELECT :new_id, b.book_order, b.book_key, b.abbreviation, n.name, b.testament_type
FROM public.bible_book b
JOIN (VALUES
  (1,'創世記'),(2,'出エジプト記'),(3,'レビ記'),(4,'民数記'),(5,'申命記'),
  (6,'ヨシュア記'),(7,'士師記'),(8,'ルツ記'),(9,'サムエル記上'),(10,'サムエル記下'),
  (11,'列王紀上'),(12,'列王紀下'),(13,'歴代志上'),(14,'歴代志下'),(15,'エズラ記'),
  (16,'ネヘミヤ記'),(17,'エステル記'),(18,'ヨブ記'),(19,'詩篇'),(20,'箴言'),
  (21,'伝道の書'),(22,'雅歌'),(23,'イザヤ書'),(24,'エレミヤ書'),(25,'哀歌'),
  (26,'エゼキエル書'),(27,'ダニエル書'),(28,'ホセア書'),(29,'ヨエル書'),(30,'アモス書'),
  (31,'オバデヤ書'),(32,'ヨナ書'),(33,'ミカ書'),(34,'ナホム書'),(35,'ハバクク書'),
  (36,'ゼパニヤ書'),(37,'ハガイ書'),(38,'ゼカリヤ書'),(39,'マラキ書'),
  (40,'マタイによる福音書'),(41,'マルコによる福音書'),(42,'ルカによる福音書'),
  (43,'ヨハネによる福音書'),(44,'使徒行伝'),(45,'ローマ人への手紙'),
  (46,'コリント人への第一の手紙'),(47,'コリント人への第二の手紙'),(48,'ガラテヤ人への手紙'),
  (49,'エペソ人への手紙'),(50,'ピリピ人への手紙'),(51,'コロサイ人への手紙'),
  (52,'テサロニケ人への第一の手紙'),(53,'テサロニケ人への第二の手紙'),
  (54,'テモテへの第一の手紙'),(55,'テモテへの第二の手紙'),(56,'テトスへの手紙'),
  (57,'ピレモンへの手紙'),(58,'ヘブル人への手紙'),(59,'ヤコブの手紙'),
  (60,'ペテロの第一の手紙'),(61,'ペテロの第二の手紙'),(62,'ヨハネの第一の手紙'),
  (63,'ヨハネの第二の手紙'),(64,'ヨハネの第三の手紙'),(65,'ユダの手紙'),(66,'ヨハネの黙示録')
) AS n(book_order, name) ON n.book_order = b.book_order
WHERE b.translation_id = (SELECT id FROM public.bible_translation WHERE translation_type = 'JPNMEB');
```

### 6.5 `bible_book_description` — 추가 작업 없음

`ja` 66행이 JPNMEB 작업에서 이미 들어갔다. 이 표는 `(book_key, language_code)` 키이므로 역본과 무관하게 재사용된다.

---

## 7. 검증

### 7.1 구조 검증

```sql
SELECT COUNT(DISTINCT b.id) AS books,
       COUNT(DISTINCT c.id) AS chapters,
       COUNT(v.id)          AS verses
FROM public.bible_book b
JOIN public.bible_chapter c ON c.book_id = b.id
JOIN public.bible_verse  v ON v.chapter_id = c.id
WHERE b.translation_id = :tid;
-- 기대: 66 / 1189 / 31104   (B안 기준. A안이면 31087)
```

절 번호 연속성:

```sql
SELECT b.book_order, c.chapter_number, COUNT(*) AS n, MAX(v.verse_number) AS maxv
FROM public.bible_book b
JOIN public.bible_chapter c ON c.book_id = b.id
JOIN public.bible_verse  v ON v.chapter_id = c.id
WHERE b.translation_id = :tid
GROUP BY b.book_order, c.chapter_number
HAVING COUNT(*) <> MAX(v.verse_number)
ORDER BY 1, 2;
-- 기대: 0행
```

### 7.2 인코딩 검증

일본어가 한 글자도 없는 절을 찾는다. 스페인어 역본에서 쓰던 `LIKE '%Ã%'` 류는 **일본어 모지바케를 잡지 못한다**(JPNMEB 문서에서 확인한 함정이다).

```sql
SELECT COUNT(*) FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid
  AND v.text !~ '[぀-ヿ一-鿿]';
-- 기대: 0행 (이 역본에는 (omitted) 절이 없다 — 7.5 참조)
```

### 7.3 루비 누출 검증

[4.3](#43-함정-1-루비를-지우지-않으면-읽기가-본문에-섞인다)이 실패하면 본문에 `한자（히라가나）` 패턴이 남는다.

```sql
SELECT b.book_order, c.chapter_number, v.verse_number, left(v.text, 60)
FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid
  AND v.text ~ '[一-鿿]（[ぁ-ゟー]+）'
ORDER BY 1, 2, 3 LIMIT 20;
-- 기대: 0행
```

이 질의의 민감도를 실측했다. 루비를 지우지 않고 파싱한 창세기·마가·시편 2,205절 중 **2,197절(99.6%)** 이 걸린다. 놓치는 8절은 루비가 붙은 한자가 없는 절이라, 오염되어도 원래 바꿀 것이 없는 절이다. 반대로 정상 파싱한 31,104절에 대한 **오탐은 0건**이다.

CJK 공백 오염도 같이 본다(JPNMEB와 동일한 질의).

```sql
... AND v.text ~ '[぀-ヿ一-鿿] [぀-ヿ一-鿿]';
-- 기대: 0행
```

### 7.4 KJV 대조 — 네 개 장

장별 절 수를 KJV와 맞춰 보면 **정확히 4개 장에서만** 달라야 한다. 이 목록이 없으면 "차이 4건"이 정상인지 실패인지 판단할 수 없다.

| 장 | KJV | 口語訳 | 비고 |
| --- | ---: | ---: | --- |
| 시 47 | 9 | **10** | 제2 증인도 10 |
| 고후 13 | 14 | **13** | jpn1965도 13 |
| 요삼 1 | 14 | **15** | jpn1965도 15 |
| 계 12 | 17 | **18** | jpn1965도 18 |

합계 차이는 **+2**(31,102 → 31,104)다. 뒤 세 장은 [jpn1965 설계](new-japanese-nt-scraping-design.md)에서 확인한 차이와 같은 장이다. 일본어 역본이 공유하는 절 구분이지 이 소스의 결함이 아니다.

JPNMEB와 비교하면 6개 장이 다르다. 위 4개에 더해 롬 14(JPNMEB 26 대 23)와 롬 16(25 대 27)이 걸린다. DB를 직접 확인한 결과 원인은 이렇다.

- JPNMEB는 송영을 **14:24-26**에 둔다(「私の福音、すなわちイエス・キリストについての宣教と…」). 口語訳은 KJV와 같이 16:25-27에 둔다.
- JPNMEB 롬 16은 24절까지가 본문이고 **25절이 `(omitted)`** 다. 그래서 실제 본문은 24절인데 행 수는 25로 잡힌다.

두 역본의 총계 차이 +1(31,104 대 31,103)은 이 여섯 장의 합(+1 −1 +1 +1 −3 +2)으로 정확히 설명된다.

### 7.5 병합·분할 절 검증

```sql
-- 병합 16건: 범위 안 번호들이 같은 본문이어야 한다 (B안)
SELECT b.book_order, c.chapter_number, v.verse_number, left(v.text, 40)
FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid
  AND (b.book_order, c.chapter_number, v.verse_number) IN (
      (4,15,4),(4,15,5), (13,16,12),(13,16,13), (19,49,8),(19,49,9),
      (19,132,3),(19,132,4),(19,132,5), (45,16,25),(45,16,26))
ORDER BY 1, 2, 3;
-- 기대: 각 범위 안에서 text 가 동일
```

```sql
-- 분할 1건: 출 22:3 이 a→b 순서로 이어져야 한다
SELECT v.text FROM public.bible_verse v ...
WHERE b.book_order = 2 AND c.chapter_number = 22 AND v.verse_number = 3;
-- 기대: 'しかし日がのぼって後ならば' 로 시작
```

`(omitted)` 절은 **0건이어야 한다.** WEB/SBLM/JPNMEB가 비워 두는 네 절(눅 17:36, 행 8:37·15:34·24:7)을 口語訳은 **본문과 함께 〔 〕로** 싣는다. 이 역본에서 `(omitted)`가 나오면 파서 오류다.

```sql
SELECT COUNT(*) FROM public.bible_verse v ... WHERE b.translation_id = :tid AND v.text = '(omitted)';
-- 기대: 0
```

### 7.6 제2 증인 대조

이 판본은 **독립된 두 사이트가 각각 옮겨 적은 텍스트**다. 적재 후 religious-life와 절 단위로 비교하면 파서 오류와 소스 오탈자가 분리된다.

전권 프로토타입 대조 결과(실측):

```
일치 30,983절 / 불일치 122절 / 차이가 난 장 63개
```

| 차이 유형 | 건수 | 어느 쪽 문제인가 |
| --- | ---: | --- |
| 절 경계 차이 | 44 | **religious-life** — 절 마커가 밀려 있다 |
| 괄호 위치 차이 | 36 | 표기 방식 차이. [4.6](#46-괄호가-앞-절-끝에-달린다)의 이동을 적용하면 사라진다 |
| 표기/오탈자 차이 | 24 | **양쪽 모두** — 아래 참조 |
| religious-life에 절 없음 | 11 | **religious-life** |
| jpn.bible에 절 없음 | 1 | **religious-life**가 계 5:13을 둘로 쪼갠 것 |
| 기타 | 6 | 개별 확인 필요 |

religious-life 쪽 구조 결함은 전권 검사에서 따로 확인된다. **중복 라벨 11개 장**(gen-26, exo-2, deu-12, job-28, **jer-23**, mat-10, mat-22, mar-9, mar-15, joh-7, act-14), **번호 빠짐 5개 장**(2ch-26, mat-10, mar-9, mar-15, act-14). jer-23은 아예 **다음 장 본문 일부가 섞여 있다.** mar-9는 22~25절이 한 칸씩 밀려 라벨 21이 두 번 나온다.

#### 갈리는 절을 누가 판정하는가

표기/오탈자 25건을 실제로 판정해 봤다. **처음 세운 방법은 틀렸다.** baiburu와 STEPBible을 제3·제4 증인으로 쓰려 했는데, 둘 다 jpn.bible과 **같은 계보**였다([1.5](#15-추가-검토-baiburucom-과-stepbible)). 같은 흔적을 그대로 갖고 있으니 판정에 쓸 수 없다.

계보 밖에서 대조할 수 있는 것은 **religious-life**와, 訂正판이라 채택하지 않은 **wordproject**뿐이다. wordproject를 넣어 25건을 다시 판정한 결과:

| 판정 | 건수 |
| --- | ---: |
| jpn.bible 읽기가 다수 | 16 |
| religious-life 읽기가 다수 | 5 |
| 구두점만 차이 | 4 |

**jpn.bible이 틀린 5건은 그대로 적어 둔다.** 계보 밖 두 증인이 모두 다른 읽기를 주는 절이다.

| 절 | jpn.bible | 다른 두 증인 |
| --- | --- | --- |
| 2사무 19:32 | 八十**{**歳 | 八十歳 |
| 이사 55:7 | **正らぬ**人 | 正しからぬ人 |
| 이사 65:16 | 忘れられて、**と**わが目から | 忘れられて、わが目から |
| 요한 1:27 | わたしの**あとにあとに** | わたしのあとに |
| 2고린 9:12 | 欠乏を**補え**だけ | 欠乏を補うだけ |

증인에 기대지 않는 검사도 돌렸다. **일본어 성경 본문에 있을 수 없는 문자**(ASCII 영숫자, 괄호류, 중복 구두점)를 전권에서 세면 jpn.bible 31,104절 중 **4절**, religious-life 31,078개 마커 중 **2절**이다(범위 라벨을 펼치기 전 개수라 31,104와 직접 비교할 수는 없다). jpn.bible 쪽은 위의 `{` 하나와 「、、」·「。、」 세 건이고, 그중 `exod 8:5`의 「、、」는 religious-life에도 있어 공통 조상 또는 인쇄본에서 온 것으로 보인다.

> 정리하면 **어느 소스도 정본이 아니다.** 다만 성격이 다르다. jpn.bible의 결함은 **글자 몇 개**이고 목록으로 만들 수 있다. religious-life의 결함은 **절 번호 12개 장**이고, 올바른 개수의 연속된 목록을 만들어 내므로 목록화 자체가 어렵다. 이 대조는 합격/불합격 판정이 아니라 **정오표를 만드는 작업**이다.

적재 후 기대 불일치는 **86건**이다(122 − 괄호 이동으로 해소되는 36). 이보다 많이 나오면 파서 문제다.

---

## 8. 테스트 설계

`tests/test_scraper.py`에 인라인 HTML 픽스처로 추가한다. **네트워크를 타는 테스트는 넣지 않는다.**

| 테스트 | 검증 내용 |
| --- | --- |
| `test_jpnbible_prose_chapter` | `span.verse-content` 산문 형태에서 절 번호·본문 추출 |
| `test_jpnbible_poetry_chapter` | `data-s-id`/`data-e-id` 시가 형태 누적, `br` 사이 공백 없음 |
| `test_jpnbible_strips_ruby` | `<ruby>神<rp>（</rp><rt>かみ</rt><rp>）</rp></ruby>` → `神`. **`get_text()`가 아니라 파서 결과로 확인해야 의미가 있다** |
| `test_jpnbible_merged_range` | `id="132:3 Ps.132.4 Ps.132.5"` → 3·4·5에 같은 본문 |
| `test_jpnbible_split_verse` | `!b`가 문서상 먼저 와도 `a → b` 순서로 합쳐짐 |
| `test_jpnbible_moves_opening_bracket` | 앞 절 끝 `〔`가 다음 절 앞으로 이동 |
| `test_jpnbible_drops_psalm_title` | `<title type="psalm">`이 본문에 섞이지 않음 |
| `test_jpnbible_book_page_cache` | 같은 책의 두 장을 요청해도 `_request_html` 호출이 **1회** |
| `test_jpnbible_missing_chapter_returns_empty` | 캐시에 없는 장 → 절 0개(예외 아님) |
| `test_other_sources_unaffected` | eBible/BibleGateway 픽스처가 새 파서에 걸리지 않음 |
| `test_ja_entry_url_ambiguity` | `ja` URL 둘을 설정하고 `BIBLE_LANGUAGE_CODE=ja`만 주면 **예외**([5.4](#54-기존-동작이-바뀐다--일본어-역본이-둘이-된다)) |
| `test_jpnmeb_still_resolves` | `BIBLE_TRANSLATION_TYPE=JPNMEB`이면 기존대로 eBible URL |

캐시 테스트가 특히 중요하다. 이것이 깨지면 조용히 요청이 1,189회로 늘어나고, 결과는 정상이라 아무 검사도 잡지 못한다.

---

## 9. 운영 계획

### 9.1 요청 간격과 소요

- `robots.txt`에 `Crawl-delay`가 없다. 기존 하한(1초)을 그대로 적용한다.
- **HTTP 요청은 전권 66회**다. 책 전환 지연(5초)이 65회 들어가므로 네트워크 구간은 약 7분이다. 나머지 시간은 파싱과 DB 쓰기가 지배한다.
- 총 전송량은 비압축 기준 약 25 MB(66개 책 페이지 실측 합계). 서버가 gzip으로 보내므로 실제 회선 사용량은 이보다 작다.

### 9.2 실행 예

```bash
# 파서만 확인 (DB 미접속)
KOUGO_ENTRY_URL=https://jpn.bible/kougo/gen#1 BIBLE_TRANSLATION_TYPE=KOUGO \
  python3 scrape_bible_to_db.py --test-genesis1

# 전권
BIBLE_TRANSLATION_ID=<tid> BIBLE_TRANSLATION_TYPE=KOUGO BIBLE_LANGUAGE_CODE=ja \
KOUGO_ENTRY_URL=https://jpn.bible/kougo/gen#1 \
  python3 scrape_bible_to_db.py --start-book 1 --end-book 66
```

`BIBLE_TRANSLATION_ID`만 주면 엔트리 URL 선택이 흔들린다. `BIBLE_TRANSLATION_TYPE`을 함께 넘기거나 `--entry-url`을 쓴다.

### 9.3 갱신 문제

- 이 사이트는 **`Last-Modified`를 보내지 않는다.** `scripts/check_translation_drift.py --head-only`가 아무것도 보고하지 못한다. 대신 `ETag`와 `sitemap.xml`의 `lastmod`(현재 전 페이지 `2026-02-22T03:10:25+09:00`)를 쓴다.
- 본문은 1955년에 고정된 판본이므로 SBLM 같은 "초안 갱신" 위험이 없다. 다만 **사이트가 오탈자를 고칠 수는 있다**([7.6](#76-제2-증인-대조)). 그때는 미적재 삽입 특성상 자동 반영되지 않으므로, 해당 절만 지우고 다시 넣는다. `bible_chapter`/`bible_verse`에 외래키가 없으므로 **절 → 장 순서**를 지킨다.
- salterrae가 사라진 사례가 보여 주듯 **소스 사이트는 없어질 수 있다.** 적재를 마치면 DB가 원본이 되고, 그 시점의 크롤 결과를 따로 보관해 둘지는 운영 판단이다.

### 9.4 잘못 적재했을 때 되돌리기

미적재 삽입이라 **재실행으로는 고쳐지지 않는다.** 파서를 고쳐 다시 넣으려면 먼저 지워야 한다. `bible_chapter`/`bible_verse`에 외래키가 없으므로 **절을 먼저, 장을 나중에** 지운다. 순서를 뒤집으면 절이 고아가 되어 책 기준 질의로는 다시 찾을 수 없다.

```sql
-- 1) 절 먼저
DELETE FROM public.bible_verse v
USING public.bible_chapter c, public.bible_book b
WHERE v.chapter_id = c.id AND c.book_id = b.id
  AND b.translation_id = (SELECT id FROM public.bible_translation WHERE translation_type = 'KOUGO');

-- 2) 그다음 장
DELETE FROM public.bible_chapter c
USING public.bible_book b
WHERE c.book_id = b.id
  AND b.translation_id = (SELECT id FROM public.bible_translation WHERE translation_type = 'KOUGO');

-- 3) 확인 — 0 / 0 이어야 한다
SELECT (SELECT COUNT(*) FROM public.bible_verse v
          JOIN public.bible_chapter c ON c.id = v.chapter_id
          JOIN public.bible_book b ON b.id = c.book_id
         WHERE b.translation_id = :tid) AS verses,
       (SELECT COUNT(*) FROM public.bible_chapter c
          JOIN public.bible_book b ON b.id = c.book_id
         WHERE b.translation_id = :tid) AS chapters;
```

`bible_book` 66행과 `bible_translation` 1행은 **지우지 않는다.** 도구가 읽기만 하는 표이고, 지우면 다시 시드해야 한다. 일부 장만 다시 넣을 때도 같은 순서를 지킨다.

재적재 자체는 안전하다. 삽입이 미적재분만 대상으로 하므로 **중간에 끊긴 실행을 다시 돌리면 남은 것만 채운다.** 병합 절을 B안으로 넣어도 번호마다 한 행이므로 재실행이 행을 늘리지 않는다.

---

## 10. 대안 경로 — religious-life

jpn.bible이 사라지거나 접근이 막히면 [1.4](#14-후보-소스-비교)의 두 번째 후보로 갈아탈 수 있다. 비용과 조건은 이렇다.

| 항목 | jpn.bible | religious-life | baiburu |
| --- | --- | --- | --- |
| 판본 | 원본 | 원본 (동일) | 원본 (동일) |
| 요청 수 / 전송량 | 66 / 25 MB | **1,189** / 29 MB | **1,189** / 약 133 MB |
| 구조 변경 | 책 페이지 캐시 필요 | **불필요** (장 단위 URL) | **불필요** (장 단위 URL) |
| 절 마커 | `id` 속성, 기계 판독 | 텍스트 라벨(`25-26`, `3a`) | `data-verse-number` 속성 |
| 절 번호 결함 | 0 | **12개 장** (중복 라벨 11 + 번호 빠짐 5, 4개 장은 양쪽 모두). 라벨은 정상인데 본문 경계가 어긋난 절이 **44건 더** 있다 | 병합을 뒤 번호에만 표기 |
| 본문 소실 | 0 | 0 | **출 22:3 전체** |
| 루비 | 있음(제거 필요) | 없음 | 있음(`rt`만, `rp` 없음) |
| 표제 | `<title>` 138 | `h3` 138 (개수 일치) | 미조사 |
| `robots.txt` | 전면 허용 | 허용(`/*?*`만 차단, 장 URL은 대상 아님) | 허용, 단 `ai-train=no, use=reference` 선언 |

**결함 12개 장 때문에 주 소스로 권고하지 않는다.** 오탈자는 정오표로 다룰 수 있지만, 절 번호가 밀린 것은 *올바른 개수의 연속된 절 목록*을 만들어 내므로 이 저장소의 어떤 자동 검사도 잡지 못한다. 막 9장에서 22~25절 본문이 21~24절 자리에 들어가고, 그대로 커밋된다.

굳이 이 소스를 써야 한다면 결함 12개 장에 대한 보정표가 필요하고, **사이트가 나중에 이를 고치면 보정표가 거꾸로 오염원이 된다.** 그 위험까지 감수할 이유가 없다.

**baiburu는 구조상 가장 편한 대안이지만 출 22:3이 없다**([1.5](#15-추가-검토-baiburucom-과-stepbible)). 이 소스로 가려면 그 한 절을 다른 소스에서 채워 넣는 예외 처리가 필요하고, 그 순간 "소스는 하나"라는 전제가 깨진다. 전송량이 jpn.bible의 7배인 점도 같이 본다.

wordproject는 절 번호가 깨끗하지만 **2002년 訂正 본문**이라 권리 관계가 달라진다([1.3](#13-권리자가-붙인-두-가지-단서)). STEPBible은 판본은 맞지만 시편 일부가 빈 응답이고 절 구분 체계가 다르다. 둘 다 대안 목록에 넣지 않는다.

---

## 11. 구현 순서

1. **테스트 먼저** — [8](#8-테스트-설계)의 픽스처를 작성한다. 루비·병합·분할·괄호·캐시 다섯 개가 핵심이다.
2. `scraper.py` — 소스 판별, URL 빌더, 장 발견(`KJV_CHAPTER_COUNTS` 재사용), 책 페이지 캐시, 파서, `_extract_verses()` 체인 편입.
3. `scrape_bible_to_db.py` — `TRANSLATION_SOURCE_REQUIREMENTS` 외 3개 표, `get_source_name`/`get_source_version` 분기.
4. `pytest -q` 전량 통과 확인. **기존 109개가 그대로 통과해야 한다.**
5. `--test-genesis1`, `--test-book 19 --test-chapter 119`(표제 22개), `--test-book 2 --test-chapter 22`(분할)로 DB 없이 확인.
6. **DB 시드** — CHECK 제약 1개 값 → `bible_translation` 1행 → `bible_book` 66행. 순서를 지킨다.
7. 한 권 적재(창세기)로 절 수·본문을 확인한 뒤 전권.
8. [7](#7-검증) 전체 실행. 특히 [7.3](#73-루비-누출-검증)과 [7.6](#76-제2-증인-대조).

저장소가 요구하는 신규 소스 체크리스트(CLAUDE.md "Adding a new source")와의 대응은 이렇다. 이 소스는 **항목이 세 개 늘어난다.**

| CLAUDE.md 단계 | 이 설계에서 | 비고 |
| --- | --- | --- |
| 1 `_is_<source>_source()` | [5.1](#51-scraperpy--책-페이지-캐시와-장-분리) | 호스트 판별 |
| 2 `_build_<source>_url()` | [4.1](#41-url-규칙--책-단위-한-페이지) | `#{chapter}` 프래그먼트를 붙인다 |
| 3 `_discover_chapter_urls_for_<source>()` | [4.1](#41-url-규칙--책-단위-한-페이지) | `KJV_CHAPTER_COUNTS` 재사용, 프로브 없음 |
| 4 `_extract_verses_from_<source>()` + 체인 | [5.2](#52-scraperpy--파서) | eBible 뒤, `bibletable` 앞 |
| 5 `get_source_name()` 등 분기 | [5.2](#52-scraperpy--파서)·[5.3](#53-scrape_bible_to_dbpy--역본-등록) | `get_source_version()` 분기 포함 |
| 6 엔트리 URL 해석 | [5.3](#53-scrape_bible_to_dbpy--역본-등록) | **[5.4](#54-기존-동작이-바뀐다--일본어-역본이-둘이-된다)의 파급을 함께 볼 것** |
| 7 `TRANSLATION_SOURCE_REQUIREMENTS` | [5.3](#53-scrape_bible_to_dbpy--역본-등록) | 잘못 적재를 막는 마지막 방어선 |
| 8 `resolve_book_code_for_source()` | [5.3](#53-scrape_bible_to_dbpy--역본-등록) | `None` 반환 + 전용 슬러그 상수 |
| **추가 A** `_fetch_soup()` 분기와 책 페이지 캐시 | [5.1](#51-scraperpy--책-페이지-캐시와-장-분리) | 체크리스트에 없는 신규 구조 |
| **추가 B** `JPNBIBLE_BOOK_SLUGS` 상수 | [4.1](#41-url-규칙--책-단위-한-페이지) | `book_key`로 대체 불가 |
| **추가 C** 문서 갱신 | 아래 | 계약 문서가 바뀐다 |

**추가 C가 빠지기 쉽다.** 이 소스는 CLAUDE.md에 적힌 전제 두 가지를 깬다.

- "per-source chapter URL을 만들어 HTML을 가져온다"는 데이터 흐름 설명 — 이 소스는 **책 단위**다.
- 파서 계약 절에 **루비 규칙**([4.3](#43-함정-1-루비를-지우지-않으면-읽기가-본문에-섞인다))이 없다. `CJK_JOIN_PATTERN` 항목 옆에 같은 무게로 들어가야 다음 사람이 지우지 않는다.

README의 지원 소스 표·엔트리 URL 목록·실행 예([5.4](#54-기존-동작이-바뀐다--일본어-역본이-둘이-된다))도 함께 고친다.

**6번은 3번보다 뒤여야 한다.** 역본을 먼저 등록하면 `_expected_translation_type()`이 첫 일치를 돌려주는 탓에 기존 실행이 흔들릴 수 있다(SBLM에서 확인된 순서 의존이다).

---

## 12. 리스크

### 리스크 1. 루비를 지우지 않고 적재 (가장 큼)

루비가 붙은 한자가 있는 절 전부에 읽기가 섞인다 — 창세기·마가·시편 표본 2,205절 중 **2,197절(99.6%)** 이다. 그러면서 절 수·연속성·빈 절 검사를 **모두 통과한다.** [7.3](#73-루비-누출-검증)의 질의가 유일한 방어이며, `get_text()`로 확인하면 문제가 없어 보이므로 테스트를 파서 결과로 작성해야 한다.

### 리스크 2. 책 페이지 캐시가 조용히 무력화

캐시가 깨져도 **결과는 정상**이고 요청만 1,189회로 는다. 시편에서만 270 MB를 받는다. 테스트로 `_request_html` 호출 횟수를 고정한다.

### 리스크 3. 병합 `id`의 마지막 토큰을 놓침

시 132는 토큰이 세 개다. 두 번째까지만 읽으면 5절이 사라지고 그 장만 연속성이 깨진다. 전권 연속성 검사가 잡지만, **검사를 돌리지 않으면 1개 절이 조용히 빈다.**

### 리스크 4. 분할 절을 문서 순서로 합침

출 22:3 한 절뿐이지만 모든 자동 검사를 통과한다. 픽스처로 고정한다.

### 리스크 5. 訂正 후 본문을 섞어 적재

wordproject 등 訂正 판본에서 일부를 보충하면 **권리 상태가 다른 텍스트가 섞인다.** 소스를 하나로 고정하고, 대조는 [7.6](#76-제2-증인-대조)처럼 **읽기 전용**으로만 한다.

### 리스크 6. 적재 도중 소스를 바꿈

jpn.bible이 중간에 사라지면 religious-life로 갈아타고 싶어진다. 그런데 두 소스는 **괄호 위치와 절 경계 규약이 다르다**([7.6](#76-제2-증인-대조)). 앞 절반과 뒤 절반이 다른 규약으로 들어가면 어떤 검사도 잡지 못하고, 나중에 정오표를 만들 기준도 사라진다. 소스를 바꿔야 한다면 **처음부터 다시 적재한다.**

### 리스크 7. 관할을 혼동한 채 배포

[1.2](#12-제시된-근거-검토)의 표에서 미국은 2049/2050년까지 보호 기간이 남아 있다. 적재 자체와 별개로 **서비스 대상 지역**에 따라 판단이 달라진다. 이 문서는 사실 관계만 정리한 것이고 결정은 사용자 몫이다.

---

## 13. 결론

제시된 "Public Domain*" 표기는 **일본 기준으로 정확하고, 미국 기준으로는 정확하지 않다.** 앞 문서가 이 판본을 배제한 것도 같은 사실의 다른 면이었다. 한국에서 운영하는 이 프로젝트에는 저작권법 제3조 제4항이 적용되며, 권리자 본인이 만료를 명시하고 있다.

다만 권리자는 **訂正한 낱말에는 저작권이 남아 있다**고 밝혔다. 그래서 절 번호가 가장 깨끗한 후보(wordproject)가 오히려 쓸 수 없는 소스가 되고, 원본을 싣는 네 곳 중에서 골라야 한다. 전수 또는 표본 대조 결과는 이렇다.

| 소스 | 절 번호 결함 | 본문 소실 |
| --- | --- | --- |
| **jpn.bible** | **0** (1,189장 전수) | **0** |
| religious-life | 12개 장 (1,189장 전수) | 0 |
| baiburu | 병합을 뒤 번호에만 표기 | **출 22:3** |
| STEPBible(`JapKougo`) | 절 구분 체계가 다름 | **시 130~133** |

선택은 **결함의 성격**을 고른 것이기도 하다. jpn.bible에도 계보에서 물려받은 글자 오류가 있지만([7.6](#76-제2-증인-대조)) 목록으로 만들 수 있는 다섯 절이고, religious-life의 절 번호 결함은 올바른 모양의 연속 목록을 만들어 내므로 자동 검사로 걸리지 않는다.

- 소스: `https://jpn.bible/kougo/{book}` — 66 요청, 25 MB(비압축)
- 예상 적재량: 66권 / 1,189장 / **31,104절** (KJV 대비 +2, 차이는 4개 장)
- 구조 변경: 책 페이지 캐시 + 장 분리 1곳, 새 파서 1개
- 파서 함정: 루비 제거, 병합 16, 분할 1, 괄호 이동 19, 표제 138
- DB 선행: CHECK 값 1개, `bible_translation` 1행, `bible_book` 66행

미결정 사항은 하나다. **병합 절 저장 방식**([4.4](#44-함정-2-병합-절-16건))이며, [jpn1965 설계](new-japanese-nt-scraping-design.md)와 **같은 값으로** 정해야 한다. 이 문서는 B안을 권고하고, 예상 절 수 31,104는 B안 기준이다.
