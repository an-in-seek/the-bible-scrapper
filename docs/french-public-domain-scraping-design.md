# 프랑스어 퍼블릭 도메인 성경(Louis Segond 1910 · Ostervald · Martin) 본문 스크래핑 개발 설계

## 1. 목적

프랑스어 개신교 전통 역본 세 종 — **Louis Segond 1910**, **Ostervald**, **David Martin** — 을 스크래핑하여 기존 PostgreSQL 스키마(`bible_chapter`, `bible_verse`)에 적재할 수 있는지 판단하고, 적재할 수 있는 것의 설계를 정한다.

이 문서의 소스·DOM·절 수 서술은 **세 역본 전권(각 1,189장)을 실제로 수집해 저장소의 파서로 돌린 결과**다. 확인 범위는 [3절](#3-실측-검증-범위)에 있다.

### 1.1 제시된 근거 검토

요청과 함께 세 역본의 특징과 라이선스가 제시됐다. 항목별로 확인한 결과다.

| 제시된 서술 | 판정 | 근거 |
| --- | --- | --- |
| LSG 1910 — 1910년 개정판은 퍼블릭 도메인 | **맞음** | 프랑스어 위키백과 「Bible Segond」: 1910년 개정본은 퍼블릭 도메인이라고 적는다. eBible도 `public domain`. 1931년 이전 발행이라 미국에서도 보호 대상이 아니다 |
| (주의) "1978년판 'Nouvelle Bible Segond(NBS)'" | **틀림** | 1978년판은 **「Segond révisée, dite à la Colombe」** 다. NBS는 **2002년**이다(같은 항목: 1979 NEG, 2007 Segond 21). "현대 개정판은 저작권이 유효하다"는 결론 자체는 맞다 |
| Ostervald — "칼뱅의 사촌인 올리베탕 번역본을 오스터발이 개정" | **부분적으로 맞음** | 올리베탕이 칼뱅의 사촌인 것은 맞다(위키백과 「Pierre Robert Olivétan」). 그러나 오스터발이 개정한 것은 **제네바 목사회 역본(Bible de Genève)** 이다(위키백과 「Jean-Frédéric Ostervald」). 올리베탕 1535년판의 후손이지 올리베탕판 자체가 아니다 |
| Ostervald 1744 / 1886 개정판 | **연도는 맞다. 1886년판은 오스터발의 개정이 아니다** | 1744년이 오스터발 개정판의 초판이다(오스터발 1747년 사망). 1886년판은 **프랑스 성서공회(Société biblique de France)가 1881년에 처음 낸 개정판의 1886년 판**이다(1996년 개정판 서문이 1881년 서문을 인용하며 이렇게 적는다) |
| Ostervald — 퍼블릭 도메인 | **1744년판은 맞다. 그러나 온라인에서 구하는 텍스트는 1996년 개정판이다** | eBible `fra_fob`를 대조한 결과 1996년 개정판이다([1.3](#13-온라인에-실제로-있는-판본)). 1881/1886년판은 발행 140년이 지났지만 개정 참여자 전원의 생몰년은 확인하지 않았다 |
| Martin 1707 / 1744 개정판 | **맞음** | 1707년 암스테르담 전서(신약은 1696년 위트레흐트)가 위키백과에 있다. 1744년판은 피에르 로크(Pierre Roques)가 손본 판이라고 배포처들이 적는다 |
| Martin — "종교개혁 시기 … 고전 번역본" | **틀림** | 마르탱(1639–1721)의 작업은 1696~1707년으로, 종교개혁(1517)보다 한 세기 반 이상 뒤다. 새 번역도 아니고 왈롱 교회의 요청으로 한 **제네바 성경의 개정**이다(위키백과 「David Martin (théologien)」: 1710년 레이우아르던 총회 승인) |
| Martin — 수용본문(Textus Receptus) 기반 | **실측과 부합** | 요일 5:7의 삼위 증언 구절, 행 8:37 등 수용본문 계열 독법이 모두 들어 있다([10.2](#102-martin--보류)) |
| LSG — 표준적 위상, 직역 중심 문체 | 평가 서술 | 검증 대상이 아니다 |

배포처 쪽에도 틀린 서술이 있다. eBible의 LSG 저작권 페이지는 `The first edition of the Bible Segond was published in 1910`이라고 적지만, 1910년판은 **개정판**이다. 위키백과 「Bible Segond」에 따르면 스공의 구약은 1874년에 처음 나왔고(이때 신약은 올트라마르 역), 스공 자신의 신약은 1879년에 완성되어 1880년부터 1910년까지 30만 부가 나왔다. 1910년 개정은 스공이 1880년 12월 25일 영국 해외성서공회(British and Foreign Bible Society)에 보낸 동의 서신에 따라 프랑스·스위스 목사와 신학자들이 했다.

> 이 문서는 법률 자문이 아니다. 권리에 관한 서술은 배포처·위키백과·판본 서문의 표기를 조회한 결과이며 판단은 사용자 몫이다.

### 1.2 판본 계보 — 무엇이 퍼블릭 도메인인가

세 역본 모두 "이름"이 하나의 텍스트를 가리키지 않는다. 같은 이름으로 여러 세기에 걸친 개정판이 있고, 그중 오래된 것만 퍼블릭 도메인이다.

| 계보 | 판 | 상태 (조회 결과) |
| --- | --- | --- |
| **Segond** | 1874 구약(신약은 올트라마르 역) · 1880년부터 스공 신약 포함 (루이 스공, 1810–1885) | 보호 기간 만료 |
| | **1910 개정판** (스공의 동의 아래 프랑스·스위스 목사·신학자들이 개정) | **퍼블릭 도메인** — 위키백과가 명시, eBible `public domain` |
| | 1978 Colombe · 1979 NEG · 2002 NBS · 2007 Segond 21 | 보호 대상 |
| **Ostervald** | **1744** (장프레데리크 오스터발, 1663–1747, 제네바 역본 개정) | 보호 기간 만료 |
| | 1881 프랑스 성서공회 개정 · 1886년판 | 발행 140년 경과. 개정 참여자 전원의 생몰년은 미확인 |
| | **1996 개정판** — "1886년판의 갱신"(서문) | **권리 보유자 불명.** 배포처는 `public domain`으로 표기하지만 그 근거를 찾지 못했다 |
| **Martin** | 1696 신약 · **1707** 전서 (다비드 마르탱, 1639–1721, 제네바 역본 개정) | 보호 기간 만료 |
| | **1744년판** (피에르 로크 수정) | 보호 기간 만료 |

권리 관점의 결론은 단순하다. **1910년 LSG, 1744년 Ostervald, 1707/1744년 Martin은 관할을 가리지 않고 깨끗하다.** 문제는 권리가 아니라 **온라인에 실제로 있는 텍스트가 그 판인가**다.

### 1.3 온라인에 실제로 있는 판본

#### LSG — eBible `fraLSG`는 1910년판이다

위키백과는 1910년 개정에서 바뀐 교리 용어의 예로 `prêtres`를 `sacrificateurs`로, `fidélité`를 `foi`로 바꾼 것을 든다. eBible `fraLSG` 전권에서 세어 보면 `sacrificateur`가 **846회**, `prêtre`가 **46회**이고, `prêtre` 46회는 **전부 이방·우상·산당의 제사장**이다 — 창 41:45 `Poti-Phéra, prêtre d’On`, 삿 17–18장 미가의 사사로운 제사장, 왕상 12:32 산당 제사장, 왕하 11:18 `Matthan, prêtre de Baal`, 렘 48:7 그모스의 제사장, 암 7:10 벧엘의 아마샤, 행 14:13 `Le prêtre de Jupiter` 등. 아론 계열 제사장(레 1:5 등)은 모두 `sacrificateurs`다. 1910년판의 구분과 일치한다.

#### Ostervald — eBible `fra_fob`는 1744년판이 아니라 1996년 개정판이다

eBible 메타데이터는 이 역본의 SWORD 모듈 이름을 `fraFOB1744eb`로 적어 1744년판처럼 보이게 하지만, 본문 설명은 `The Holy Bible in French, Ostervald`뿐이고 판을 밝히지 않는다. 판을 가리기 위해 두 텍스트와 대조했다.

- **1996년판**: 1996년 개정판 서문을 함께 싣고 "révisée en 1996"이라고 밝히는 사이트(lueur.org)의 본문
- **1877년판**: `gratis.bible/fr/bo1877/` (1877년 인쇄본을 입력했다고 밝힌 텍스트)

| 장 | 절 | 1996년판과 일치 | 1877년판과 일치 |
| --- | --- | --- | --- |
| 창 1 | 31 | **31** | 4 |
| 시 23 | 6 | **6** | 0 |
| 마 6 | 34 | 31 | 12 |
| 요 3 | 36 | 35 | 10 |
| 요일 5 | 21 | **21** | 3 |
| 합계 | 128 | **124** | 29 |

1996년판과 다른 4절 중 3절은 **합자 표기**(`œil`/`oeil`, `œuvres`/`oeuvres`) 차이다. 나머지 1절(마 6:21)은 eBible 쪽이 `cœur`를 `cour`로 적은 것으로, eBible Ostervald에 되풀이되는 결함이다([10.1](#101-ostervald--보류)). 1877년판과의 차이는 성격이 다르다. 첫 두 절을 보면 분명하다.

```
eBible fra_fob   Au commencement, Dieu créa les cieux et la terre.
                 Or la terre était informe et vide, et les ténèbres étaient à la surface de l'abîme, …
1996년판         (위와 같음)
1877년판         Dieu créa, au commencement, les cieux et la terre.
                 Et la terre était sans forme et vide, et les ténèbres  étaient  sur la face de l’abîme, …
```

**eBible의 Ostervald는 1996년 개정판이다.** 1996년판의 권리는 확인되지 않는다.

- 서문은 개정 주체를 밝히지 않는다. 조회한 어느 문서도 1996년 개정자나 권리 포기 선언을 제시하지 않았다.
- 배포처(eBible)는 `public domain`으로 표기하지만, 1996년판을 1744년판처럼 보이게 하는 모듈 이름을 쓰는 곳이라 그 표기를 1996년 개정분의 권리 근거로 삼기 어렵다.
- 1996년 개정이 창작성 있는 개정이라면, 저작자가 드러나지 않은 저작물의 프랑스법상 보호 기간은 공표 다음 해부터 70년, 즉 **2066년 말**까지다.

직전 和合本 작업([1.3](chinese-union-version-1919-scraping-design.md#13-ebible의-중국어-화합본은-1919년판이-아니다))과 같은 구도다 — **요청은 옛 판인데 가장 손쉬운 소스는 새 개정판**이다.

#### 옛 Ostervald 텍스트는 있지만 출처가 좁다

1877년판 텍스트는 두 곳에서 확인했다.

| 소스 | 관찰 |
| --- | --- |
| `levigilant.com/bible_vaudoise/ostervald_1877/` | 「Exclusivité de GoDieu.com et LeVigilant.com - Août 2011」, OCR 입력 후 교정했다고 적는다. 원 인쇄본의 이탤릭(보충어)을 살렸다고 한다 |
| `gratis.bible/fr/bo1877/` | 장 단위 정적 페이지(`/fr/bo1877/gen/1`). `Rights`·`Publisher`·`Contributor` 칸이 모두 `Fehlt`(없음)이고 `Creator`는 변환 스크립트(`VplToZefaniaXML.ps1`)다. 이탤릭 마크업이 빠지면서 **그 자리에 이중 공백만 남아 있다**(`les ténèbres  étaient  sur`) |

1877년 인쇄본 자체는 보호 기간이 끝났다. 그러나 입력본을 배포하는 쪽이 "독점"을 표기하고 있고, 두 번째 사이트는 출처와 권리를 밝히지 않는다. 입력본에 대해 무엇을 주장하는지는 확인하지 못했다.

#### Martin — 한 가지 입력본이 여러 사이트에 퍼져 있다

studybible.info의 `Martin`은 lueur.org가 "1744년판(1707년판을 P. Rocques가 손봄), 알베르 호프만(Albert Hofmann)의 디지털화, 허락을 받아 게시, 원 사이트는 더 이상 없음"이라고 밝힌 텍스트와 **낱말이 같다.** 네 장(창 1, 시 23, 요 3, 요일 5) 94절을 대조하면 아래 두 차이를 걷어낸 뒤 **94절 모두 일치**한다.

- lueur.org는 보충어를 `[ ]`로 표시하는데(원 인쇄본의 이탤릭), **studybible은 괄호를 뺐다**: `les ténèbres [étaient] sur` → `les ténèbres étaient sur`
- lueur.org는 `;` `!` 앞에도 공백을 두는 프랑스식 구두점을 쓰고, studybible은 그 공백을 뺐다(`:` 앞 공백은 남아 있다: `Dieu dit : Que la lumière soit;`)

두 사이트 모두 같은 입력 오류를 공유한다(요 3:18 `n'a point crut` — `cru`의 오기). 같은 입력본이라는 증거다. studybible 쪽 판본 설명 페이지(`/version/Martin`)는 PHP 오류만 출력하고, 본문 상자의 버전 정보 링크는 `title`에 `French Martin Bible 1910`이라고 적는데 1910년 Martin판이라는 것은 확인되는 바가 없다.

> **lueur.org는 소스 후보에서 뺐다.** `robots.txt`가 `ClaudeBot`·`anthropic-ai`·`Claude-Web` 등 AI 크롤러를 명시적으로 차단한다. 판본 판별을 위해 이 사실을 확인하기 전까지 페이지 17회를 요청했고(마지막 4개 — 민 12·13장, 출 37장, 신 28장 — 는 `robots.txt`와 같은 요청 묶음), 확인한 뒤로는 요청하지 않았다. 이 문서의 lueur.org 대조는 모두 그 17개 응답으로 한 것이다.

### 1.4 후보 소스 비교

| 후보 | 판 | 상태 (실측) | 판정 |
| --- | --- | --- | --- |
| **eBible `fraLSG`** | LSG 1910 | 1,189장 / 31,170절. 기존 eBible 어댑터로 파싱됨. **LSG 원래의 절 체계**(KJV와 106개 장이 다름). 파서가 만드는 결함 둘(고칠 수 있음) | **채택 권고 (A)** |
| studybible `Segond` | LSG 1910 | 1,189장 / 31,102절. 기존 studybible 어댑터로 파싱됨. **KJV 절 체계.** 소스 결함 63곳 이상과 표기 손실(고칠 수 없음) | 대안 (B) |
| eBible `fra_fob` | **Ostervald 1996** | 1,189장 / 31,107절. 판이 요청과 다르고 권리 근거가 없다. 본문 결함 3종 | 보류([10.1](#101-ostervald--보류)) |
| `gratis.bible/fr/bo1877/` | Ostervald 1877 | 표본만 확인. 권리 표기 없음, 이탤릭 자리 이중 공백. 새 어댑터 필요 | 보류([10.1](#101-ostervald--보류)) |
| studybible `Martin` | Martin 1744 (호프만 입력본) | 1,189장 / 31,057절. **92개 장에서 절 번호가 내용과 어긋난다** | 보류([10.2](#102-martin--보류)) |
| lueur.org | Ostervald 1996 · Martin 1744 | `robots.txt`가 AI 크롤러 차단 | 제외 |
| bible.com(YouVersion) | 여러 판 | 앱 플랫폼이라 조사하지 않았다 | 제외 |

eBible에는 Martin이 **없다**(`translations.csv` 1,551행 중 `fra` 5행: `fraLSG`, `fra_fob`, `frajnd`(Darby), `francl`(néo-Crampon, 저작권 표기), `frasbl`(현대 자유역)).

---

## 2. 결론 먼저

1. **권리는 옛 판 기준으로 모두 깨끗하다. 문제는 온라인 텍스트가 그 판인지, 그리고 구조가 맞는지다.** 세 역본의 결론이 모두 다르다.
2. **LSG 1910 — 적재할 수 있다. eBible `fraLSG`(A)를 권고하되, 절 체계 결정이 먼저다.** 같은 1910년 본문이 두 소스에 있고, 두 소스를 전권 낱말 대조했다(779,734낱말, 차이 290곳).
   - **A는 LSG 원래의 절 체계**다. 히브리어 성경처럼 긴 시편 표제를 1절로 세고(62편), 출 7–8장·레 5–6장·욥 38–41장 등 44개 장에서 장 경계가 다르다. **KJV와 절 수가 다른 장이 106개**로, 이미 적재된 11개 역본의 최대치(RVR1909, 12개)의 약 9배다([4.5](#45-함정-3-절-체계가-kjv와-106개-장에서-다르다)).
   - **B(studybible)는 같은 본문을 KJV 절 체계로 다시 나눈 것**이지만 소스 쪽 결함을 고칠 수 없다 — 절 첫머리의 악센트 글자 61곳이 사라졌고(`à la chaîne`→`la chaîne`, `Écoute`→`coute`), 장 끝 두 곳에 책 이름이 붙었고(`… hors de son pays. Exode`), 대문자 악센트·여는 괄호·대괄호가 전부 없다([4.10](#410-b안--같은-본문의-kjv-절-체계판-그러나-소스-결함이-있다)).
   - **기준 충돌을 먼저 밝힌다.** 그리스어 구약 때 정한 "구조가 어긋나면 중단"([N1904 설계 13](greek-new-testament-nestle-1904-scraping-design.md#13-결론))을 그대로 적용하면 A는 중단 대상이다. 이 문서는 A를 권고하지만 **이 결정은 사용자 몫이다**([4.11](#411-절-체계-결정)). → **A로 결정되어 구현·적재했다**([14장](#14-구현적재-결과-실측)).
3. **A는 파서를 두 곳 고쳐야 한다.** 둘 다 모든 자동 검사(절 수·연속성·숫자·빈 절)를 통과하는 오염이다.
   - 소제목 `div.ms2`가 제거 셀렉터에 없어 **창 11:9 끝에 `DEPUIS ABRAHAM JUSQU’À JOSEPH`가 붙는다**([4.3](#43-함정-1-소제목-하나가-창-119에-붙는다)).
   - 각주 마커가 두 낱말 사이의 **유일한 경계**인 곳이 189곳이라, 마커를 지우면 `et on`이 `eton`으로 붙는다(마 5:15 등, 복음서·계시록에 몰림)([4.4](#44-함정-2-각주-마커가-유일한-낱말-경계인-곳이-189곳)).
4. **B를 택하면** studybible 어댑터의 신약 전용 방어(`book_order < 40` 거부)를 역본별로 바꿔야 한다([5.2](#52-b안--studybible-segond)).
5. **Ostervald — 보류.** eBible의 Ostervald는 1744년판이 아니라 **1996년 개정판**이고, 그 개정분의 권리 근거를 찾지 못했다. 본문 결함도 셋이다 — 왕하 14–24장 11곳에 깨진 태그 문자열 `‘br wp="br1"’`, `cœur`→`cour` 등 `œ` 탈락 20곳 이상, 앞부분이 잘린 시편 표제([10.1](#101-ostervald--보류)).
6. **Martin — 보류.** 기존 어댑터로 읽히는 유일한 소스(studybible)는 히브리어 절 체계의 원본을 KJV 절 수에 **억지로 맞췄다.** 절 수가 KJV와 같은데도 내용이 한 절씩 밀린 장이 64개(시편 53편), 본문 없는 절 마커 45개 — 모두 합쳐 **92개 장(7.7%)**. 원 체계의 Martin을 구해도 LSG A와 같은 절 체계 결정이 남는다([10.2](#102-martin--보류)).
7. **DB 작업**: `language_code` CHECK에 `fr` 추가(프랑스어 첫 역본), `translation_type` CHECK 35번째 값 `LSG1910`, `bible_translation` 1행, `bible_book` 66행. `bible_book_description`의 `fr` 66행은 선택([6장](#6-db-준비)).

---

## 3. 실측 검증 범위

| 검증 | 방법 | 결과 |
| --- | --- | --- |
| 역사·권리 서술 | 프랑스어 위키백과 원문(`action=raw`) 3개 항목, eBible `copyright.htm`·`details.php`, 1996년 Ostervald 서문 | [1.1](#11-제시된-근거-검토)·[1.2](#12-판본-계보--무엇이-퍼블릭-도메인인가) |
| eBible 프랑스어 목록 | `translations.csv` 전량 | `fra` 5행, Martin 없음 |
| LSG 판본 | 1910년 개정 지표(`sacrificateur`/`prêtre`) 전권 집계 | 846 / 46, `prêtre`는 전부 이방 제사장 |
| Ostervald 판본 | 1996년판·1877년판과 128절 대조 | 1996년판 124, 1877년판 29 |
| Martin 입력본 | lueur.org 1744년판과 94절 대조 | 괄호·구두점 공백 제거 후 94절 일치 |
| **LSG A (eBible)** | **1,189장 전권** 수집, 저장소 파서로 파싱, 클래스·각주 위치 전수 조사 | 31,170절, 파서 기인 오염 2종([4.3](#43-함정-1-소제목-하나가-창-119에-붙는다)·[4.4](#44-함정-2-각주-마커가-유일한-낱말-경계인-곳이-189곳)) |
| **LSG B (studybible)** | **1,189장 전권** 수집·파싱, 원 페이지 마커 전수 | 31,102절, 1,189장 모두 KJV 절 수 |
| **A·B 전권 대조** | 66권 각각 낱말 열(악센트·대소문자·구두점 제거) 비교, 차이 290곳 전수 분류 | [4.10](#410-b안--같은-본문의-kjv-절-체계판-그러나-소스-결함이-있다) |
| **Ostervald (eBible)** | **1,189장 전권** 수집·파싱 | 31,107절, 결함 3종 |
| **Martin (studybible)** | **1,189장 전권** 수집·파싱, 원 페이지 마커 전수, Ostervald와 절별 낱말 겹침 비교 | 92개 장 결함 |
| KJV 대조 | DB의 KJV 장별 절 수(1,189장/31,102절)와 비교 | 각 절 |
| 기존 역본 선례 | DB의 11개 역본 장별 최대 절 번호를 KJV와 비교 | RVR1909 12개 장이 최대 |
| 기존 적재분 영향 | RVR1909·SBLM 등에서 대문자 소제목 흔적 조회, SBLM 20장 표본에서 각주 마커 위치 조사 | 둘 다 0건 |
| DB 현황 | `bible_translation`·CHECK·`bible_book` 형식 조회, 문서의 SQL을 읽기 전용 세션에서 실행 | [6.1](#61-현재-상태-실측-2026-09-27) |
| 약관 | `robots.txt` 5개 사이트 | [9.1](#91-요청-간격과-소요) |

수집은 흐름마다 요청 사이 1초 이상 간격을 두었고, 한 호스트에 동시에 둔 흐름은 최대 둘이었다(eBible·studybible 각각 한동안).

### 3.1 확인하지 못한 것

1. **인쇄본을 보지 못했다.** A와 B가 갈리는 곳 중 한쪽의 명백한 누락·오타가 아닌 곳([4.10](#410-b안--같은-본문의-kjv-절-체계판-그러나-소스-결함이-있다))은 어느 쪽이 1910년 인쇄본인지 확인할 수단이 없다. 대문자 악센트를 인쇄본이 어떻게 찍었는지도 모른다.
2. **1996년 Ostervald의 개정자와 권리 상태를 찾지 못했다.** 찾지 못했다는 것이 권리가 없다는 뜻은 아니다.
3. **Ostervald 1877년판은 표본만 봤다.** 권리와 출처 문제가 먼저라 전권을 수집하지 않았다.
4. **Martin의 다른 소스를 전부 조사하지는 않았다.** 원 절 체계를 그대로 싣는 곳(lueur.org)은 AI 크롤러를 막고 있어 제외했고, 나머지는 [10.2](#102-martin--보류)에 적었다.
5. **각주 마커 수정이 기존 역본에 주는 영향은 표본으로만 봤다.** SBLM 20장(각주 63개)에서 해당 위치가 0건이었다. 수정 후 [7.8](#78-기존-역본-회귀-검증)의 전권 확인이 필요하다. → 전권 확인에서 SBLM 1곳(눅 4:18)이 나왔다([14.3](#143-기존-역본-회귀)).
6. **법적 판단은 하지 않았다.** [1.1](#11-제시된-근거-검토)·[1.2](#12-판본-계보--무엇이-퍼블릭-도메인인가)는 각 출처의 표기를 옮긴 것이다.

---

## 4. LSG 페이지 특성

### 4.1 URL 규칙 — 기존 eBible과 같다

```text
https://ebible.org/fraLSG/{USFM 대문자}{장}.htm      시편만 3자리, 나머지 2자리
```

`GEN01.htm`, `PSA003.htm`, `REV22.htm`. 1,189개 URL이 모두 200이었다. RVR1909·SBLM·JPNMEB와 같은 규칙이라 `_build_ebible_chapter_segment()`를 그대로 쓴다.

### 4.2 DOM 구조

기존 eBible 역본과 뼈대는 같지만 **들어 있는 것이 훨씬 많다.** 1,189장 전수 결과(`div.main` 안, 주요 항목):

| 요소 | 개수 | 처리 |
| --- | --- | --- |
| `span.verse` | 31,170 | 절 마커 |
| `div.q` / `div.p` / `div.m` | 23,917 / 2,594 / 118 | 본문 — 유지 |
| `span.wj` (예수의 말씀) / `span.it` (이탤릭) | 2,644 / 159 | 본문 — 유지 |
| `a.notemark` + `span.popup` | 9,751 | **전부 상호참조**(`p.x`) — 제거 |
| `div.r` (평행 본문 참조) | 2,786 | 제거 |
| `div.s` (소제목) | 1,476 | 제거 |
| `div.b` (빈 줄) / `div.qs` (`— Pause.`) | 144 / 74 | 유지(`Pause`는 본문) |
| `div.ip`·`div.io`·`div.ie`·`div.imt`·`table` 등 **책 소개문** | 499·165·66·65·13 … | 각 책 1장 첫 마커 **앞**에만 있다 — 파서가 자연히 버린다 |
| `div.ms` / `div.mr` / **`div.ms2`** | 24 / 25 / **8** | ms·mr은 제거, **ms2는 제거 목록에 없다**(4.3) |

eBible 역본 중 **소개문과 상호참조가 붙은 첫 사례**다.

- 소개문은 모두 1장 첫 절 마커 **앞**에 있었다(1,189장 전수, 마커 뒤 0건). 누적 파서는 첫 마커 전에는 아무것도 모으지 않는다. 1910년 본문이 아니라 현대 해설이므로(`Le troisième discours de Moïse (28:69–30:20) …`) 버리는 것이 맞다.
- 각주 9,751개는 **모두 상호참조**(`p.x`)이고 본문 이문(異文) 각주는 없다. `EBIBLE_FOOTNOTE_SELECTOR`가 `a.notemark`를 팝업째 지운다. 파싱 결과에 숫자가 들어간 절이 **0개**다. 다만 지우는 방식에 문제가 있다(4.4).

### 4.3 함정 1. 소제목 하나가 창 11:9에 붙는다

주 소제목은 `div.ms`(1단계)·`div.ms2`(2단계)로 온다. 대부분 책 첫머리, 즉 첫 마커 앞에 있지만 **창 11장과 출 15장에는 절 사이에 있다.**

```text
창 11:9 뒤   div.ms   LES ANCÊTRES DU PEUPLE D’ISRAËL        ← 제거됨
             div.ms2  DEPUIS ABRAHAM JUSQU’À JOSEPH          ← 제거 목록에 없음
             div.mr   Ch. 11:10 à 50. (És 51:1, 2. …)         ← 제거됨
출 15:21 뒤  div.ms   LE PEUPLE D’ISRAËL DANS LE DÉSERT      ← 제거됨
             div.mr   Ch. 15:22 à 40. (…)                     ← 제거됨
```

`EBIBLE_REMOVABLE_SELECTOR`에 `div.ms`·`div.ms1`은 있고 `div.ms2`는 없다. 현재 파서로 돌리면:

```text
창 11:9  … et c’est de là que l’Éternel les dispersa sur la face de toute la terre. DEPUIS ABRAHAM JUSQU’À JOSEPH
```

SBLM 때 `div.d`로 겪은 것과 같은 종류다(CLAUDE.md). 대문자가 12자 넘게 이어지는 절을 LSG 전권에서 찾으면 이 한 건뿐이다. 이미 적재된 RVR1909·SBLM에서 같은 조회를 하면 0건이다 — `div.ms2`는 LSG에서 처음 나타난다.

### 4.4 함정 2. 각주 마커가 유일한 낱말 경계인 곳이 189곳

LSG는 각주 마커를 낱말 **사이**에 공백 없이 끼운 곳이 있다.

```html
<span class='wj'>et</span><a class="notemark">j<span class="popup">Mc 4:21. …</span></a><span class='wj'>on n’allume pas …
<span class='it'>Mais</span><a class="notemark">b<span class="popup">2 Ch 36:16, 17, etc.</span></a><span class='it'>après que nos pères …
```

화면에서는 위첨자 `j`가 두 낱말을 갈라 보이지만, 파서가 마커를 `decompose()`하면 사이에 아무것도 남지 않는다.

```text
마 5:15   … et on n’allume pas …        →   … eton n’allume pas …
스 5:12   Mais après que nos pères …   →   Maisaprès que nos pères …
```

9,751개 마커의 앞뒤 글자를 전수 조사하니 **양쪽이 모두 문자인 곳이 189곳**이다 — 마 62, 요 44, 눅 40, 계 25, 막 14, 스 3, 행 1. 예수의 말씀(`span.wj`)과 이탤릭(`span.it`)이 마커를 사이에 두고 끊긴 자리다. 숫자·연속성 검사는 물론 [7.3](#73-오염-검증--이-소스-필수)의 대문자 검사로도 잡히지 않는다. B와의 전권 대조(4.10)에서 **낱말 경계 차이 191곳**으로 드러났고, 책별 개수까지 위 189곳과 일치한다(나머지 2곳은 창세기의 eBible 원문 하이픈 누락: 12:1 `Vat’en`, 50:10 `audelà`). 막 9:49 `serasalé`(sera salé)도 그중 하나다.

같은 파서를 쓰는 SBLM에서 20장(각주 63개)을 표본 조사하면 이런 위치가 0곳이다. RVR1909에는 각주가 없고, JPNMEB는 공백을 쓰지 않는 문자라 영향이 없다. (수정 후 SBLM 전권을 확인하니 1곳 — 눅 4:18 `corazonesrotos` — 이 있었고, 고쳤다. [14.3](#143-기존-역본-회귀))

### 4.5 함정 3. 절 체계가 KJV와 106개 장에서 다르다

**가장 중요한 사실이다.** 장 수는 66권 모두 `KJV_CHAPTER_COUNTS`와 같고 구멍(절 번호 누락)도 없다. 그러나 절 수가 KJV와 다른 장이 **106개**다.

| 구분 | 장 수 | 내용 |
| --- | --- | --- |
| 시편 표제를 1절로 셈 | **62** | 시 3편: KJV 8절 / LSG 9절. 표제가 두 절인 시편 4편(51, 52, 54, 60)은 +2 |
| 장 경계·절 나눔이 다름 | **44** | 출 7–8장, 레 5–6장, 민 29–30장, 욥 38–41장, 전 4–5·11–12장, 겔 20–21장, 호 1–2·11–12장, 욘 1–2장, 막 9–10장, 행 19장, 고후 13장 등 20권 |

총계는 31,170절로 KJV보다 68절 많다(LSG에만 있는 절 번호 114개, KJV에만 있는 절 번호 46개).

```text
            KJV                         LSG (eBible)
시 3:1      LORD, how are they …        Psaume de David. A l’occasion de sa fuite …   ← 표제
시 3:2      Many there be …             O Éternel, que mes ennemis sont nombreux!
출 8:1      And the LORD spake …        (LSG 7:26)
욘 1:17     Now the LORD had prepared … (LSG 2:1)
```

이것은 **LSG 1910이 원래 쓰는 체계**이고(히브리어 성경의 장·절 구분), eBible이 틀린 것이 아니다. 시 23편처럼 표제가 짧은 시편은 히브리어 성경에서도 1절 안에 있으므로 LSG도 KJV와 같다.

**기존 역본과의 비교.** DB에 적재된 11개 역본의 장별 최대 절 번호를 KJV와 비교했다.

| 역본 | 최대 절 번호가 KJV와 다른 장 |
| --- | --- |
| RVR1909 | 12 |
| CUVT / CUVS / KOUGO / KRV / N1904 | 4 |
| NKRV | 3 |
| JPNMEB / SBLM / WEB | 2 |
| ASV | 0 |
| **LSG (A)** | **106** |

즉 **지금 DB의 모든 역본은 사실상 KJV 절 체계**다. RVR1909의 12개 장은 장 끝 절을 다음 장으로 옮기거나(욘 1:17→2:1) 앞 절에 합친(행 19:41) 경우로 이미 기록돼 있다([RVR1909 설계 8.2](reina-valera-1909-scraping-design.md#82-kjv-대조)). A를 적재하면 **절 번호로 역본을 나란히 놓을 때 시편 62편이 한두 절씩 어긋나는 첫 역본**이 된다.

### 4.6 시편 표제는 번호가 붙은 절이다 — 버리면 안 된다

이 저장소는 시편 표제를 저장하지 않는 것이 원칙이다(KJV·NKRV·WEB·ASV). 그러나 그 원칙은 **번호 없는 표제**(eBible `div.d`, BibleGateway `h4.psalm-title`)에 대한 것이다. LSG의 표제는 `div.q` 안에서 `V1` 마커를 달고 있는 **정식 1절**이다.

```html
<div class='q'> <span class="verse" id="V1">1&#160;</span>Psaume de David. A l’occasion de sa … fuite devant Absalom, son fils.</div>
```

버리면 그 장은 2절부터 시작하고, CLI의 "첫 절이 1이 아니면 건너뛴다" 방어에 걸려 **시편 62편이 통째로 빠진다.** 현재 파서가 이미 1절로 남긴다(추가 코드 없음).

### 4.7 문자

| 항목 | LSG (A) 전권 |
| --- | --- |
| 아포스트로피 | **U+2019(’) 22,546절**, ASCII `'` 0 |
| 대문자 악센트 `É` 등 | 9,804자 / 7,739절(`Éternel` 6,973회). `À`는 `A`로 쓴다(74회) |
| 괄호 `( )` / 대괄호 `[ ]` | 36쌍 / 2절 — 삼상 6:19 `[cinquante mille]`, 행 28:29 전체. 인쇄본의 괄호이므로 유지 |
| 숫자 · mojibake · NFC 아님 · NBSP · 이중 공백 | 모두 0 |

eBible은 `Content-Type`에 charset을 보내지 않지만 `_request_html()`의 `apparent_encoding` 재해석으로 이미 처리된다(RVR1909 때 도입). mojibake 0이 그 확인이다.

U+2019는 **정규화하지 않는다.** 검색에서 `l'Éternel`(ASCII)과 `l’Éternel`이 갈리는 문제는 있지만, 이것은 원문 문자이고 NFC도 바꾸지 않는 문자다. 서비스 쪽 검색 정규화의 몫이다.

### 4.8 판본 지표

| 절 | LSG (A) | 비고 |
| --- | --- | --- |
| 마 17:21 · 18:11 · 23:14 | 있음 | |
| 막 7:16 · 16:9–20 | 있음 | |
| 막 9:44 · 9:46 | **번호는 있으나 반복구가 없음** | `où leur ver ne meurt point`는 9:48에만 있다. 9:43·45를 둘로 나눠 번호를 채웠다 |
| 요 5:4 · 7:53–8:11 | 있음 | |
| 행 8:37 · 15:34 · 24:7 | 있음 | |
| 행 28:29 | **`[ ]` 안에 있음** | |
| 요일 5:7 | `Car il y en a trois qui rendent témoignage:` | **삼위 증언 구절 없음** |

LSG 1910은 수용본문 독법 대부분을 싣되 요일 5:7–8의 삼위 증언 구절과 막 9:44·46의 반복구는 싣지 않는 **혼합형**이다. Ostervald(1996)와 Martin은 요일 5:7에 `le Père, la Parole, et le Saint-Esprit`를 싣는다.

### 4.9 B안 — studybible `Segond`의 DOM

N1904에서 만든 studybible 어댑터가 그대로 읽는다. 컨테이너는 `div.passage.Segond`이고, 안에는 `sup`과 `a.verse_ref`(와 버전 링크 `a.version_info`)뿐이다 — 소개문·각주·소제목이 없다. 마커의 `title`은 `Genesis 1:1 Segond` 형식이다.

studybible은 **모르는 버전 이름을 404로 돌려주지 않는다.** `/LSG/Genesis 1`과 `/Ostervald/Genesis 1`은 200으로 **다른 책의 ASV 본문**을 돌려줬다. 파서가 `div.passage`의 버전 클래스를 확인하므로 `[]`가 나와 막히지만, `version`을 잘못 적으면 조용히 다른 역본을 받는다는 뜻이므로 [5.2](#52-b안--studybible-segond)의 등록에서 `version`을 반드시 채운다.

책 이름은 `BIBLEGATEWAY_BOOK_NAMES`의 구약 39개도 모두 제 책으로 해석됐다(`Song of Solomon`은 `Song of Songs`로 표기되어 돌아온다).

### 4.10 B안 — 같은 본문의 KJV 절 체계판, 그러나 소스 결함이 있다

**절 체계는 깨끗하다.** 원 페이지 마커 31,102개, 1,189장 모두 KJV와 절 수가 같고, 본문 없는 마커·절 번호 혼입·숫자가 모두 0이다. 시편 표제는 1절 본문 앞에 붙는다(RVR1909와 같은 방식).

```text
B 시 3:1   Psaume de David. A l'occasion de sa fuite devant Absalom, son fils. O Eternel, que mes ennemis sont nombreux! …
B 출 8:1   L'Eternel dit à Moïse: Va vers Pharaon, …          ← A의 7:26
```

**본문은 A와 같은 1910년판이다.** 66권 각각을 낱말 열(악센트·대소문자·구두점 제거)로 맞대면 779,734낱말 중 차이는 290곳이고, 23권은 완전히 같다. 절 경계만 다르고 내용은 옮겨졌을 뿐이라는 뜻이다. 차이 290곳을 전수 분류했다.

| 유형 | 곳 | 어느 쪽 결함 | 예 |
| --- | --- | --- | --- |
| 낱말 경계 | 191 | **A** — 189곳은 파서(4.4), 2곳은 원문 | `eton`/`et on`, `Vat’en`/`va-t'en` |
| 절 첫머리 악센트 글자 소실 | **61** | **B** — 원 페이지에 없음 | 레 13:48 `la chaîne`(A `à la chaîne`), 왕상 8:32 `coute-le`(A `Écoute-le`) |
| 장 끝에 책 이름 | 2 | **B** | 출 11:10 `… hors de son pays. Exode`, 신 18:22 `… n'aie pas peur de lui. Deutéronome` |
| 소제목 오염 | 1 | **A** — 파서(4.3) | 창 11:9 |
| 그 밖의 낱말·철자 | 35 | 양쪽 | 아래 |

61곳 중 60곳이 절의 **첫 낱말**이다(`à` 52, `É`로 시작하는 낱말 8). B의 입력 과정이 절 첫머리의 악센트 글자를 떨어뜨린 것으로 보인다.

"그 밖의" 35곳 중 한쪽의 누락이나 오타가 분명한 것은 이렇다.

- **B의 누락·오타**: 출 11:10 `l’Éternel endurcit le cœur de Pharaon` 구절 전체, 요 16:19 `et il`, 시 138:2 `accomplissemen`, 딛 2:5 `à être`→`tre`
- **A의 누락·오타**: 사 8:9 반복구 `Préparez-vous au combat, et vous serez brisés` 한 번, 겔 21:32 `aua`(aura)

나머지(`tamaris`/`tamarisc`, `Habacuc`/`Habakuk`, `naziréens`/`nazaréens`, `fonction`/`fonctions` 등)는 어느 쪽이 인쇄본인지 확인하지 못했다.

**표기는 B가 전면적으로 잃었다.**

| 항목 | A | B |
| --- | --- | --- |
| 대문자 악센트 | 9,804자 | **0** (`Éternel` 6,973 → `Eternel` 6,969) |
| 아포스트로피 | `’` | `'` |
| 여는 괄호 `(` / 닫는 괄호 `)` | 36 / 36 | **0 / 4** — 여는 괄호만 사라져 짝이 깨졌다(요 9:7 `Siloé nom qui signifie envoyé).`) |
| 대괄호 | 2절 | 0 |
| `— Pause.` | 74 | 0 (`-Pause.` 52) |

B의 판본 설명 페이지(`/version/Segond`)는 Martin과 같이 PHP 오류만 출력해 **입력본의 출처를 알 수 없다.**

### 4.11 절 체계 결정

| | A. eBible `fraLSG` | B. studybible `Segond` |
| --- | --- | --- |
| 본문 | LSG 1910 | LSG 1910 |
| 절 체계 | **LSG 원 체계** — KJV와 106개 장이 다름 | **KJV 체계** — 1,189장 모두 KJV 절 수 |
| 시편 표제 | 긴 표제는 별도 1절 | 1절 본문 앞에 붙음(RVR1909와 같은 방식) |
| 본문 결함 | 파서 기인 190곳(**고칠 수 있음**) + 원문 오타 몇 곳 | **소스 기인 63곳 이상(고칠 수 없음)** + 원문 오타 몇 곳 |
| 표기 | `Éternel` · `’` · `( )` · `[ ]` · `— Pause.` | 대문자 악센트·여는 괄호·대괄호 없음 |
| 소스 출처 | eBible, 인증(`Certified: True`) | 출처 불명 |
| 코드 변경 | 제거 셀렉터 1줄 + 각주 마커 제거 방식 + 등록 | 신약 전용 방어를 역본별로 + 등록 |
| 요청 수 · 소요 | 1,189회 · 약 35분 | 1,189회 · 약 40분 |

**권고: A.**

1. **본문이 더 정확하다.** A의 결함은 이 저장소의 파서가 만든 것이라 고칠 수 있고, 고치고 나면 B와의 차이에서 A 쪽 결함은 원문 오타 몇 곳만 남는다. B의 결함은 소스에 있어 고칠 수 없다 — 없는 글자를 넣는 것은 소스가 준 적 없는 데이터를 만드는 일이다.
2. **A의 번호가 LSG 1910의 번호다.** A의 시 51:12는 `O Dieu! Crée en moi un cœur pur`이고, B에서는 같은 절이 51:10이다(KJV와 같은 번호). B는 판이 가진 번호를 KJV에 맞춰 다시 매긴 것이다.
3. **A의 구조 차이는 결함이 아니다.** Martin(studybible)처럼 번호가 내용과 어긋난 것이 아니라, 판이 원래 가진 체계를 그대로 옮긴 것이다. 장 수와 장 순서는 KJV와 같다.

**그러나 기준과 충돌한다.** 사용자는 그리스어 구약에서 "구조가 어긋나면 중단"을 정했고, A는 절 수준에서 106개 장이 어긋난다. 이 문서는 그 기준이 칠십인역의 **장·책 수준 불일치**(시편 번호 이동, 예레미야 재배열)를 겨냥한 것으로 읽고 A를 권고하지만, 기준을 절 수준에도 적용한다면 선택지는 둘이다.

- **B를 쓴다** — 구조는 맞고, 63곳 이상의 소스 결함과 표기 손실을 감수한다.
- **LSG도 보류한다.**

서비스가 절 번호로 역본을 나란히 놓는지가 판단 기준이다. **이 결정이 서기 전에는 적재하지 않는다.**

> **결정 (2026-09-27): A.** 사용자가 A(eBible `fraLSG`, LSG 원 절 체계)로 구현하도록 정했다. 구현과 적재 결과는 [14장](#14-구현적재-결과-실측)에 있다.

---

## 5. 코드 변경 지점

### 5.1 A안 — eBible `fraLSG`

**`scraper.py` ① 제거 셀렉터에 `div.ms2`·`div.ms3` 추가**

```python
EBIBLE_REMOVABLE_SELECTOR = (
    "ul.tnav, div.mt, div.mt1, div.mt2, div.mt3, "
    "div.ms, div.ms1, div.ms2, div.ms3, div.s, div.s1, div.s2, div.sr, div.mr, div.r, "
    ...
)
```

`div.ms3`은 관측되지 않았지만 USFM `\ms` 계열의 같은 단계 표지이고, `div.mt1~3`을 이미 같은 방식으로 나열하고 있다. **`div.q`·`div.b`·`div.m`은 넣지 않는다**(본문이다).

**`scraper.py` ② 각주 마커가 낱말 사이에 있으면 공백 하나를 남긴다**

```python
        for marker in working.select(EBIBLE_FOOTNOTE_SELECTOR):
            if marker.decomposed:  # went with an enclosing marker
                continue
            before = self._ebible_text_beside_note(marker.previous_elements)
            after = self._ebible_text_beside_note(marker.next_elements)
            marker.decompose()
            if before is not None and after is not None and before[-1].isalpha() and after[0].isalpha():
                after.replace_with(" " + after)
```

`_ebible_text_beside_note()`는 마커 **바깥**에서 가장 가까운 비지 않은 텍스트 노드를 돌려준다(자기 팝업과 이웃 마커의 팝업은 건너뛴다). 앞 노드의 마지막 글자와 뒤 노드의 첫 글자가 모두 `str.isalpha()`일 때만 뒤 노드 앞에 공백을 붙인다. 한자·가나도 `isalpha()`가 참이지만, 붙인 공백은 뒤이어 `CJK_JOIN_PATTERN`이 지운다.

> **처음 설계는 동작하지 않았다.** 이 절의 첫 판은 마커를 `replace_with(" ")`로 공백 노드로 바꾸는 것이었다. 그러나 누적 루프가 **공백만 있는 텍스트 노드를 건너뛰므로**(`if not text.strip(): continue`) 넣은 공백이 버려지고 `eton`이 그대로 남는다. 구현 전에 이것을 확인하고 뒤 텍스트 노드에 붙이는 방식으로 바꿨다. 누적 루프의 건너뛰기를 고치는 쪽은 택하지 않았다 — 모든 eBible 역본의 블록 경계 처리를 건드리기 때문이다.

**①②는 이미 적재된 eBible 역본의 결과를 바꿀 수 있는 변경이다.** 이 문서의 조사로는 영향이 0이지만(RVR1909·SBLM에 `div.ms2` 흔적 0, SBLM 표본에 해당 마커 0), 전권 확인을 [7.8](#78-기존-역본-회귀-검증)에 넣었다.

URL 빌더·장 목록·소스 판별·인코딩 처리는 **변경 없음**이다.

**`scrape_bible_to_db.py` — 역본 등록**

```python
ENTRY_URL_ENV_BY_TRANSLATION_TYPE = { ..., "LSG1910": "LSG1910_ENTRY_URL" }
TRANSLATION_TYPES_BY_LANGUAGE_CODE = { ..., "fr": ("LSG1910",) }
ENTRY_URL_PREFERENCE_ORDER = ( ..., "N1904", "LSG1910" )
TRANSLATION_SOURCE_REQUIREMENTS = {
    ...,
    "LSG1910": {
        "source": "ebible",
        "version": "fraLSG",
        "name": "Louis Segond 1910",
        "language_code": "fr",
    },
}
```

- `version`을 비우면 eBible 네 역본이 서로를 통과시킨다. `_version_matches()`가 대소문자를 무시하므로 `fraLSG`/`fralsg` 어느 쪽이든 된다.
- `name`은 [6.4](#64-bible_translation-1행)에서 넣는 값과 글자까지 같아야 한다(`_translation_type_by_identity()`).
- `resolve_book_code_for_source()`는 손대지 않는다. bskorea·biblegateway가 아닌 소스에는 `None`을 돌려주고, eBible URL은 `USFM_BOOK_CODES`에서 만들어진다.

### 5.2 B안 — studybible `Segond`

**`scraper.py` — 신약 전용 방어를 역본별로**

지금 `_build_studybible_url()`과 `_discover_chapter_urls_for_studybible()`은 `STUDYBIBLE_FIRST_NT_BOOK_ORDER = 40`을 **버전과 무관하게** 적용한다. Segond에 그대로 쓰면 구약 39권을 요청조차 하지 않는다. 방어의 이유(구약 URL이 200에 빈 상자를 돌려주는 것)는 **Nestle에만** 해당하므로 범위를 버전별로 둔다.

```python
# Nestle 1904 is New Testament only; its Old Testament URLs answer 200 with an empty
# passage box that the generic chain would read as two fake verses.
STUDYBIBLE_FIRST_BOOK_ORDER_BY_VERSION = {"Nestle": 40}

def _studybible_first_book_order(self) -> int:
    return STUDYBIBLE_FIRST_BOOK_ORDER_BY_VERSION.get(self._get_studybible_version(), 1)
```

`_build_studybible_url()`은 `self._studybible_first_book_order() <= book_order <= 66`을 검사하고, `_discover_chapter_urls_for_studybible()`도 같은 값을 쓴다. **Nestle의 동작은 바뀌지 않아야 한다** — 기존 테스트 `test_studybible_chapter_urls_cover_the_new_testament_only`(Nestle에서 `book_order` 1·39·67은 `ValueError`, 1권 장 목록은 `{}`)가 고치지 않고 통과해야 한다.

CLAUDE.md의 "`_build_studybible_url()` refuses `book_order < 40`" 문장도 "Nestle에 대해"로 고친다.

**`scrape_bible_to_db.py` — 역본 등록**

```python
    "LSG1910": {
        "source": "studybible",
        "version": "Segond",
        "name": "Louis Segond 1910",
        "language_code": "fr",
    },
```

studybible은 한 호스트에서 여러 역본을 주므로 `version`이 비면 이 호스트의 모든 역본이 `LSG1910`으로 통과한다. N1904와 같은 이유다. `Segond_Strongs`라는 별도 버전이 있으니 **정확히 `Segond`** 여야 한다.

---

## 6. DB 준비

### 6.1 현재 상태 (실측, 2026-09-27)

```
[bible_translation]        34행, 최대 translation_order = 37 (N1904)
[translation_type CHECK]   34개 값, 'LSG1910' 없음
[language_code CHECK]      ko,en,zh,ja,es,de,la,el — 'fr' 없음
[bible_book_description]   en/es/ja/ko/zh 각 66행 — fr 없음
```

### 6.2 `language_code` CHECK — `fr` 추가

```sql
ALTER TABLE public.bible_translation DROP CONSTRAINT bible_translation_language_code_check;
ALTER TABLE public.bible_translation ADD CONSTRAINT bible_translation_language_code_check
  CHECK (language_code IN ('ko', 'en', 'zh', 'ja', 'es', 'de', 'la', 'el', 'fr'));
```

기존 8개 값을 그대로 유지해야 한다. **손으로 다시 적지 말고 `pg_get_constraintdef()`에서 읽은 목록 뒤에 붙인다** — N1904 때 그렇게 했고([N1904 설계 12.5](greek-new-testament-nestle-1904-scraping-design.md#125-적재-결과-실측)), 그 사이 목록이 한 번 바뀌었다(`grc`→`el`).

### 6.3 `translation_type` CHECK — 35번째 값

```sql
ALTER TABLE public.bible_translation DROP CONSTRAINT bible_translation_translation_type_check;
ALTER TABLE public.bible_translation ADD CONSTRAINT bible_translation_translation_type_check
  CHECK (translation_type IN ( … 기존 34개 값 … , 'LSG1910'));
```

값 이름은 `LSG`가 아니라 **`LSG1910`** 으로 한다. `RVR1909`·`LUTH1545`가 이미 연도를 붙이고 있고, "Segond"라는 이름 아래 1978·1979·2002·2007년 개정판이 모두 유통되므로 연도가 판을 가른다.

### 6.4 `bible_translation` 1행

```sql
INSERT INTO public.bible_translation (translation_type, name, language_code, translation_order)
SELECT 'LSG1910', 'Louis Segond 1910', 'fr', COALESCE(MAX(translation_order), 0) + 1
FROM public.bible_translation;
```

`name`은 eBible의 제목(`Louis Segond 1910`)이고 `Reina Valera 1909` 행과 형식이 같다. `translation_order`는 **38**이 된다.

### 6.5 `bible_book` 66행

```sql
INSERT INTO public.bible_book (translation_id, book_order, book_key, abbreviation, name, testament_type)
SELECT t.id, s.book_order, s.book_key, s.abbreviation, s.name,
       CASE WHEN s.book_order <= 39 THEN 'OLD' ELSE 'NEW' END
FROM public.bible_translation t
CROSS JOIN (VALUES
  ( 1,'GEN','Gn','Genèse'), ( 2,'EXO','Ex','Exode'), ( 3,'LEV','Lv','Lévitique'),
  ( 4,'NUM','Nb','Nombres'), ( 5,'DEU','Dt','Deutéronome'), ( 6,'JOS','Jos','Josué'),
  ( 7,'JDG','Jg','Juges'), ( 8,'RUT','Rt','Ruth'), ( 9,'1SA','1 S','1 Samuel'),
  (10,'2SA','2 S','2 Samuel'), (11,'1KI','1 R','1 Rois'), (12,'2KI','2 R','2 Rois'),
  (13,'1CH','1 Ch','1 Chroniques'), (14,'2CH','2 Ch','2 Chroniques'), (15,'EZR','Esd','Esdras'),
  (16,'NEH','Né','Néhémie'), (17,'EST','Est','Esther'), (18,'JOB','Jb','Job'),
  (19,'PSA','Ps','Psaumes'), (20,'PRO','Pr','Proverbes'), (21,'ECC','Ec','Ecclésiaste'),
  (22,'SNG','Ct','Cantique'), (23,'ISA','Es','Ésaïe'), (24,'JER','Jr','Jérémie'),
  (25,'LAM','Lm','Lamentations'), (26,'EZK','Ez','Ézékiel'), (27,'DAN','Dn','Daniel'),
  (28,'HOS','Os','Osée'), (29,'JOL','Jl','Joël'), (30,'AMO','Am','Amos'),
  (31,'OBA','Ab','Abdias'), (32,'JON','Jon','Jonas'), (33,'MIC','Mi','Michée'),
  (34,'NAM','Na','Nahum'), (35,'HAB','Ha','Habacuc'), (36,'ZEP','So','Sophonie'),
  (37,'HAG','Ag','Aggée'), (38,'ZEC','Za','Zacharie'), (39,'MAL','Ml','Malachie'),
  (40,'MAT','Mt','Matthieu'), (41,'MRK','Mc','Marc'), (42,'LUK','Lc','Luc'),
  (43,'JHN','Jn','Jean'), (44,'ACT','Ac','Actes'), (45,'ROM','Rm','Romains'),
  (46,'1CO','1 Co','1 Corinthiens'), (47,'2CO','2 Co','2 Corinthiens'), (48,'GAL','Ga','Galates'),
  (49,'EPH','Ep','Éphésiens'), (50,'PHP','Ph','Philippiens'), (51,'COL','Col','Colossiens'),
  (52,'1TH','1 Th','1 Thessaloniciens'), (53,'2TH','2 Th','2 Thessaloniciens'), (54,'1TI','1 Tm','1 Timothée'),
  (55,'2TI','2 Tm','2 Timothée'), (56,'TIT','Tt','Tite'), (57,'PHM','Phm','Philémon'),
  (58,'HEB','Hé','Hébreux'), (59,'JAS','Jc','Jacques'), (60,'1PE','1 P','1 Pierre'),
  (61,'2PE','2 P','2 Pierre'), (62,'1JN','1 Jn','1 Jean'), (63,'2JN','2 Jn','2 Jean'),
  (64,'3JN','3 Jn','3 Jean'), (65,'JUD','Jude','Jude'), (66,'REV','Ap','Apocalypse')
) AS s(book_order, book_key, abbreviation, name)
WHERE t.translation_type = 'LSG1910';
```

세 열의 출처가 다르다.

- `book_key`는 KJV·RVR1909 행과 같은 USFM 대문자 코드다(DB 확인).
- `name`은 **eBible `fraLSG/index.htm`의 책 목록 66개를 그대로** 옮겼다. 소스가 쓰는 이름이다(`Ésaïe`, `Ézékiel`, `Cantique`).
- `abbreviation`은 **소스에 없다.** 프랑스어 성경에서 흔히 쓰는 축약을 채운 것이므로 서비스 표기 규칙에 맞춰 바꿔도 된다. RVR1909가 `1 S`, `1 R`처럼 공백을 넣은 형식을 따랐다. NOT NULL이라 비워 둘 수 없다.

`bible_book`에는 `(translation_id, book_key)`와 `(translation_id, book_order)` UNIQUE가 있어 두 번 실행해도 중복되지 않고 실패한다.

### 6.6 `bible_book_description` — `fr`

`en/es/ja/ko/zh` 각 66행이 있고 `fr`은 없다. **본문 적재와 독립이며 이 도구는 이 표를 읽지 않는다.** 넣지 않아도 적재는 완결된다.

---

## 7. 검증

`:tid`는 `LSG1910`의 `translation_id`다. 기대값은 A/B를 나눠 적었다.

### 7.1 구조 검증 (전 소스 공통)

```sql
-- 1절로 시작하지 않거나 절 번호에 구멍이 있는 장 (기대: 0 — A·B 모두)
SELECT b.book_order, c.chapter_number, count(*) AS n, max(v.verse_number) AS mx
FROM bible_book b JOIN bible_chapter c ON c.book_id = b.id JOIN bible_verse v ON v.chapter_id = c.id
WHERE b.translation_id = :tid
GROUP BY 1, 2
HAVING min(v.verse_number) <> 1 OR count(*) <> max(v.verse_number);
```

| 항목 | A | B |
| --- | --- | --- |
| 장 | 1,189 | 1,189 |
| 절 | **31,170** (구약 23,211 / 신약 7,959) | **31,102** |
| 구멍 · 1절 아닌 시작 · 빈 절 | 0 · 0 · 0 | 0 · 0 · 0 |

A의 총계는 eBible `translations.csv`가 밝힌 값(`OTverses 23211`, `NTverses 7959`)과 같다.

### 7.2 KJV 대조 — 고정 목록으로

KJV `translation_id`와 장별 절 수를 비교한다.

- **A: 106개 장이 달라야 정상이다.** 시편 62편(+1, 단 51·52·54·60편은 +2)과 20권 44개 장. LSG에만 있는 절 번호 114개, KJV에만 있는 절 번호 46개. 아래 목록으로 **고정**하고, 한 장이라도 늘거나 줄면 파싱 이상으로 본다.

  ```text
  시편 (62)  3 4 5 6 7 8 9 12 18 19 20 21 22 30 31 34 36 38 39 40 41 42 44 45 46 47 48 49
             51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 67 68 69 70 75 76 77 80 81 83 84
             85 88 89 92 102 108 140 142
  그 밖 (44, KJV 절 수 → LSG 절 수)
    EXO 7 25→29   EXO 8 32→28   LEV 5 19→26   LEV 6 30→23   NUM 29 40→39  NUM 30 16→17
    1SA 20 42→43  1SA 23 29→28  1SA 24 22→23  1KI 22 53→54  2CH 13 22→23  2CH 14 15→14
    JOB 34 37→36  JOB 38 41→38  JOB 39 30→38  JOB 40 24→28  JOB 41 34→25
    ECC 4 16→17   ECC 5 20→19   ECC 11 10→8   ECC 12 14→16  SNG 6 13→12   SNG 7 13→14
    ISA 8 22→23   ISA 9 21→20   ISA 64 12→11  EZK 20 49→44  EZK 21 32→37
    HOS 1 11→9    HOS 2 23→25   HOS 11 12→11  HOS 12 14→15  JON 1 17→16   JON 2 10→11
    MIC 4 13→14   MIC 5 15→14   NAM 1 15→14   NAM 2 13→14   MRK 9 50→51   MRK 10 52→53
    ACT 19 41→40  2CO 13 14→13  3JN 1 14→15   REV 12 17→18
  ```
- **B: 0개 장이 달라야 정상이다.** 원 페이지의 마커부터 1,189장 모두 KJV와 같은 개수다.

### 7.3 오염 검증 — 이 소스 필수

절 수 검사로는 **절대 안 잡힌다.**

```sql
-- 대문자 12자 이상 연속 (소제목 흔적). 기대: 0
SELECT c.chapter_number, v.verse_number, v.text FROM bible_verse v
JOIN bible_chapter c ON c.id = v.chapter_id JOIN bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid AND v.text ~ '[A-ZÀ-Ý’'' ]{12,}';

-- 숫자 (상호참조 `2 S 15:16`·소개문 `(28:69–30:20)`·절 번호 혼입). 기대: 0
SELECT count(*) FROM bible_verse v JOIN bible_chapter c ON c.id = v.chapter_id
JOIN bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid AND v.text ~ '[0-9]';
```

**셀렉터 수정 전에 첫 번째 질의를 돌리면 창 11:9 한 건이 나와야 한다.** 수정 후 0이 되는 것까지 확인한다.

붙은 낱말(4.4)은 일반 질의로 잡을 수 없다. 아래 절을 눈으로 확인하고, 전체는 [7.6](#76-제2-증인-대조)의 B 대조로 확인한다.

| 절 | 수정 전 | 수정 후 |
| --- | --- | --- |
| 마 5:15 | `… eton n’allume pas …` | `… et on n’allume pas …` |
| 스 5:12 | `Maisaprès que nos pères …` | `Mais après que nos pères …` |

### 7.4 문자 검증

| 항목 | A 기대값 | B 기대값 |
| --- | --- | --- |
| mojibake(`Ã`, `â€`) · NFC 아님 · NBSP | 0 · 0 · 0 | 0 · 0 · 0 |
| U+2019 `’` 포함 절 | 22,546 | 0 (ASCII `'` 22,538절) |
| `Éternel` | 6,973 | 0 |
| `Eternel` (악센트 없음) | 0 | 6,969 |

### 7.5 판본 지표

```sql
SELECT
  count(*) FILTER (WHERE v.text ILIKE '%sacrificateur%') AS sacrificateur,
  count(*) FILTER (WHERE v.text ILIKE '%prêtre%')        AS pretre
FROM bible_verse v JOIN bible_chapter c ON c.id = v.chapter_id JOIN bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid;
```

이 질의는 **절 수**를 센다(한 절에 두 번 나오면 1). [1.3](#13-온라인에-실제로-있는-판본)의 846/46은 **출현 횟수**이므로, 절 수 기대값은 적재 후 처음 확정해 기록한다. 판본 판별에 필요한 것은 비율과 `prêtre`의 문맥(전부 이방 제사장)이다. → 적재 결과 **766절 / 40절**([14.6](#146-적재와-검증)). 이후 재적재나 drift 점검에서는 이 값이 기대값이다.

눈으로 확인할 절:

- 요일 5:7 — 삼위 증언 구절이 **없어야** 한다(`Car il y en a trois qui rendent témoignage:`)
- 행 28:29 — A는 `[ ]` 안에 있어야 한다(B는 괄호 없음)
- 삼상 6:19 — A는 `[cinquante mille]`
- 시 3:1 — A는 `Psaume de David. A l’occasion de sa fuite devant Absalom, son fils.`만, B는 표제 뒤에 `O Eternel, que mes ennemis sont nombreux!`가 이어져야 한다

### 7.6 제2 증인 대조

A와 B는 서로의 증인이다. 적재한 쪽을 다른 쪽 전권과 [4.10](#410-b안--같은-본문의-kjv-절-체계판-그러나-소스-결함이-있다)의 방식(책 단위 낱말 열, 악센트·대소문자·구두점 제거)으로 맞대 **차이 목록이 이 문서의 분류와 같은지** 본다.

- A를 적재했다면 파서 수정 뒤 **낱말 경계 차이 189곳과 소제목 1곳이 사라지고** 약 100곳(B의 결함 63곳 이상 + 양쪽 철자 차이 + 원문 하이픈 2곳)만 남아야 한다.
- 차이가 새로 늘었다면 한쪽 소스가 바뀐 것이다.

### 7.7 잘못 적재 방지 검증

적재 전에 아래 두 실행이 **실패하는지** 먼저 본다. `<LSG1910 id>`는 [6.4](#64-bible_translation-1행)에서 생긴 `translation_id`다.

```bash
BIBLE_TRANSLATION_ID=33 python scrape_bible_to_db.py --entry-url https://ebible.org/fraLSG/GEN01.htm --start-book 1 --end-book 1
```

```bash
BIBLE_TRANSLATION_ID=<LSG1910 id> python scrape_bible_to_db.py --entry-url https://ebible.org/spaRV1909/GEN01.htm --start-book 1 --end-book 1
```

첫째는 LSG 본문을 RVR1909(33) 책에, 둘째는 RVR1909 본문을 LSG 책에 넣으려는 실행이다. 둘 다 `Source/translation mismatch`로 거부돼야 한다. **`BIBLE_TRANSLATION_TYPE`만으로 시험하면 안 된다** — `.env`가 `BIBLE_TRANSLATION_ID=2`를 고정하고 있으면 ID가 먼저 적용되어 NKRV를 상대로 실패하므로, 거부는 되지만 확인하려던 경로를 타지 않는다. B안이면 `https://studybible.info/Segond/Genesis%201`을 `N1904`로, `https://studybible.info/Nestle/Matthew%201`을 `LSG1910`으로 넣는 두 실행을 같은 방식으로 확인한다.

### 7.8 기존 역본 회귀 검증

A안의 파서 수정 ①②는 eBible 파서 공용 코드다. 이미 적재된 세 역본이 **한 글자도 바뀌지 않는지** 읽기 전용 drift 검사로 확인한다.

```bash
python scripts/check_translation_drift.py --translation-id 35 --entry-url https://ebible.org/spablm/GEN01.htm
```

SBLM(35)은 각주가 있는 역본이라 ②의 영향을 받을 수 있는 유일한 기존 역본이다 — **전권**을 돌린다. RVR1909(33, 각주 없음)와 JPNMEB(36, CJK)는 각각 몇 권으로 충분하다. 기대값은 셋 모두 **차이 0**이다(실측은 SBLM 2절 — [14.3](#143-기존-역본-회귀)). drift 검사는 소스의 현재 본문과 비교하므로, 소스가 그 사이 바뀌었다면 파서 변경과 무관한 차이가 섞인다 — 수정 **전** 파서로 한 번, **후**로 한 번 돌려 차이가 같은지 보면 가를 수 있다.

---

## 8. 테스트 설계

네트워크 없이 인라인 HTML로 쓴다.

**A안**

| 테스트 | 확인하는 것 |
| --- | --- |
| `test_ebible_drops_a_second_level_major_heading` | 절 사이 `div.ms2`가 앞 절에 붙지 않는다. **셀렉터를 되돌리면 실패해야 한다** |
| `test_ebible_keeps_a_space_where_a_note_marker_split_two_words` | `<span class='wj'>et</span><a class='notemark'>j<span class='popup'>…</span></a><span class='wj'>on</span>` → `et on`. **수정을 되돌리면 `eton`으로 실패해야 한다** |
| `test_ebible_adds_no_space_before_punctuation_after_a_note_marker` | `mot<a class='notemark'>…</a>.` → `mot.` (공백 없음) |
| `test_ebible_keeps_a_numbered_psalm_title` | `div.q` 안 `V1` 마커 뒤의 표제가 1절로 남는다(`div.d` 표제와 구별) |
| `test_ebible_ignores_a_book_introduction` | 첫 마커 앞의 `div.ip`·`div.io`·`table`이 1절에 들어가지 않는다 |
| `test_ebible_keeps_selah_line` | `div.qs`의 `— Pause.`가 해당 절 끝에 남는다 |
| 파이프라인: `LSG1910` 등록 | `fraLSG`→`LSG1910` 통과, `fraLSG`→`RVR1909` 거부, `spaRV1909`→`LSG1910` 거부, `BIBLE_LANGUAGE_CODE=fr` 해석 |

기존 CJK 테스트(`CJK_JOIN_PATTERN` 양방향)가 ② 이후에도 통과해야 한다.

**B안**

| 테스트 | 확인하는 것 |
| --- | --- |
| `test_studybible_segond_covers_both_testaments` | `Segond`에서 1권 장 목록이 50개, `(1, 1)` URL이 `/Segond/Genesis%201`, 67은 `ValueError` |
| 기존 `test_studybible_chapter_urls_cover_the_new_testament_only` | **수정 없이** 통과(Nestle 동작 불변) |
| `test_studybible_parser_rejects_another_versions_box` | 기대 버전이 `Segond`인데 `div.passage.ASV`가 오면 `[]` (4.9의 대체 응답) |
| 파이프라인: `LSG1910` 등록 | `Segond`→`LSG1910` 통과, `Segond_Strongs`·`Nestle`→`LSG1910` 거부 |

`tests/test_pipeline.py`의 `FakeScraper`는 새 메서드를 쓰게 되면 함께 빌려 와야 한다. N1904 때 이것을 빠뜨려 13개 테스트가 깨졌다([N1904 설계 12.5](greek-new-testament-nestle-1904-scraping-design.md#125-적재-결과-실측)).

---

## 9. 운영 계획

### 9.1 요청 간격과 소요

| 사이트 | `robots.txt` | 이 문서의 사용 |
| --- | --- | --- |
| `ebible.org` | `Baiduspider`의 한 경로만 막음. `Crawl-delay` 없음 | A 소스. 기존 하한 `EBIBLE_MIN_DELAY_SECONDS = 1.0` |
| `studybible.info` | `Baiduspider`·`Amazonbot`·`Sogou`에만 `Crawl-delay: 30` | B 소스. 기존 하한 `STUDYBIBLE_MIN_DELAY_SECONDS = 1.0` |
| `gratis.bible` | 콘텐츠 신호 선언문만 있고 값이 없음(허용도 제한도 아님) | 표본 조회만 |
| `levigilant.com` | 404 | 표본 조회만 |
| `lueur.org` | **AI 크롤러 차단** | 제외 |

전권 요청 수는 A·B 모두 1,189회다. 이 문서의 수집에서 장당 eBible 약 1.6초, studybible 약 1.8초가 걸렸으므로, 책 사이 5초 대기(66권, 약 5.5분)를 합쳐 A는 약 35분, B는 약 40분으로 본다.

### 9.2 실행 예

`.env`가 `BIBLE_TRANSLATION_ID=2`로 고정돼 있으면 셸 환경변수로 덮어야 한다(`.env`는 `setdefault()`로 읽히고, 역본 해석은 ID가 `BIBLE_TRANSLATION_TYPE`보다 먼저다).

```bash
python scrape_bible_to_db.py --entry-url https://ebible.org/fraLSG/GEN01.htm --test-book 1 --test-chapter 11
```

```bash
python scrape_bible_to_db.py --entry-url https://ebible.org/fraLSG/GEN01.htm --test-book 40 --test-chapter 5
```

```bash
python scrape_bible_to_db.py --entry-url https://ebible.org/fraLSG/GEN01.htm --test-book 19 --test-chapter 3
```

위 셋은 DB에 접속하지 않는다. 창 11:9에 소제목이 없는지, 마 5:15가 `et on`인지, 시 3:1이 표제인지 본다. 이상이 없으면 창세기만 적재해 [7장](#7-검증)을 돌리고 전권으로 간다. N1904 때와 같이 **ID와 엔트리 URL을 셸에서 함께** 준다([N1904 설계 12.5](greek-new-testament-nestle-1904-scraping-design.md#125-적재-결과-실측)).

```bash
BIBLE_TRANSLATION_ID=<LSG1910 id> python scrape_bible_to_db.py --entry-url https://ebible.org/fraLSG/GEN01.htm --start-book 1 --end-book 1
```

### 9.3 갱신 문제

eBible `fraLSG`의 `UpdateDate`는 2026-08-08이다. eBible은 원본 파일을 주기적으로 다시 생성하므로 **본문이 바뀔 수 있다.** 적재 후 바뀌면 missing-only 삽입으로는 고쳐지지 않으므로 `scripts/check_translation_drift.py`로 감지하고, 절→장 순으로 지운 뒤 다시 적재한다(CLAUDE.md). studybible도 같다.

---

## 10. 대안 경로 — 보류한 두 역본

### 10.1 Ostervald — 보류

**판과 권리.** eBible `fra_fob`는 1996년 개정판이고 개정분의 권리 근거가 없다([1.3](#13-온라인에-실제로-있는-판본)).

**구조.** 깨끗한 편이다. DOM은 `div.p` 하나에 마커뿐이고(각주·소제목·소개문 없음), 1,189장 31,107절, KJV와 절 수가 다른 장은 9개(시 30·51·52·54·60·66편, 고후 13장, 요삼, 계 12장)다.

**본문 결함 셋.** 권리가 해결돼도 그대로 적재할 수 없다.

| 결함 | 범위 | 예 |
| --- | --- | --- |
| 깨진 태그가 본문 문자열로 남음 | 왕하 14–24장, **각 장 마지막 절 11곳** | 왕하 14:29 `… régna à sa place.‘br wp="br1"’` |
| `œ` 탈락으로 다른 낱말이 됨 | **최소 20곳** — 마태 8, 사도행전 11(`cœur`→`cour`), 행 21:23(`vœu`→`vou`) | 마 6:21 `là sera aussi votre cour.` |
| 시편 표제가 잘림 | 편마다 다름 | 시 3편 표제 없음 · 시 51:1은 표제 뒷부분(`Lorsque Nathan …`)만 · 시 18:1은 표제 끝의 `Il dit donc:`만 |

첫째는 규칙으로 지울 수 있지만, **둘째는 고칠 수 없다** — `cour`(뜰)는 실제 낱말이라 같은 본문에 정상 용례가 30곳 넘게 있고(에 1:5 `la cour du jardin` 등) 문맥 없이 가를 수 없다. 셋째는 원 페이지에 표제 앞부분이 아예 없다.

**재개하려면** 다음 중 하나가 먼저다.

1. 1996년 개정판의 권리 상태를 확인한다. 확인돼도 둘째·셋째 결함 때문에 eBible 텍스트는 권하지 않는다.
2. 1877년판(`gratis.bible/fr/bo1877/`)으로 간다. 새 어댑터가 필요하고, 권리 표기가 없는 입력본이며, 원 입력처(`levigilant.com`)가 독점을 표기한다. 전권 실측과 제2 증인이 필요하다.

### 10.2 Martin — 보류

**studybible `Martin`의 실측.** 원 페이지의 마커는 1,189장 **31,102개로 KJV와 똑같다** — 원본의 절 체계가 아니라 KJV의 틀이다. 그런데 원본(호프만 입력본)은 LSG처럼 **히브리어 성경의 장·절 구분**을 쓴다(시 3:1이 표제, 민 12:16이 13:1 등). 다른 체계의 본문을 KJV 틀에 끼우면서 생긴 결과다. LSG의 B는 내용에 맞춰 번호를 다시 매겼지만, 이것은 **번호만 맞추고 내용은 그대로 두었다.**

| 결함 | 범위 | 예 |
| --- | --- | --- |
| **절 수는 맞는데 내용이 밀림** | **64개 장**(시편 53편, 민 13·30장, 삼상 24장, 욥 39–41장, 전 12장, 사 9장, 겔 21장, 호 12장, 욘 2장) | 민 13:1이 KJV 12:16의 내용(`Après cela le peuple partit de Hatséroth`) |
| 끝 절 병합 | 표제가 따로 절인 시편 | 시 3:8 = 원본 3:8+3:9, 시 51:19 = 원본 19–21절 |
| **본문 없는 마커** | **45개**(장 중간 29, 장 끝 16) | 출 37:24, 욥 41:26–34 |
| 절 번호가 본문에 남음 | 13곳 | 신 28:1 `… de la terre.2 Et toutes ces bénédictions` |
| 숫자가 글자 자리에 | 33곳 | `0r`(20), `0n`(5), `I1`(`Il`)·`peup1e`·`voic1`·`1'Eternel` 등(8) |

내용 밀림·본문 없는 마커·절 번호 잔존이 있는 장을 중복 없이 합치면 **92개 장(7.7%)** 이다. 절 수 검사로 잡히는 것은 그중 30개 장뿐이다. 민 13장처럼 절 수가 KJV와 같은데 번호가 가리키는 내용이 다른 장은, 같은 제네바 계통인 Ostervald와 절별 낱말 겹침을 비교해서야 드러났다(1,180장 비교: 29,227절은 같은 번호와, 857절은 한 절 앞 번호와, 72절은 한 절 뒤 번호와 가장 많이 겹쳤다).

**원 체계의 Martin을 구해도 결정이 남는다.** 원본이 히브리어 절 체계이므로 LSG A와 같은 이유로 KJV와 어긋난다. [4.11](#411-절-체계-결정)의 결정을 Martin에도 똑같이 적용해야 하고, 그 전에 원 체계를 그대로 싣고 크롤링을 허용하는 소스를 찾아야 한다. 조사한 범위에서는 찾지 못했다(lueur.org는 AI 크롤러 차단, `levigilant.com`의 Martin은 지금 접속되지 않는 `biblemartin.com`에서 가져왔다고 밝히며, 실측하지 않았다).

studybible 텍스트는 그 외에도 표기가 고르지 않다 — `cœur` 103 / `coeur` 866, `Éternel` 10 / `Eternel` 6,884. 수용본문 독법(요일 5:7 삼위 증언 구절, 행 8:37 등)은 모두 있다.

---

## 11. 구현 순서

**0. 결정** — [4.11](#411-절-체계-결정)의 A/B/보류를 정한다. 결정 전에는 DB를 건드리지 않는다.

**A안(권고)**

1. `EBIBLE_REMOVABLE_SELECTOR`에 `div.ms2, div.ms3` 추가.
2. 각주 마커 제거를 [5.1](#51-a안--ebible-fralsg)의 ②로 바꾼다.
3. [8장](#8-테스트-설계)의 A안 테스트를 쓰고 `pytest -q` 전부 통과. 두 수정 테스트는 **수정을 되돌리면 실패하는지** 확인한다.
4. [7.8](#78-기존-역본-회귀-검증) — SBLM 전권 drift 차이 0, RVR1909·JPNMEB 표본 차이 0.
5. `LSG1910` 등록(`source="ebible"`, `version="fraLSG"`).
6. [9.2](#92-실행-예)의 DB 없는 확인 세 건.
7. DB 준비: CHECK 둘 → `bible_translation` 1행 → `bible_book` 66행([6장](#6-db-준비)).
8. [7.7](#77-잘못-적재-방지-검증)이 실패하는지 먼저 본다.
9. 창세기만 적재 → [7장](#7-검증) → 전권 → [7.6](#76-제2-증인-대조) B 대조.
10. CLAUDE.md(소스 표, eBible 파서 계약에 `div.ms2`와 각주 마커 공백 규칙, LSG 절 체계), README 갱신.

**B안**

1. `STUDYBIBLE_FIRST_BOOK_ORDER_BY_VERSION`과 `_studybible_first_book_order()`를 넣고 `_build_studybible_url()`·`_discover_chapter_urls_for_studybible()`이 쓰게 한다.
2. [8장](#8-테스트-설계)의 B안 테스트. **기존 N1904 테스트를 고치지 않고** 통과하는지가 핵심이다.
3. `LSG1910` 등록(`source="studybible"`, `version="Segond"`).
4. 이후 A안 6~10과 같다. [7.2](#72-kjv-대조--고정-목록으로)의 기대값은 0개 장이고, CLAUDE.md의 studybible 계약을 "Nestle에 대해 `book_order < 40` 거부"로 고친다.

---

## 12. 리스크

### 리스크 1. 절 체계 결정 없이 적재 (가장 큼)

A는 적재 자체가 성공하고 모든 자동 검사를 통과한다. 문제는 서비스가 `(책, 장, 절)`로 역본을 나란히 놓을 때 드러난다 — 시편 62편과 44개 장에서 KJV·한국어 역본과 한두 절씩 어긋난다. 이 저장소에는 절 체계 대응표가 없다. 반대로 B를 택하면 고칠 수 없는 본문 결함을 들여온다. 어느 쪽이든 [4.11](#411-절-체계-결정)의 결정이 먼저다.

### 리스크 2. `div.ms2` 수정 없이 A를 적재

창 11:9 한 절이 오염된 채 들어가고 [7.3](#73-오염-검증--이-소스-필수)의 대문자 질의 말고는 어떤 검사에도 걸리지 않는다.

### 리스크 3. 각주 마커 수정 없이 A를 적재

189곳의 낱말이 붙은 채 들어간다. 어떤 SQL 검사로도 일반적으로 잡을 수 없고, B와의 전권 대조로만 드러난다. 복음서의 예수 말씀 경계에 몰려 있어 가장 많이 읽히는 곳이다.

### 리스크 4. 각주 마커 수정이 기존 역본을 바꾼다

②는 공용 eBible 파서의 변경이다. 조건(양쪽이 모두 문자)을 빼고 항상 공백을 넣으면 `mot .`처럼 구두점 앞에 공백이 생기고, SBLM drift 검사가 대량 차이를 낸다. [7.8](#78-기존-역본-회귀-검증)이 방어다.

### 리스크 5. B의 신약 방어를 풀다가 Nestle 방어까지 푼다

범위를 전역 상수에서 버전별로 옮기는 과정에서 Nestle의 구약 거부가 사라지면, N1904 재적재나 drift 검사에서 구약 빈 페이지가 가짜 절 두 개(`John 1:1`, `Peter 3:5`)로 들어갈 수 있다([N1904 설계 6.5](greek-new-testament-nestle-1904-scraping-design.md#65-bible_book-27행--66행이-아닌-이유)). 기존 테스트를 고치지 않고 통과시키는 것이 방어다.

### 리스크 6. studybible `version` 오기

모르는 버전 이름은 404가 아니라 **다른 역본의 200 응답**이다([4.9](#49-b안--studybible-segond의-dom)). 파서의 버전 클래스 확인과 `TRANSLATION_SOURCE_REQUIREMENTS`의 `version`이 두 겹 방어다.

### 리스크 7. B의 결함을 "복원"하려는 시도

`Eternel`을 `Éternel`로, 절 첫머리에 `à`를 되돌리는 규칙을 넣고 싶어질 수 있다. 소스가 그렇게 주므로 하지 않는다 — 소스가 준 적 없는 데이터를 만들고, 파서 실패와 판본 차이를 구별할 수 없게 한다(N1904의 구멍을 채우지 않은 것과 같은 이유).

### 리스크 8. Ostervald·Martin을 "PD라서" 적재

권리 표기만 보고 eBible `fra_fob`나 studybible `Martin`을 넣으면, 요청한 판이 아닌 1996년 개정판이 들어가거나 92개 장의 절 번호가 내용과 어긋난 채 들어간다. 보류 사유는 [10장](#10-대안-경로--보류한-두-역본)에 있다.

---

## 13. 결론

세 역본의 **권리는 옛 판 기준으로 모두 깨끗하다.** 그러나 온라인에서 실제로 구할 수 있는 텍스트를 전권 수집해 보면 결론이 셋으로 갈린다.

- **LSG 1910**은 적재할 수 있다. eBible(A, 원 절 체계)과 studybible(B, KJV 절 체계)이 같은 1910년 본문을 준다. 두 소스를 전권 낱말 대조한 결과 **A는 파서가 만든 결함 190곳만 고치면 되고 B는 소스 결함 63곳 이상을 고칠 수 없으므로 A를 권고**한다. 다만 A는 절 체계가 KJV와 106개 장에서 달라 "구조가 어긋나면 중단" 기준과 충돌한다 — **적재 전에 이 결정이 필요하다.**
- **Ostervald**는 보류한다. 손쉬운 소스(eBible)는 1744년판이 아니라 권리 근거 없는 1996년 개정판이고, 고칠 수 없는 본문 결함(`cœur`→`cour`)이 있다.
- **Martin**은 보류한다. 기존 어댑터로 읽히는 유일한 소스는 다른 절 체계의 본문을 KJV 틀에 번호만 맞춰 끼워 92개 장이 어긋나 있고, 원 체계의 Martin을 구해도 LSG와 같은 결정이 남는다.

재개하려면 LSG는 [4.11](#411-절-체계-결정)에서 A/B/보류를 정하고, Ostervald와 Martin은 [10장](#10-대안-경로--보류한-두-역본)의 선행 조건 중 하나를 먼저 해결해야 한다.

> **이후 (2026-09-27).** LSG는 A로 결정되어 구현·적재했다([14장](#14-구현적재-결과-실측)). Ostervald와 Martin은 그대로 보류다.

---

## 14. 구현·적재 결과 (실측)

[11장](#11-구현-순서)의 A안 순서대로 구현하고 적재한 결과다(2026-09-27).

### 14.1 구현

| 파일 | 변경 |
| --- | --- |
| `scraper.py` | `EBIBLE_REMOVABLE_SELECTOR`에 `div.ms2, div.ms3`. 각주 마커 제거를 [5.1](#51-a안--ebible-fralsg) ②로(`_ebible_text_beside_note()` 추가). `DEFAULT_EBIBLE_LSG1910_ENTRY_URL` |
| `scrape_bible_to_db.py` | `LSG1910` 등록 — `ENTRY_URL_ENV_BY_TRANSLATION_TYPE`, `"fr": ("LSG1910",)`, 선호 순서 끝, `TRANSLATION_SOURCE_REQUIREMENTS`(`ebible` / `fraLSG` / `Louis Segond 1910` / `fr`) |
| `tests/test_scraper.py` | [8장](#8-테스트-설계) A안 파서 테스트 6개 |
| `tests/test_pipeline.py` | 등록 테스트 4개 — `fraLSG`→`LSG1910` 통과, eBible 네 역본 상호 거부 6쌍, `translation_type`이 빈 행의 이름 식별, `BIBLE_LANGUAGE_CODE=fr` 해석 |

`pytest -q` **165개 통과**(기존 155 + 10). 두 수정은 되돌렸을 때 해당 테스트가 실패하는지 확인했다.

| 되돌린 것 | 실패한 테스트 |
| --- | --- |
| `div.ms2` 제거 | `test_ebible_drops_a_second_level_major_heading` |
| 마커 공백 | `test_ebible_keeps_a_space_where_a_note_marker_split_two_words` |
| 조건 없이 항상 공백 | `test_ebible_adds_no_space_where_a_note_marker_touches_punctuation` ([리스크 4](#리스크-4-각주-마커-수정이-기존-역본을-바꾼다)) |

### 14.2 파서 수정의 효과 — 수집해 둔 1,189장 재파싱

조사 때 받아 둔 fraLSG 1,189장을 네트워크 없이 수정 전·후 파서로 각각 파싱해 비교했다.

- 바뀐 절 **175개**. 그중 174절은 공백 추가뿐이고 합계 **189개** — 책별로 마 62, 요 44, 눅 40, 계 25, 막 14, 스 3, 행 1로 [4.4](#44-함정-2-각주-마커가-유일한-낱말-경계인-곳이-189곳)의 조사와 같다.
- 나머지 1절은 창 11:9의 소제목 제거다.
- 그 밖의 절은 한 글자도 바뀌지 않았다. 구두점 앞 공백 증가 0, 이중 공백 0, 숫자 0, 대문자 12자 연속 0.

B(studybible `Segond`)와의 낱말 대조([7.6](#76-제2-증인-대조))를 다시 돌리면 차이가 **290곳 → 100곳**이다. 낱말 경계 차이는 191곳에서 원문 하이픈 2곳(창 12:1, 50:10)만 남았고 소제목 오염은 사라졌다. 남은 100곳은 B의 결함(`à` 53 + 악센트 대문자 8 + 책 이름 2)과 그 밖의 낱말·철자 차이 35곳([4.10](#410-b안--같은-본문의-kjv-절-체계판-그러나-소스-결함이-있다))으로, [7.6](#76-제2-증인-대조)의 예측("약 100곳")과 같다.

### 14.3 기존 역본 회귀

[7.8](#78-기존-역본-회귀-검증)의 확인이다. eBible 페이지를 한 번씩 받아, 수정 전 파서(HEAD)와 수정 후 파서로 각각 파싱해 비교하고(파서 변경의 효과), 수정 후 결과를 DB와 비교했다(drift, `check_translation_drift.py`와 같은 비교). DB는 읽기만 했다.

| 역본 | 범위 | 파서 변경으로 바뀐 절 | DB와 다른 절 |
| --- | --- | --- | --- |
| SBLM (35) | **전권** 1,189장 31,103절 | **1** | 2 |
| RVR1909 (33) | 창·출·마·요·계 161장 5,100절 | 0 | 0 |
| JPNMEB (36) | 같은 5권 161장 5,100절 | 0 | 0 |

**기대값은 "차이 0"이었지만 SBLM에서 둘이 나왔다. 둘 다 이번 적재를 막는 문제는 아니다.**

- **눅 4:18 — 파서 수정이 기존 결함을 고친 것이다.** SBLM 원문에도 LSG와 같은 모양이 한 곳 있었다.

  ```html
  <span class='wj'>Me ha enviado a sanar a los corazones</span><a class="notemark">*<span class="popup">NU omite …</span></a><span class='wj'>rotos, </span>
  ```

  DB에는 `… a los corazonesrotos, …`로 붙은 채 들어 있고 새 파서는 `corazones rotos`를 만든다. 20장 표본([3.1](#31-확인하지-못한-것) 5)에서는 보이지 않던 곳이다.
- **롬 16:25 — 원문 변경이다.** 수정 전 파서도 같은 결과를 내므로 파서와 무관하다. DB에는 24절까지만 있다. 지금 원문은 그 뒤에 25절 마커를 두고 각주만 달아 `(omitted)`로 파싱된다(26·27절은 원문에도 없다). SBLM은 개정 중인 초안이다.

두 절 모두 missing-only 삽입으로는 바뀌지 않는다. **사용자 승인을 받아 LSG 적재가 끝난 뒤 고쳤다.**

1. 눅 4:18 행 하나를 지웠다(행이 정확히 하나이고 본문에 `corazonesrotos`가 있을 때만 지우도록 확인).
2. `BIBLE_TRANSLATION_ID=35`로 눅 4장과 롬 16장을 다시 적재했다. 두 장 모두 `inserted=1`로, 해당 절 하나씩만 들어갔다.
3. `check_translation_drift.py`로 눅·롬 전권을 다시 대조했다. 결과는 [14.6](#146-적재와-검증)에 있다.

LSG 적재가 끝나기를 기다린 이유는 [14.7](#147-구현하며-드러난-것)에 있다(두 적재기를 동시에 돌리면 시퀀스가 되감긴다).

### 14.4 DB 준비

[6장](#6-db-준비)의 SQL을 한 트랜잭션으로 묶은 스크립트로 적용했다. CHECK 목록은 `pg_get_constraintdef()`에서 읽어 뒤에 붙였고, 읽은 값이 [6.1](#61-현재-상태-실측-2026-09-27)의 기록(언어 8개, 역본 종류 34개)과 다르면 멈추도록 했다. 드라이런(롤백) 뒤 커밋했다.

```
language_code CHECK     ko,en,zh,ja,es,de,la,el → … ,fr
translation_type CHECK  34개 → 35개 (… ,CUVS,N1904,LSG1910)
bible_translation       id=43  LSG1910  Louis Segond 1910  fr  translation_order=38
bible_book              66행 (OLD 39 / NEW 27), book_key가 RVR1909와 66권 모두 같음
```

`translation_id`는 42가 아니라 **43**이다. N1904 때와 같이 드라이런이 identity 시퀀스 값 하나를 썼다.

### 14.5 잘못 적재 방지

[7.7](#77-잘못-적재-방지-검증)의 확인이다.

| 실행 | 결과 |
| --- | --- |
| `BIBLE_TRANSLATION_ID=33` + `fraLSG` | `Source/translation mismatch: ebible source (version=fraLSG) requires translation_type='LSG1910'` |
| `BIBLE_TRANSLATION_ID=43` + `spaRV1909` | `Source/translation mismatch: ebible source (version=spaRV1909) requires translation_type='RVR1909'` |
| ID 없이 `BIBLE_TRANSLATION_TYPE=LSG1910`, `BIBLE_LANGUAGE_CODE=fr` | id 43으로 해석, 엔트리 URL은 `LSG1910_ENTRY_URL` |

두 거부 모두 소스 요청 **전**에 일어난다.

### 14.6 적재와 검증

[9.2](#92-실행-예)의 DB 없는 확인 세 건(창 11장 32절, 마 5장 48절, 시 3편 9절)을 거쳐 창세기만 적재해 [7장](#7-검증)을 돌리고, 이상이 없어 2~66권을 적재했다. 경고·오류 0건, 재시도 0건. 창세기 약 2분, 2~66권 약 43분(회귀 검사 수집과 동시에 돌았다).

```
translation_id=43  LSG1910  Louis Segond 1910  fr  translation_order=38
66권 / 1,189장 / 31,170절 (구약 23,211 / 신약 7,959)

7.1  구멍 0 · 1절로 시작하지 않는 장 0 · 빈 절 0 · 절 없는 장 행 0
     DB 본문 = 수집해 둔 1,189장의 오프라인 재파싱 결과 (31,170절 전부 글자 단위 일치)
7.2  KJV와 절 수가 다른 장 106 (시편 62 / 그 밖 44) — 7.2의 고정 목록과 완전 일치
     LSG에만 있는 절 번호 114 / KJV에만 있는 절 번호 46
7.3  대문자 12자 연속 0 · 숫자 0
     마 5:15 "et on n’allume pas …" · 스 5:12 "Mais après que …" · 창 11:9 소제목 없음
7.4  mojibake 0 · NFC 아님 0 · NBSP 0 · U+2019 22,546절 · ASCII ' 0 · Éternel 6,973회 · Eternel 0
7.5  sacrificateur 766절(846회) / prêtre 40절(46회)
     요일 5:7 "Car il y en a trois qui rendent témoignage:" (삼위 증언 구절 없음)
     행 28:29 [ … ] · 삼상 6:19 [cinquante mille] · 시 3:1 표제만 · 시 3:2 "O Éternel, …"
7.6  DB = 재파싱 결과이므로 B와의 차이는 14.2의 100곳 그대로
```

유다서를 다시 돌리면 `inserted=0, skipped=25`로 총계가 변하지 않는다.

SBLM을 고친 뒤 `check_translation_drift.py --translation-id 35`로 대조한 결과, 눅 1,151절과 롬 434절 모두 **차이 0**이다.

### 14.7 구현하며 드러난 것

- **[5.1](#51-a안--ebible-fralsg) ②의 첫 설계는 동작하지 않았다.** 마커를 `" "` 노드로 바꾸면 누적 루프가 공백 노드를 건너뛰어 `eton`이 그대로 남는다. 구현 전에 한 줄짜리 실험으로 확인하고 공백을 뒤 텍스트 노드에 붙이는 방식으로 바꿨다. 설계 문서의 코드도 고쳤다.
- **DB는 Supabase 트랜잭션 풀러(6543)를 거친다. 세션 수준 설정이 다른 클라이언트에게 샌다.** 회귀 검사 스크립트의 연결을 `set_session(readonly=True, autocommit=True)`로 바꿨더니, psycopg2가 세션 수준 `SET default_transaction_read_only = on`을 보냈다. 그 설정이 풀러의 공유 백엔드에 남았고, 이어서 그 백엔드를 받은 DB 준비 드라이런이 `cannot execute ALTER TABLE in a read-only transaction`으로 실패했다.
  - 곧바로 스크립트를 멈췄다.
  - 그 시점의 Supavisor 백엔드 14개를 모두 확인했고, 읽기 전용이 남은 것은 없었다.
  - 같은 DB의 JDBC 연결 15개(서비스로 보인다)는 `application_name`이 Supavisor가 아닌 직접 연결이라 공유 백엔드를 받을 수 없었다.
  - 이후 모든 스크립트는 `SET LOCAL`이나 autocommit 없는 `readonly`(트랜잭션마다 `BEGIN READ ONLY`)만 쓴다. CLAUDE.md의 DB 계약에 적었다.
- **두 적재기를 동시에 돌리면 안 된다.** `sync_identity_sequences()`는 시작할 때 `setval(seq, MAX(id))`를 조건 없이 실행하고, `MAX(id)`에는 커밋된 행만 보인다. 다른 적재기가 장 하나를 쓰는 중이면 시퀀스가 그 아래로 되감겨 다음 삽입이 기본 키에서 충돌한다. SBLM 두 절 수정을 LSG 적재가 끝난 뒤로 미룬 이유다. 이번 작업의 적재 실행은 모두 순차였다. CLAUDE.md의 DB 계약에 적었다.
- **`ALTER TABLE`은 열린 읽기 트랜잭션에 막힌다.** 처음 회귀 스크립트는 읽기 트랜잭션을 끝내지 않아 `bible_translation`의 ACCESS SHARE 잠금을 쥐고 있었다. 그대로 `ALTER TABLE`을 보내면 대기열에 선 ACCESS EXCLUSIVE 요청 뒤로 **다른 모든 읽기가 막힌다.** 회귀 스크립트는 읽은 직후 트랜잭션을 닫게 바꿨고, DB 준비 스크립트에는 `SET LOCAL lock_timeout = '5s'`를 넣어 기다리지 않고 실패하게 했다.
