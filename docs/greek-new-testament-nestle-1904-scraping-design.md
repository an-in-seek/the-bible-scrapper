# 그리스어 성경 본문 스크래핑 개발 설계 — Nestle 1904 신약 / Rahlfs LXX 1935 검토

## 1. 목적

요청은 **Rahlfs 1935 칠십인역(구약) + Nestle 1904 비평본문(신약)** 조합을 기존 PostgreSQL 스키마(`bible_chapter`, `bible_verse`)에 적재하는 것이다.

**실측 결과 이 조합은 절반만 성립한다.** 신약(Nestle 1904)은 채택하고, 구약(Rahlfs LXX)은 **권리와 구조 두 가지 독립된 이유로 채택하지 않는다**. 아래에 근거를 하나씩 둔다.

### 1.1 제시된 근거 검토

요청과 함께 제시된 내용은 이렇다.

```
1. 구약 70인역: Rahlfs' Septuagint 1935
   저자 앨프레드 랄프스(1865~1935) → 2005-12-31 사후 70년 경과, 저작권 영구 소멸
   2006년 개정판(Rahlfs-Hanhart)을 제외한 1935년 오리지널 본문 데이터는 완전한 퍼블릭 도메인

2. 신약 비평본문: Nestle 1904 GNT
   에버하르트 네슬레(1851~1913) → 1983-12-31 사후 70년 경과, 저작권 완전 소멸
   BibleHub, eBible, SWORD, Wikisource 등에서 공인된 퍼블릭 도메인 텍스트로 배포

→ 두 조합은 어떠한 라이선스 고지 의무나 법적 분쟁 리스크 없이
  상용 앱·웹 서비스·DB에 무료로 안전하게 사용 가능
```

한 항목씩 조회한 결과다.

| 주장 | 판정 | 근거 |
| --- | --- | --- |
| 랄프스 1865년생 ~ 1935년 사망 | **맞다** | 1865-05-29 ~ 1935-04-08 |
| 네슬레 1851년생 ~ 1913년 사망 | **맞다** | 1851-05-01 ~ 1913-03-09 |
| 네슬레 1904는 퍼블릭 도메인 | **맞다.** 관할을 가리지 않는다 | [1.2](#12-nestle-1904--권리-관계는-깨끗하다) |
| Rahlfs 1935 **인쇄본**의 저자 사후 70년이 지났다 | **날짜는 맞다.** 다만 미국 관할과 보호 유형에 이견의 여지가 있다 | [1.3](#13-rahlfs-1935--인쇄본과-전자본은-다른-문제다) |
| Rahlfs 1935 **본문 데이터**는 완전한 퍼블릭 도메인 | **아니다** | [1.3](#13-rahlfs-1935--인쇄본과-전자본은-다른-문제다) |
| 두 조합을 상용에 리스크 없이 쓸 수 있다 | **신약은 그렇다. 구약은 아니다** | [1.3](#13-rahlfs-1935--인쇄본과-전자본은-다른-문제다), [1.4](#14-권리를-다-풀어도-lxx는-이-저장소의-66권-표에-들어가지-않는다) |

**"인쇄본이 퍼블릭 도메인"과 "쓸 수 있는 전자본이 퍼블릭 도메인"은 다른 문장이다.** 요청문은 이 둘을 한 문장으로 묶었고, Rahlfs에서는 그 둘이 갈라진다.

> 이 문서는 법률 자문이 아니다. 아래는 배포처·권리자·전사자의 표기를 조회한 결과이며 판단은 사용자 몫이다.

### 1.2 Nestle 1904 — 권리 관계는 깨끗하다

| 관할 | 상태 | 근거 |
| --- | --- | --- |
| 베른 협약 일반(한국·독일·영국 등) | **만료** — 1984-01-01 | 네슬레 1913 사망, 사후 70년 |
| 미국 | **만료** | 1904년 발행. 1930년 이전 발행물은 미국에서 무조건 퍼블릭 도메인이고, URAA 복원(발행 후 95년)을 가정해도 1999년에 끝난다 |

직전 일본어 작업([口語訳 설계](japanese-colloquial-1955-scraping-design.md) 1.2)에서 문제가 됐던 "일본은 만료, 미국은 존속" 같은 관할 분리가 여기서는 생기지 않는다.

**전자본 계보도 하나뿐이고 표기가 분명하다.** 현재 유통되는 Nestle 1904 디지털 텍스트는 전부 **Diego Renato dos Santos**가 Internet Archive의 1904년 초판·1913년 재쇄 스캔에서 전사한 것이다.

| 확인처 | 표기 (실측) |
| --- | --- |
| 전사자 본인 사이트 FAQ | "Yes, you may use it wherever you want. You are not obliged to, but I ask you to refer to this website." |
| studybible.info `/version/Nestle` | "This work (Η ΚΑΙΝΗ ΔΙΑΘΗΚΗ Text with Critical Apparatus, by Eberhard Nestle), identified by http://sites.google.com/site/nestle1904/ , is free of known copyright restrictions." / "Version 2.2 (July 27, 2012) Edited by Diego Santos" |
| GitHub `biblicalhumanities/Nestle1904` | "The base text was created by Diego Renato dos Santos" |
| GitHub `CenterBLC/N1904` (Text-Fabric) | 같은 전사본에서 파생. "Nestle 1904 (seventh edition: reprint 1913)" |

**출처 표기는 요청이지 의무가 아니다.** 그래도 표기하는 편이 낫고, 이 저장소에서는 설계 문서와 README에 남기는 것으로 충분하다.

> 계보가 하나라는 사실은 [4.9](#49-함정-7-제2-증인이-존재하지-않는다)에서 다시 문제가 된다. 대조할 독립 증인이 없다.

### 1.3 Rahlfs 1935 — 인쇄본과 전자본은 다른 문제다

**(가) 인쇄본.** 랄프스는 1935-04-08에 사망했고 같은 해에 두 권짜리 『Septuaginta』가 슈투트가르트 Privileg. Württembergische Bibelanstalt(현 Deutsche Bibelgesellschaft)에서 나왔다. 저자 사후 70년 기준이면 2006-01-01에 만료된다. 다만 두 가지가 남는다.

1. **보호 유형이 확정적이지 않다.** 고대 본문의 비평정본은 독일법에서 저작권(§64 UrhG, 사후 70년)이 아니라 학술판 보호(§70 UrhG, 발행 후 25년, 1960년 만료)의 대상이라고 볼 여지가 있다. 어느 쪽이든 오늘 기준으로는 만료지만, **어느 조항이 적용되는지가 다음 항목의 답을 바꾼다.**
2. **미국은 URAA 복원 가능성이 있다.** §64가 적용된다면 1996-01-01 시점에 독일에서 보호 중이었으므로 미국에서 발행 후 95년으로 복원되고, 그 경우 **2030년 말까지 존속하여 2031-01-01에 만료**한다(1935 + 95). 이것은 [口語訳 설계](japanese-colloquial-1955-scraping-design.md) 1.2가 정리한 것과 정확히 같은 구조다.

또한 현재 Deutsche Bibelgesellschaft가 판매하는 것은 **Rahlfs-Hanhart 2006년 개정판**(© 2006 Deutsche Bibelgesellschaft)이며, 요청문이 지적한 대로 그것은 별개의 보호 대상이다.

**(나) 전자본. 여기가 결정적이다.**

조회 범위 안에서 유통되는 Rahlfs 1935 전자본은 **전부 CCAT/CATSS(펜실베이니아 대학) 계보**이고, CATSS의 컴퓨터 판형 자체가 TLG(Thesaurus Linguae Graecae)에서 왔다. CCAT 배포 디렉터리에는 `0-user-declaration.txt`가 함께 놓여 있고 그 본문은 이렇다.

```
In accepting materials distributed by or through CCAT, the recipient agrees to
observe the following "fair use" provisions:

(1) Not to use or make available these materials for commercial purposes without
first obtaining the written consent of the owners/encoders;
...
(3) To control access to these materials and require any other party to whom the
recipient supplies any portion of this material to observe these conditions and
to register a signed USER AGREEMENT form with CCAT;
```

즉 **상용 사용은 서면 동의 없이는 금지**이고, 재배포 상대에게도 같은 서약서 등록을 요구한다. 파생물도 그 조건을 지고 다닌다.

| 배포물 | 표기 (실측) | 상용 |
| --- | --- | --- |
| CCAT `lxxmorph` 원본 | 위 사용자 서약서 | **불가**(서면 동의 필요) |
| `eliranwong/LXX-Rahlfs-1935` | `Creative Commons Attribution-NonCommercial-ShareAlike 4.0` | **불가** |
| `CenterBLC/LXX` | 저장소 라이선스는 **MIT** | **표시가 어긋난다**(아래) |
| biblebento.com `lxx1` | 위 CC BY-NC-SA 저장소를 그대로 싣고 CCAT 서약서를 안내 | **불가** |

넷을 따로 조회했는데 **모두 같은 한 계보로 되돌아간다.**

`CenterBLC/LXX`의 README는 출처를 스스로 밝히고 있다.

```
As a direct source for the CBLC version of RLXX1935 we have used Eliran Wong's work
on the RLXX1935 (https://github.com/eliranwong/LXX-Rahlfs-1935). His work is based on
the data available at the Computer Assisted Tools for Septuagint Studies (CATSS)...
```

**MIT 표기가 CC BY-NC-SA 파생물 위에 얹혀 있다.** 이런 표기 충돌이 있는 데이터를 상용 DB의 근거로 삼을 수는 없다. 요청문이 인용한 "인터넷에서 구한 아무 파일이나 쓰면 안 된다"는 원칙(직전 [和合本 설계](chinese-union-version-1919-scraping-design.md) 1.1)이 여기서 그대로 재현된다.

> 정리하면 **Rahlfs 1935는 "인쇄본은 아마도 만료, 전자본은 상용 금지"** 상태다. 스캔본에서 새로 전사하면 이 제약을 벗어날 수 있지만, 그것은 스크래핑이 아니라 OCR·교정 프로젝트이고 이 문서의 범위 밖이다.

### 1.4 권리를 다 풀어도 LXX는 이 저장소의 66권 표에 들어가지 않는다

권리 문제를 전부 해결했다고 가정해도 **구조가 맞지 않는다.** Rahlfs 본문 자체를 받지 않았으므로(위 이유), 권리가 깨끗한 다른 칠십인역으로 대신 실측했다 — eBible.org `grclxx`(『Η Παλαιά Διαθήκη κατά τη μετάφραση των εβδομήκοντα』, 배포 표기 `Public Domain`, 발행 주체 Orthodox Media Network).

**칠십인역 전체 구조 (USFM 번들 실측)**

```
52권 / 1,088장 / 27,766절
```

**66권 표의 구약 39권과 대조하면**

| 문제 | 실측 |
| --- | --- |
| 그 코드로 아예 없는 책 | `EZR`(에스라)·`EST`(에스더)·`DAN`(다니엘) — 각각 `ΕΣΔΡΑΣ Β`, `ΕΣΘΗΡ`(그리스어 추가분 포함), `ΔΑΝΙΗΛ`(추가분 포함)으로 따로 있다 |
| 사무엘·열왕기 | `ΒΑΣΙΛΕΙΩΝ Α~Δ`(왕국기 1~4)로 묶여 이름과 경계가 다르다 |
| 장 수가 다른 책 | 시편 **151**(KJV 150), 잠언 **29**(31), 요엘 **4**(3) |
| 정경 밖 책 | 토빗·유딧·지혜서·집회서·바룩·마카베오 1·3·4서 등 16권 |

**장별 절 수를 KJV 격자와 맞대면**

```
비교한 장 931개
  절 수 일치      631
  절 수 다름      296   ← 32%
  LXX에만 있는 장   2   (시편 151, 요엘 4)
  KJV에만 있는 장   2   (잠언 30·31)
```

시편은 **150장 중 139장이 다르다.** 원인은 잘 알려진 번호 밀림이고, 실측이 그대로 보여 준다.

| LXX | 절 수 | 대응하는 KJV | 절 수 |
| --- | --- | --- | --- |
| 9편 | 39 | 9편 + 10편 | 20 + 18 |
| 10편 | 7 | 11편 | 7 |
| 22편 | 6 | 23편 | 6 |
| 113편 | 26 | 114편 + 115편 | 8 + 18 |
| 114 / 115편 | 9 / 10 | 116편을 둘로 나눔 | 19 |
| 116편 | 2 | 117편 | 2 |
| 146 / 147편 | 11 / 9 | 147편을 둘로 나눔 | 20 |
| 151편 | 7 | **없음** | — |

**예레미야는 52장 중 36장이 다르다.** 장 수는 52로 같지만 열국에 대한 신탁이 25:13 뒤로 옮겨져 있어 같은 번호가 다른 본문을 가리킨다. **장 수만 맞춰 놓고 적재하면 번호는 멀쩡한데 내용이 어긋난 데이터가 된다.**

Rahlfs를 실제로 쓴다면 여기에 **이중 본문**이 더해진다. CCAT 파일 목록이 그대로 증거다.

```
07.JoshB / 08.JoshA      09.JudgesB / 10.JudgesA      22.TobitBA / 23.TobitS
59.BelOG / 60.BelTh      61.DanielOG / 62.DanielTh    63.SusOG / 64.SusTh
30.Odes                  37.PsSol                     27.4Macc
```

한 책에 본문이 둘인 경우가 6건이고, 어느 정경에도 없는 『송가』·『솔로몬의 시편』까지 들어 있다. **`bible_book`이 역본당 66행이고 `bible_verse`가 (장, 절) 하나에 본문 하나인 이 스키마에는 표현할 자리가 없다.**

> 이것은 소스를 바꿔서 해결되는 문제가 아니다. **칠십인역이 마소라 본문과 다른 책·다른 장·다른 절 구분을 갖는다는 사실 자체**가 원인이다. 그리스어 구약을 넣으려면 스키마를 바꾸거나 별도 테이블을 두어야 하고, 그것은 이 도구가 지금까지 지켜 온 계약([CLAUDE.md](../CLAUDE.md) "Contracts that must hold")을 다시 쓰는 일이다.

### 1.5 후보 소스 비교

**신약**

| 후보 | 본문 | 상태 (실측) | 판정 |
| --- | --- | --- | --- |
| **studybible.info `/Nestle/`** | **Nestle 1904** | 260장 전권 파싱 성공, 7,942절, 장당 42 KB, 절 마커가 링크로 표시됨 | **채택** |
| sites.google.com/site/nestle1904 | Nestle 1904 (원 전사본) | 같은 본문. 장당 **489 KB**(내용은 2 KB), 클래스명이 난독화 해시(`zfr3Q`, `C9DxTc`), **절 번호가 본문 안 평문** | 제외 — 전송량 12배, 셀렉터 수명 불확실 |
| biblehub.com/nestle/ | Nestle 1904 | 장당 21 KB, DOM이 가장 깨끗 | **제외 — 이용약관 6(d)가 상용 사용을 금지**한다 |
| newchristianbiblestudy.org | Nestle 1904 | 장당 150 KB | 제외 — 같은 본문에 전송량만 크다 |
| eBible `grc-tisch` 등 6종 | Tischendorf 8판·Textus Receptus·Robinson-Pierpont 등 | 전부 `public domain`, **기존 eBible 어댑터로 코드 0** | 제2 증인 및 대안([10.1](#101-그리스어-신약--코드를-한-줄도-안-쓰는-길)) |
| eBible `grcsbl`, `grcf35` | SBLGNT / Family 35 | **저작권 표기 있음** | 제외 |
| BibleGateway | SBLGNT, THGNT 둘뿐 | 둘 다 저작권 있음 | 제외 — 기존 어댑터가 있어도 쓸 수 없다 |

**구약**

| 후보 | 본문 | 상태 (실측) | 판정 |
| --- | --- | --- | --- |
| CCAT / eliranwong / CenterBLC | Rahlfs 1935 | 상용 금지 또는 표기 충돌 | 제외([1.3](#13-rahlfs-1935--인쇄본과-전자본은-다른-문제다)) |
| eBible `grclxx` | 정교회 칠십인역 | 권리 표기는 깨끗(`public domain`) | 제외 — **구조가 안 맞는다**([1.4](#14-권리를-다-풀어도-lxx는-이-저장소의-66권-표에-들어가지-않는다)) |
| eBible `grcbrent` | Brenton 칠십인역(1851) | 1851년 발행이라 권리는 깨끗 | 같은 이유로 제외 |
| 마소라 본문을 옮긴 그리스어 역본 | — | **찾지 못했다** | [10.2](#102-그리스어-구약--퍼블릭-도메인은-있다-맞지-않을-뿐이다) |

`grclxx`가 Rahlfs가 **아니라는** 근거는 배포 표기(Orthodox Media Network)와 수록 범위다. Rahlfs에 있는 『송가』·『솔로몬의 시편』과 6건의 이중 본문이 `grclxx`에는 없다. 다만 **본문 대조는 하지 않았다**([3.1](#31-확인하지-못한-것)).

---

## 2. 결론 먼저

1. **신약만 적재한다.** 역본 하나(`N1904`), 27권 260장 **7,942절**. 구약은 [1.3](#13-rahlfs-1935--인쇄본과-전자본은-다른-문제다)·[1.4](#14-권리를-다-풀어도-lxx는-이-저장소의-66권-표에-들어가지-않는다)의 두 이유로 넣지 않는다.
2. **새 소스 어댑터가 필요하다.** 기존 어댑터 중 Nestle 1904를 서비스하는 곳은 없다. 지금 파이프라인에 studybible.info 마태 1장을 그대로 넣으면 **그리스어 25절 대신 `Samuel 7:13` 한 줄**이 나온다([4.2](#42-dom-구조)).
3. **URL이 장 단위다.** `https://studybible.info/Nestle/Matthew 1`. 책 페이지 캐시가 필요 없고, 전권 요청 수는 **260회**, 전송량 **10.7 MB**다.
4. **KJV 신약과 절 수가 다르다: −17 +2.** KJV에 있는 17절이 없고(마 17:21 등 비평본문의 통상 생략), Nestle에만 있는 2절이 있다(요삼 1:15, 계 12:18). 7,957 − 17 + 2 = **7,942**로 정확히 맞는다([4.3](#43-함정-1-kjv에-있는-17절이-없다)).
5. **절 번호에 구멍이 생긴다 — 15곳, 14개 장에서**(막 9장만 두 곳). `(omitted)` 마커를 쓰지 **않기를** 권고하며, 대신 검증 질의를 **고정된 기대 목록 대조**로 바꾼다([4.3](#43-함정-1-kjv에-있는-17절이-없다), [7.3](#73-구멍-검증--연속성-대신-기대-목록)). 이것은 이 저장소의 첫 사례가 아니다 — **ASV에 이미 16곳, NKRV에 10곳의 구멍이 있고**(DB 실측), Nestle의 15곳은 **ASV의 16곳에서 요 5:4 하나만 뺀 것**이다.
6. **구멍 없이 짧아지는 장이 둘 더 있다**(행 19장, 고후 13장). 마지막 두 절을 합쳤기 때문이라 연속성 검사로는 절대 잡히지 않는다([4.4](#44-함정-2-구멍-없이-짧아지는-장이-둘-있다)).
7. **본문의 27.1%가 NFC가 아니다.** 원인은 U+0387 GREEK ANO TELEIA 2,359개와 이형 악센트 21개다. **마태복음 1:1의 첫 낱말 `Βίβλος`가 여기 해당**해서, 그대로 저장하면 정상적으로 입력한 검색어에 걸리지 않는다. **파서에서 NFC 정규화를 권고**한다([4.6](#46-함정-4-본문의-271가-nfc가-아니다)).
8. **DB 작업에 `language_code` CHECK 변경이 처음으로 들어간다.** 설계 당시 허용 목록에 그리스어 코드가 없었다([6.2](#62-language_code-check--그리스어-코드-추가)). 설계는 `grc`를 권고했고 그대로 적재했으나, **이후 DB가 `el`로 바뀌어 코드도 `el`로 맞췄다**([5.4](#54-기존-동작이-바뀐다--언어-코드)).
9. **`bible_book`은 66행이 아니라 27행(book_order 40~66)을 넣는다.** 구약 URL은 200을 돌려주지만 본문이 없고, 그 페이지를 지금 파이프라인에 넣으면 `John 1:1`·`Peter 3:5`라는 **1절부터 시작하는 가짜 절 2개**가 나온다 — CLI의 "1절로 시작하지 않으면 건너뛴다" 방어를 그대로 통과한다([6.5](#65-bible_book-27행--66행이-아닌-이유)).

---

## 3. 실측 검증 범위

| 검증 | 방법 | 결과 |
| --- | --- | --- |
| 네슬레·랄프스 생몰 | 사전 조회 | [1.1](#11-제시된-근거-검토) |
| Nestle 1904 전자본 계보 | 전사자 FAQ, studybible.info, GitHub 2곳 | 단일 계보 확인 |
| Rahlfs 전자본 라이선스 | CCAT `0-user-declaration.txt` 전문, GitHub 2곳 | [1.3](#13-rahlfs-1935--인쇄본과-전자본은-다른-문제다) |
| Rahlfs 수록 범위 | CCAT `lxxmorph` 파일 목록 전량 | 이중 본문 6건 확인 |
| LXX 구조 | eBible `grclxx` USFM **전권** 파싱 | 52권 1,088장 27,766절 |
| LXX ↔ KJV 격자 | 장별 절 수 비교(DB 질의) | 931장 중 296장 불일치 |
| 소스 후보 약관 | biblehub `/terms.htm`, studybible `robots.txt` | [1.5](#15-후보-소스-비교), [9.1](#91-요청-간격과-소요) |
| Nestle 본문 | studybible.info **260장 전권** 크롤·파싱 | 7,942절, 빈 절 0 |
| KJV 대조 | 절 번호 집합 비교(DB 질의) | −17 +2, 18개 장 |
| 문자 구성 | 파싱 결과 전량 문자 조사 | 라틴 문자 0, 숫자 0, 괄호 13절 |
| 유니코드 정규화 | 전량 NFC 대조 + 기존 DB 342,078행 대조 | [4.6](#46-함정-4-본문의-271가-nfc가-아니다) |
| 판본 지표 | 철자 계수(`Ἰωάν-`, `Μαθθα-`, `Δαυείδ`) | [7.5](#75-판본-검증--nestle-1904인지-확인) |
| 제2 증인 | eBible `grc-tisch` 절 번호 집합 대조 | 260장 중 254장 동일 |
| 컨테이너 구성 | 260장 전량 태그·클래스·`nbsp`·중복 마커 조사 | `sup`/`a` 외 태그 0, 블록 요소 0, 중복 0 |
| 파서 체인 자리 | 앞선 5개 소스 파서를 실제 Nestle 페이지에, 새 파서를 저장소 픽스처에 교차 실행 | 양방향 전부 `[]` |
| 검증 정규식 | 서버(`en_US.UTF-8`)에서 문자 클래스 동작 확인 | `[A-Za-z]`가 그리스 문자에 걸리지 않음 |
| 기존 파이프라인 오작동 | 새 어댑터 없이 파싱 | [4.2](#42-dom-구조), [6.5](#65-bible_book-27행--66행이-아닌-이유) |
| **[5장](#5-코드-변경-지점) 코드 스케치** | **문서에서 떼어 내 하위 클래스로 실행, 260장 재파싱** | **7,942절, 측정용 파서와 완전 일치** |
| 검증 SQL | [7장](#7-검증)의 질의를 기존 역본(ASV·CUVT)에 실행 | 전부 동작, PostgreSQL 17.6 |
| 기존 역본의 구멍 | 11개 역본 전량 `LEAD` 조사 | ASV 16곳, NKRV 10곳([4.3](#43-함정-1-kjv에-있는-17절이-없다)) |
| DB 현황 | `bible_translation`·CHECK·`bible_book`·`bible_book_description` 조회 | [6.1](#61-현재-상태-실측) |

### 3.1 확인하지 못한 것

- **Rahlfs 1935 본문을 직접 보지 않았다.** 상용 목적 프로젝트의 설계 근거로 삼을 수 없는 라이선스라 내려받지 않았다. 따라서 [1.4](#14-권리를-다-풀어도-lxx는-이-저장소의-66권-표에-들어가지-않는다)의 구조 실측은 **정교회 칠십인역(eBible `grclxx`) 기준**이고, Rahlfs에 그대로 옮겨진다는 것은 "시편 번호 밀림·예레미야 재배열·정경 밖 책은 칠십인역 전통의 성질"이라는 전제 위에 있다. 수록 범위 차이(이중 본문·송가·솔로몬의 시편)는 CCAT 파일 목록으로 별도 확인했다.
- **`grclxx`가 어느 인쇄판을 따르는지 대조하지 않았다.** 배포처가 판본명을 적지 않았고, 이 문서는 그 소스를 채택하지 않으므로 확인하지 않았다. `grclxx`를 실제로 쓰려면 [和合本 설계](chinese-union-version-1919-scraping-design.md) 1.3처럼 **판본 지표를 먼저 정해 대조해야 한다.**
- **1904년 인쇄본 스캔과 낱말 단위 대조를 하지 않았다.** 전자본 계보가 하나뿐이라 자동 대조 대상이 없다([4.9](#49-함정-7-제2-증인이-존재하지-않는다)). 인쇄본 대조는 표본 확인으로만 가능하다.
- **적재를 실행하지 않았다.** 이 문서는 설계까지다.

---

## 4. 대상 페이지 특성

### 4.1 URL 규칙 — 장 단위

```
https://studybible.info/Nestle/Matthew 1        ← 공백은 %20으로 인코딩
https://studybible.info/Nestle/1 Corinthians 13
https://studybible.info/Nestle/3 John 1
```

- 첫 경로 조각(`Nestle`)이 역본을 고른다. 같은 자리에 `KJV`, `ASV` 등이 들어간다 — 즉 **역본 토큰이 경로에 있다.** eBible·jpn.bible·wikisource와 같은 형태이므로 `get_source_version()`은 경로에서 읽는다([5.1](#51-scraperpy--소스-판별과-url)).
- 책 이름은 **영어 표기에 공백**이다. `BIBLEGATEWAY_BOOK_NAMES[39:66]`이 27권 모두와 **정확히 일치**한다(실측). 새 책 이름 표를 만들 필요가 없다.
- 한 장짜리 책도 `.../3 John 1`처럼 장 번호를 붙인다. 260장 전부 HTTP 200이다.
- **없는 장도 404가 아니라 200이다.** `Matthew 29`, `Revelation 23`, `Jude 2` 모두 200을 돌려주고 `div.passage`까지 있으며 그 안이 비어 있을 뿐이다(실측). 따라서 **장 수는 `KJV_CHAPTER_COUNTS`에서 가져와야 하고, 링크를 훑거나 404를 만날 때까지 세는 방식은 끝나지 않는다.** 구약 책 이름도 같은 응답을 주며, 그쪽은 더 위험하다([6.5](#65-bible_book-27행--66행이-아닌-이유)).

### 4.2 DOM 구조

```html
<div class="passage row Nestle">Nestle<sup><a class="version_info" href="/version/Nestle">(i)</a></sup>
  <sup><a class="verse_ref Nestle" href="/Nestle/Matthew%201:1"
         title="Matthew 1:1 Nestle">1</a></sup> Βίβλος γενέσεως ...
  <sup><a class="verse_ref Nestle" href="/Nestle/Matthew%201:2"
         title="Matthew 1:2 Nestle">2</a></sup> Ἀβραὰμ ἐγέννησεν ...
</div>
```

- **`div.passage`는 260장 모두 정확히 하나**이고 클래스는 항상 `('passage', 'row', 'Nestle')`이다(실측).
- **컨테이너 안의 태그는 `sup`과 `a` 둘뿐이다.** 260장 전량에서 `sup` 8,202개(절 마커 7,942 + 역본 안내 260)와 그 안의 `a` 8,202개가 전부이고, **`p`·`br`·`div` 같은 블록 요소가 하나도 없다.** `&nbsp;`도 0개다. 그래서 eBible 파서가 갖고 있는 블록 경계 공백 삽입(`block_changed`)이 여기서는 필요 없다([5.2](#52-scraperpy--파서)).
- **절 본문은 요소에 감싸여 있지 않다.** `sup > a.verse_ref`는 번호 마커일 뿐이고 본문은 형제 노드로 이어진다. eBible과 같은 구조이므로 **마커 사이를 누적**해야 한다. 和合本에서 쓴 문단 단위 누적은 여기서는 쓸 수 없다.
- **절 번호는 `title`(또는 `href`)에서 읽는다.** 표시 문자열과 `title`의 절 번호는 **7,942개 전부 일치**하므로(실측) 불일치를 고치려는 것이 아니라, `title`에 **장 번호도 들어 있어** 장이 섞인 입력을 방어할 수 있기 때문이다([5.2](#52-scraperpy--파서)).
- **한 장 안에서 같은 절 번호가 두 번 나오는 곳은 없다**(260장 실측 0건). BibleGateway처럼 같은 번호의 조각을 합쳐야 하는 처리가 필요 없다.
- 컨테이너 맨 앞의 `Nestle (i)`는 역본 안내 링크다. **첫 마커보다 앞에 있으므로 마커 사이 누적 방식에서는 자연히 빠진다** — eBible의 시편 표제와 같은 처리다. 실측에서 라틴 문자가 0개인 것이 이 사실을 확인해 준다.
- 각주·소제목·상호참조는 컨테이너 안에 **없다**.

**전용 파서가 없으면 어떻게 되는지**를 그대로 재 봤다.

```
$ 현재 파이프라인으로 studybible.info 마태 1장 파싱
  뽑힌 절 1개:   2 | "Samuel 7:13"
```

그리스어 25절 대신 사이트의 상호참조 내비게이션 한 줄이 나온다. 다행히 **1절로 시작하지 않아** CLI 방어에 걸려 기록되지는 않지만, 이 방어가 통하지 않는 경우가 [6.5](#65-bible_book-27행--66행이-아닌-이유)에 있다.

### 4.3 함정 1. KJV에 있는 17절이 없다

비평본문이라 KJV(공인본문)에 있는 절 일부를 싣지 않는다. **소스는 그 자리에 아무 표시도 하지 않는다** — 번호가 그냥 건너뛴다.

```
마 17:21  마 18:11  마 23:14
막 7:16   막 9:44   막 9:46   막 11:26  막 15:28
눅 17:36  눅 23:17
행 8:37   행 15:34  행 19:41  행 24:7   행 28:29
롬 16:24  고후 13:14
```

이 중 **행 19:41과 고후 13:14는 성격이 다르다**([4.4](#44-함정-2-구멍-없이-짧아지는-장이-둘-있다)). 나머지 15개는 장 가운데에 **구멍**을 남기고, 그 결과 **14개 장에서 절 번호가 불연속**이 된다.

반대로 **Nestle에만 있는 절이 둘** 있다.

| 절 | 내용 |
| --- | --- |
| 요삼 1:15 | KJV가 14절에 합쳐 둔 마지막 인사를 따로 센다(요삼 15절 / KJV 14절) |
| 계 12:18 | KJV가 13:1 앞부분으로 붙인 문장을 12장 끝 절로 센다 |

```
KJV 신약 7,957 − 17 + 2 = 7,942   ← 실측 파싱 결과와 정확히 일치
```

> **권고: `(omitted)` 마커를 쓰지 않는다.**
>
> WEB·spablm에서 `(omitted)`를 넣는 근거는 **소스 페이지가 그 자리에 각주를 찍어 "일부러 뺐다"는 증거를 남기기** 때문이다([CLAUDE.md](../CLAUDE.md) 참조). Nestle 1904 페이지에는 그 증거가 **아예 없다** — 번호가 없을 뿐이다. 하드코딩한 목록으로 마커를 채우면 소스가 주지 않은 데이터를 DB에 넣는 것이고, "DOM이 바뀌면 조용히 자리표시자로 채우지 말고 실패하라"는 원래 취지를 정면으로 거스른다.
>
> 대신 **연속성 검사를 이 역본에 쓰지 않고**, 고정된 기대 목록과 대조하는 질의로 바꾼다([7.3](#73-구멍-검증--연속성-대신-기대-목록)). 이것은 和合本에서 "KJV와 다른 4개 장"을 고정 목록으로 확인한 것과 같은 방식이다.

**이 저장소는 이미 구멍이 있는 역본을 담고 있다.** 적재된 11개 역본을 DB에서 훑은 결과다.

| 역본 | 절 번호 구멍 | `(omitted)` 행 |
| --- | --- | --- |
| ASV (23) | **16** | 0 |
| NKRV (2) | **10** | 0 |
| WEB (22) / SBLM (35) / JPNMEB (36) | 0 | 4 / 4 / 5 |
| 나머지 6개 역본 | 0 | 0 |

**ASV의 16곳은 Nestle의 15곳에 요 5:4 하나를 더한 것이다.** 같은 비평본문 계열의 같은 생략이고, ASV는 마커 없이 구멍으로 적재되어 있다. 즉 위 권고는 새 규칙이 아니라 **ASV에서 이미 쓰고 있는 방식**이며, 마커를 쓰는 세 역본은 전부 소스가 각주로 증거를 남긴 경우다.

파이프라인은 이 구멍을 그대로 받는다. `_sanitize_verses()`는 중복 제거와 빈 절 제거만 하고 연속성을 요구하지 않으며, CLI 방어는 **첫 절이 1인지**만 본다. 260장 전부 1절로 시작한다(실측).

### 4.4 함정 2. 구멍 없이 짧아지는 장이 둘 있다

| 장 | Nestle | KJV | 원인 |
| --- | --- | --- | --- |
| 사도행전 19장 | 40절 | 41절 | KJV 19:40–41을 한 절(40)로 합쳤다 |
| 고린도후서 13장 | 13절 | 14절 | KJV 13:12–13을 한 절(12)로 합쳤다 |

**마지막 절이 없어지므로 번호는 1..40, 1..13으로 연속이다.** 연속성 검사도, "첫 절이 1인가" 검사도 통과한다. **KJV 장별 절 수 대조 말고는 잡을 방법이 없다.**

```
절 수가 KJV와 다른 장 18개
  = 구멍이 생긴 장 14  +  구멍 없이 짧은 장 2  +  Nestle이 더 긴 장 2
```

### 4.5 함정 3. 편집 괄호가 본문 안에 있다

네슬레의 서문(studybible.info `/version/Nestle`이 그대로 싣고 있다)이 기호를 정의한다.

```
⟦ ⟧   Double brackets mark passages which the critical editors ... consider
      very early interpolations; e.g. Mk 16, 9.
< >   Indicate a passage for which ancient authority is in part wanting;
      e.g. John 5, 3. 4.
```

디지털 본문은 이중 괄호를 **ASCII `[[ ]]`**로 옮겼다. 실측 분포는 이렇다.

| 기호 | 절 수 | 위치 |
| --- | --- | --- |
| `[[ ]]` | 7 | 막 16:9·16:20, 눅 24:12·24:36·24:40·24:51·24:52 |
| `[ ]` | 1 | 엡 1:1 `[ἐν Ἐφέσῳ]` |
| `< >` | 5 | 막 1:1 `<Υἱοῦ Θεοῦ>`, 요 5:3·5:4, 요 7:53, 요 8:11 |

`[` 13개 / `]` 13개 / `<` 3개 / `>` 3개, 합쳐서 **13개 절**이다.

두 가지를 알고 있어야 한다.

1. **여는 괄호와 닫는 괄호가 다른 절에 있다.** 막 16:9가 `[[`로 열리고 **막 16:20**이 `]]`로 닫힌다. 요 7:53이 `<`로 열리고 **요 8:11**이 `>`로 닫힌다. 절 단위로 보면 짝이 맞지 않는 것이 정상이다. 괄호 짝 맞추기를 검증 조건으로 쓰면 안 된다.
2. **간음한 여인 단락(요 7:53–8:11)과 마가 긴 결말(막 16:9–20)은 본문에 들어 있다.** 빠져 있지 않다.

> **권고: 괄호를 그대로 저장한다.** 이 저장소가 본문에 하는 일은 마크업 제거와 절 경계 정리뿐이고 낱말을 바꾸지 않는다. 괄호는 네슬레 판본의 일부다. 서비스에서 감추고 싶으면 표시 단계에서 처리한다.

### 4.6 함정 4. 본문의 27.1%가 NFC가 아니다

```
7,942절 중 NFC가 아닌 절   2,154 (27.1%)
NFC가 바꾸는 문자 수         2,380
NFC 전후 길이 변화              0   ← 1:1 치환이고 결합·분해가 아니다
알려진 7개 코드포인트를 빼고 남는 절  0   ← 원인이 전부 규명됐다
```

| 코드포인트 | 개수 | NFC 결과 |
| --- | --- | --- |
| U+0387 GREEK ANO TELEIA | 2,359 | U+00B7 MIDDLE DOT |
| U+1F71/1F77/1F79/1F7B/1F7D/1FD3 (oxia 계열) | 21 | 대응하는 tonos 문자(U+03AC 등) |

두 번째 줄이 실질적인 문제다. **21곳이 18개 절에 흩어져 있고, 그중 하나가 마태복음 1:1의 첫 낱말이다.**

```
마 1:1     Βίβλος    ← ί 가 U+1F77(oxia).  나머지 본문의 ί 는 U+03AF(tonos)
마 1:1     Ἀβραάμ    마 6:25 τί · πίητε   마 21:29 κύριε    막 5:41  κούμ
눅 3:27    Ζοροβάβελ 눅 7:11 Ναΐν         요 5:2   Βηθζαθά  행 9:19  ἐνίσχυσεν
행 20:24   τελειώσω  롬 16:14 Πατρόβαν    갈 3:21  νόμου    벧전 4:18 σώζεται
벧전 5:11  αἰώνων    벧후 1:3 ἰδίᾳ · δόξῃ 벧후 2:11 Κυρίῳ   벧후 2:15 Βεώρ
유 1:4     παρεισεδύησαν                  계 1:6   αἰώνων        (21곳 / 18개 절)
```

키보드로 정상 입력한 `Βίβλος`는 U+03AF를 쓰므로 **`WHERE text LIKE '%Βίβλος%'`가 마태복음 1:1을 못 찾는다.** 색인·중복 검사·대조 질의가 전부 조용히 어긋난다.

**기존 DB는 이 문제가 없다.**

```
bible_verse 342,078행 전량 조사 → NFC가 아닌 행 0
(11개 역본, 한국어·영어·스페인어·일본어·중국어 전부)
```

> **권고: 새 파서 안에서 `unicodedata.normalize("NFC", text)`를 적용한다.**
>
> - NFC는 유니코드가 정의한 **정준 동치** 변환이라 정보가 사라지지 않는다. 실측대로 길이도 안 바뀐다.
> - **전역이 아니라 이 소스에서만 적용한다.** 다른 소스는 이미 전부 NFC이므로 무효 연산이고, 전역 처리는 검증되지 않은 경로를 만든다.
> - **`scripts/check_translation_drift.py`는 영향을 받지 않는다.** 그 도구는 `fetch_chapter_payload()`로 **같은 어댑터를 다시 태워** 비교하므로 양쪽에 똑같이 정규화가 걸린다(코드 확인). 정규화를 파서 밖에 두면 이 성질이 깨진다.
> - 대안은 "그대로 저장하고 조회 측에서 정규화"인데, 이 저장소가 통제하지 못하는 소비자에게 부담을 넘기는 선택이다. 그 길을 고른다면 [7.4](#74-문자-검증)의 NFC 질의를 **0을 기대하는 검사에서 2,154를 기대하는 검사로** 바꿔야 한다.

### 4.7 함정 5. 그리스어 문장부호는 라틴 문자가 아니다

파싱 결과 전량의 비그리스 문자 목록이다.

| 문자 | 개수 | 비고 |
| --- | --- | --- |
| `,` `.` | 9,462 / 5,715 | |
| `’` U+2019 | 1,220 | 모음 생략 부호 |
| `;` | 971 | **그리스어에서는 물음표다.** 문장 끝으로 오해하면 안 된다 |
| `—` U+2014 | 47 | |
| `[` `]` | 13 / 13 | [4.5](#45-함정-3-편집-괄호가-본문-안에-있다) |
| `(` `)` | 8 / 8 | |
| `<` `>` | 3 / 3 | [4.5](#45-함정-3-편집-괄호가-본문-안에-있다) |
| `'` U+0027 | **1** | 나머지 1,220곳이 U+2019인데 한 곳만 ASCII다 — 소스의 흔들림 |

**라틴 문자 0개, 아라비아 숫자 0개.** 절 번호가 본문에 새는지, 내비게이션이 섞이는지를 이 두 개수로 곧장 검사할 수 있다([7.4](#74-문자-검증)).

`·`(ano teleia)는 그리스 문자 블록 안에 있어 위 표에 없지만 2,359개다([4.6](#46-함정-4-본문의-271가-nfc가-아니다)).

### 4.8 함정 6. `CJK_JOIN_PATTERN`을 붙이지 않는다

블록 경계 공백을 지우는 `CJK_JOIN_PATTERN`은 일본어·중국어용이다. 그리스어는 낱말을 띄어 쓰므로 **붙이면 안 되고**, 실제로 `CJK_RANGES`에 그리스 문자가 없어 무효 연산이다. 무효라도 **넣지 않는다** — 넣으면 다음 사람이 "그리스어에도 필요한 처리"로 읽는다. 한글을 `CJK_RANGES`에서 일부러 뺀 것과 같은 이유다.

### 4.9 함정 7. 제2 증인이 존재하지 않는다

Nestle 1904 디지털 텍스트는 **전부 Diego Santos 전사본 하나에서 갈라져 나왔다**([1.2](#12-nestle-1904--권리-관계는-깨끗하다)). studybible.info, BibleHub, newchristianbiblestudy, `biblicalhumanities/Nestle1904`, `CenterBLC/N1904`가 모두 같은 계보다. **서로를 검증할 수 없다.** 直前 일본어 작업에서 STEPBible·baiburu·jpn.bible이 한 계보로 묶였던 것과 같은 상황이다.

따라서 제2 증인은 두 가지로 나눠 세운다.

1. **구조 증인**: eBible `grc-tisch`(Tischendorf 8판). 다른 편집자의 독립 비평본문이고 같은 Stephanus 절 구분을 쓴다. **절 번호 집합을 대조**하면 파싱 누락을 잡을 수 있다([7.6](#76-제2-증인--구조-대조)).
2. **낱말 증인**: archive.org의 1904년·1913년 인쇄본 스캔. **표본 확인만 가능**하다.

---

## 5. 코드 변경 지점

### 5.1 `scraper.py` — 소스 판별과 URL

```python
DEFAULT_STUDYBIBLE_N1904_ENTRY_URL = "https://studybible.info/Nestle/Matthew%201"
DEFAULT_STUDYBIBLE_VERSION = "Nestle"
STUDYBIBLE_MIN_DELAY_SECONDS = 1.0
STUDYBIBLE_FIRST_NT_BOOK_ORDER = 40
# 절 마커의 title은 "Matthew 1:1 Nestle" 꼴이다. 장 번호가 들어 있어, 장이 섞인
# 입력을 파서가 거부할 수 있다.
STUDYBIBLE_REF_PATTERN = re.compile(r"^(?P<book>.+?)\s(?P<chapter>\d{1,3}):(?P<verse>\d{1,3})$")
```

```python
    def _is_studybible_source(self) -> bool:
        return "studybible.info" in urlparse(self.entry_url or "").netloc.lower()

    def _get_studybible_version(self) -> str:
        """First path segment of the entry URL, e.g. ".../Nestle/Matthew%201"."""
        segments = [part for part in urlparse(self.entry_url or "").path.split("/") if part]
        return segments[0] if segments else DEFAULT_STUDYBIBLE_VERSION

    def _build_studybible_url(self, book_order: int, chapter_number: int) -> str:
        # Nestle 1904 is a New Testament edition. An Old Testament URL answers 200 with an
        # empty passage box, which the generic chain then reads as two plausible verses,
        # so the range guard is a write guard, not a tidiness check.
        if not STUDYBIBLE_FIRST_NT_BOOK_ORDER <= book_order <= len(BIBLEGATEWAY_BOOK_NAMES):
            raise ValueError(f"Invalid studybible book order: {book_order}")

        parsed = urlparse(self.entry_url or DEFAULT_STUDYBIBLE_N1904_ENTRY_URL)
        base_url = urlunparse(parsed._replace(path="", params="", query="", fragment=""))
        book_name = BIBLEGATEWAY_BOOK_NAMES[book_order - 1]
        # quote() keeps the observed "%20" form; urlencode() would emit "+".
        return f"{base_url}/{self._get_studybible_version()}/{quote(f'{book_name} {chapter_number}')}"
```

- `get_source_name()`에 `"studybible"` 분기, `get_source_version()`에 `_get_studybible_version()` 분기, `_build_chapter_url()`·`discover_chapter_urls_for_book()`에 분기를 더한다.
- `_discover_chapter_urls_for_studybible()`은 `KJV_CHAPTER_COUNTS`를 그대로 쓴다(다른 소스와 같은 비공개 메서드 이름 규칙). 신약 27권의 장 수는 실측에서 KJV와 전부 일치했고, **없는 장이 200을 돌려주므로 훑어서 세는 방식은 쓸 수 없다**([4.1](#41-url-규칙--장-단위)).
- `__init__`의 소스별 지연 하한에 `STUDYBIBLE_MIN_DELAY_SECONDS`를 추가한다(eBible·jpn.bible·wikisource와 같은 1.0초).

### 5.2 `scraper.py` — 파서

```python
    def _extract_verses_from_studybible_page(self, soup: BeautifulSoup) -> list[Verse]:
        """
        Parse a studybible.info chapter page:
          <div class="passage row Nestle">
            <sup><a class="verse_ref Nestle" title="Matthew 1:1 Nestle">1</a></sup> Βίβλος ...
          </div>

        Like eBible, the marker holds only the number and the body follows as sibling
        nodes, so text is accumulated between markers. The "Nestle (i)" version link sits
        before the first marker and is dropped by that alone.
        """
        version = self._get_studybible_version()
        container = None
        for candidate in soup.select("div.passage"):
            if version in (candidate.get("class") or []):
                container = candidate
                break
        if container is None:
            return []

        working = BeautifulSoup(str(container), "html.parser")
        if working.select_one("a.verse_ref") is None:
            return []

        chunks: dict[int, list[str]] = {}
        chapters: set[int] = set()
        current: int | None = None

        for node in working.descendants:
            if isinstance(node, Tag):
                if node.name == "a" and "verse_ref" in (node.get("class") or []):
                    # The title is authoritative and carries the chapter as well.
                    match = STUDYBIBLE_REF_PATTERN.match(
                        (node.get("title") or "").removesuffix(f" {version}").strip()
                    )
                    current = int(match.group("verse")) if match else None
                    if match:
                        chapters.add(int(match.group("chapter")))
                continue

            if not isinstance(node, NavigableString) or current is None:
                continue
            # Marker text is the verse number, and the version link is not body text.
            if node.find_parent("a") is not None or node.find_parent("sup") is not None:
                continue
            if node.strip():
                chunks.setdefault(current, []).append(str(node))

        if len(chapters) > 1:
            logger.warning("studybible page mixes chapters %s; skipping", sorted(chapters))
            return []

        verses: list[Verse] = []
        for verse_number in sorted(chunks):
            # 27% of this source is not NFC: U+0387 and 21 oxia letters. Left as-is,
            # Matthew 1:1 does not match a normally typed "Βίβλος".
            text = unicodedata.normalize("NFC", self._normalize_text("".join(chunks[verse_number])))
            if text:
                verses.append(Verse(verse_number=verse_number, text=text))
        return verses
```

**체인에서의 자리**는 wikisource 뒤, `bibletable` 앞이다.

```
bskorea → biblegateway → ebible → jpnbible → wikisource → studybible
        → bibletable → chapter-prefixed → ordered list → structured nodes → regex
```

- 소스별 파서는 전부 일반 파서보다 앞에 온다는 규칙 그대로다. [4.2](#42-dom-구조)에서 본 대로, 뒤에 두면 일반 파서가 상호참조 내비게이션을 절로 읽는다.
- 자기 페이지가 아니면 **`[]`를 돌려주고 예외를 던지지 않는다**. 판별자는 `div.passage` + 역본 클래스 + `a.verse_ref`이고, 이 조합은 다른 어느 소스에도 없다.
- **eBible 파서와 달리 블록 경계 공백을 넣지 않는다.** 컨테이너 안에 블록 요소가 하나도 없기 때문이다([4.2](#42-dom-구조)). 넣어도 지금은 무효지만, 넣으면 다음 사람이 "이 소스에도 문단이 있다"로 읽는다.
- 장 혼재 방어는 방어적 조치다. 260장 전부 단일 장이었고(실측), URL이 장 단위라 지금은 발생하지 않는다. jpn.bible·wikisource에서 같은 방어가 실제 함정이었으므로 형태를 맞춰 둔다.

> 위 두 블록의 코드를 **문서에서 그대로 떼어 내 실행**했다. `HolyBibleScraper` 하위 클래스에 붙여 캐시된 260장에 돌린 결과 **7,942절**이 나왔고, 별도로 작성한 측정용 파서의 결과와 **절 번호·본문이 전부 일치**했다. URL 빌더는 `book_order` 1·39·67에서 `ValueError`를 냈고, 빈 구약 페이지·다른 소스 4종·다른 역본(`div.passage.KJV`)·장 혼재 입력에서 모두 `[]`를 돌려줬다.

### 5.3 `scrape_bible_to_db.py` — 역본 등록

```python
ENTRY_URL_ENV_BY_TRANSLATION_TYPE = { ..., "N1904": "N1904_ENTRY_URL" }
TRANSLATION_TYPES_BY_LANGUAGE_CODE = { ..., "el": ("N1904",) }
TRANSLATION_SOURCE_REQUIREMENTS = {
    ...,
    "N1904": {
        "source": "studybible",
        "version": "Nestle",
        "name": "Η Καινή Διαθήκη (Nestle 1904)",
        "language_code": "el",
    },
}
```

- `version`을 반드시 채운다. studybible.info는 한 호스트에서 60종 넘는 역본을 서비스하므로, **비워 두면 `_expected_translation_type()`이 이 호스트의 모든 역본을 `N1904`로 통과시킨다.** `/KJV/Matthew 1`을 실수로 넣어도 막지 못한다.
- `name`은 [6.4](#64-bible_translation-1행)에서 넣는 `bible_translation.name`과 **글자까지 같아야 한다.** `_translation_type_by_identity()`가 (`name`, `language_code`)로 역본을 되찾으므로, 어긋나면 `translation_type`이 비어 있을 때의 대체 경로가 조용히 죽는다.
- `resolve_book_code_for_source()`는 손대지 않는다. URL 빌더가 `BIBLEGATEWAY_BOOK_NAMES`에서 직접 이름을 얻으므로 `None`으로 충분하다.
- `resolve_default_entry_url()`은 `el`에 역본이 하나뿐이라 지금은 모호성이 없다.

### 5.4 기존 동작이 바뀐다 — 언어 코드

- 설계 당시 CHECK 허용 목록에 그리스어 코드가 **하나도 없었다**(`grc`도 `el`도). CHECK 변경이 필요하다([6.2](#62-language_code-check--그리스어-코드-추가)).
- 설계는 **`grc`(ISO 639-3, 고대 그리스어)** 를 권고했다. `el`(ISO 639-1)은 현대 그리스어를 뜻하므로, 나중에 Βάμβας 같은 현대 그리스어 역본을 넣으면 같은 코드를 나눠 쓰게 되기 때문이다. 처음 적재도 `grc`로 했다([12.5](#125-적재-결과-실측)).
- **적재 후 DB가 `el`로 바뀌었다.** 2026-09-27에 조회하니 N1904 행의 `language_code`가 `el`이고, CHECK 목록에서도 `grc`가 빠지고 `el`이 들어가 있었다. CHECK까지 다시 쓴 변경이라 의도된 것으로 보고, **코드를 DB에 맞췄다** — 이 도구는 `bible_translation`을 읽기만 하므로 기준은 DB다. 그대로 두면 `BIBLE_LANGUAGE_CODE=grc` 실행이 `Could not resolve bible_translation.id`로 실패하고, `BIBLE_LANGUAGE_CODE=el` 실행은 엔트리 URL을 찾지 못한다.
- 본문이 현대 그리스어가 되는 것은 아니다. **코이네 본문에 `el` 코드가 붙어 있다**는 사실만 남는다. 위에서 걱정한 공유 문제는 현대 그리스어 역본을 넣을 때 실제로 생기며, 그때는 `en`·`es`·`ja`·`zh`와 같은 방식(같은 언어의 URL이 둘 이상 설정되면 추측하지 않고 예외)으로 처리된다.
- **신약만 있는 역본이 처음 생긴다.** `--resume`은 "절이 하나라도 있는 최대 `book_order` 다음"부터 시작하므로 27권 구성에서도 그대로 동작한다. 다만 `bible_book`을 27행만 넣는 선택과 짝을 이뤄야 한다([6.5](#65-bible_book-27행--66행이-아닌-이유)).

---

## 6. DB 준비

### 6.1 현재 상태 (실측)

```
[bible_translation]        33행, 최대 translation_order = 36 (CUVS)
[translation_type CHECK]   33개 값, 'N1904' 없음
[language_code CHECK]      ko,en,zh,ja,es,de,la — 'grc' 없음, 'el'도 없음   ← 설계 당시. 지금은 끝에 'el'이 있다(5.4)
[language_code 컬럼]       character varying(4)  → 'grc' 3글자는 들어간다
[bible_book_description]   en/es/ja/ko/zh 각 66행 — grc 없음
[bible_verse]              342,078행, 전량 NFC
```

### 6.2 `language_code` CHECK — 그리스어 코드 추가

```sql
ALTER TABLE public.bible_translation DROP CONSTRAINT bible_translation_language_code_check;
ALTER TABLE public.bible_translation ADD CONSTRAINT bible_translation_language_code_check
  CHECK (language_code IN ('ko', 'en', 'zh', 'ja', 'es', 'de', 'la', 'el'));
```

처음 적재할 때는 끝 값이 `'grc'`였다. 지금 DB는 위와 같이 `'el'`이다([5.4](#54-기존-동작이-바뀐다--언어-코드)).

**이 저장소에서 `language_code` CHECK를 건드리는 것은 처음이다.** 지금까지 추가한 언어(`zh`, `ja`)는 이미 목록에 있었다.

### 6.3 `translation_type` CHECK — 34번째 값

```sql
ALTER TABLE public.bible_translation DROP CONSTRAINT bible_translation_translation_type_check;
ALTER TABLE public.bible_translation ADD CONSTRAINT bible_translation_translation_type_check
  CHECK (translation_type IN ( … 기존 33개 값 … , 'N1904'));
```

기존 값을 **순서까지 그대로 보존**해야 한다. 하나라도 빠뜨리면 그 역본의 이후 삽입이 막힌다.

### 6.4 `bible_translation` 1행

```sql
INSERT INTO public.bible_translation (translation_type, name, language_code, translation_order)
SELECT 'N1904', 'Η Καινή Διαθήκη (Nestle 1904)', 'el',
       COALESCE(MAX(translation_order), 0) + 1
FROM public.bible_translation;
```

`translation_order`는 NOT NULL이고 기본값이 없다. 현재 최대가 36이므로 **37**이 된다. `name`과 `translation_type`에 각각 UNIQUE가 있다.

### 6.5 `bible_book` 27행 — 66행이 아닌 이유

```sql
INSERT INTO public.bible_book (translation_id, book_order, book_key, abbreviation, name, testament_type)
SELECT t.id, s.book_order, s.book_key, s.abbreviation, s.name, 'NEW'
FROM public.bible_translation t
CROSS JOIN (VALUES
  (40,'MAT','Ματθ','ΚΑΤΑ ΜΑΘΘΑΙΟΝ'),        (41,'MRK','Μαρκ','ΚΑΤΑ ΜΑΡΚΟΝ'),
  (42,'LUK','Λουκ','ΚΑΤΑ ΛΟΥΚΑΝ'),          (43,'JHN','Ιωαν','ΚΑΤΑ ΙΩΑΝΗΝ'),
  (44,'ACT','Πραξ','ΠΡΑΞΕΙΣ ΑΠΟΣΤΟΛΩΝ'),    (45,'ROM','Ρωμ','ΠΡΟΣ ΡΩΜΑΙΟΥΣ'),
  (46,'1CO','Α Κορ','ΠΡΟΣ ΚΟΡΙΝΘΙΟΥΣ Α'),   (47,'2CO','Β Κορ','ΠΡΟΣ ΚΟΡΙΝΘΙΟΥΣ Β'),
  (48,'GAL','Γαλ','ΠΡΟΣ ΓΑΛΑΤΑΣ'),          (49,'EPH','Εφεσ','ΠΡΟΣ ΕΦΕΣΙΟΥΣ'),
  (50,'PHP','Φιλ','ΠΡΟΣ ΦΙΛΙΠΠΗΣΙΟΥΣ'),     (51,'COL','Κολ','ΠΡΟΣ ΚΟΛΟΣΣΑΕΙΣ'),
  (52,'1TH','Α Θεσ','ΠΡΟΣ ΘΕΣΣΑΛΟΝΙΚΕΙΣ Α'),(53,'2TH','Β Θεσ','ΠΡΟΣ ΘΕΣΣΑΛΟΝΙΚΕΙΣ Β'),
  (54,'1TI','Α Τιμ','ΠΡΟΣ ΤΙΜΟΘΕΟΝ Α'),     (55,'2TI','Β Τιμ','ΠΡΟΣ ΤΙΜΟΘΕΟΝ Β'),
  (56,'TIT','Τιτ','ΠΡΟΣ ΤΙΤΟΝ'),            (57,'PHM','Φιλημ','ΠΡΟΣ ΦΙΛΗΜΟΝΑ'),
  (58,'HEB','Εβρ','ΠΡΟΣ ΕΒΡΑΙΟΥΣ'),         (59,'JAS','Ιακ','ΙΑΚΩΒΟΥ ΕΠΙΣΤΟΛΗ'),
  (60,'1PE','Α Πετ','ΠΕΤΡΟΥ Α'),            (61,'2PE','Β Πετ','ΠΕΤΡΟΥ Β'),
  (62,'1JN','Α Ιω','ΙΩΑΝΟΥ Α'),             (63,'2JN','Β Ιω','ΙΩΑΝΟΥ Β'),
  (64,'3JN','Γ Ιω','ΙΩΑΝΟΥ Γ'),             (65,'JUD','Ιουδ','ΙΟΥΔΑ'),
  (66,'REV','Αποκ','ΑΠΟΚΑΛΥΨΙΣ ΙΩΑΝΟΥ')
) AS s(book_order, book_key, abbreviation, name)
WHERE t.translation_type = 'N1904';
```

세 열의 출처가 서로 다르니 구분해 둔다.

- `book_key`는 **KJV 행의 값을 그대로 쓴다**(`MAT`…`REV`, DB에서 확인). 컬럼이 `varchar(4)`라 전부 들어간다.
- `name`은 **네슬레 1904 판본의 책 제목**이다. 채택 소스(studybible.info)는 책 이름을 영어로만 표시하므로, 27권 모두 **원 전사본 사이트의 페이지 제목에서 가져왔다**([1.5](#15-후보-소스-비교)에서 전송량 때문에 소스로는 쓰지 않기로 한 그 사이트다 — 본문이 아니라 제목 27개만 한 번 읽었다). 철자에 판본 정보가 들어 있다: `ΚΑΤΑ ΜΑΘΘΑΙΟΝ`(θθ), `ΚΑΤΑ ΙΩΑΝΗΝ`(ν 하나). 공인본문 계열은 `ΜΑΤΘΑΙΟΝ`, `ΙΩΑΝΝΗΝ`으로 쓴다([7.5](#75-판본-검증--nestle-1904인지-확인)).
- `abbreviation`은 **소스에 없다.** 위 값은 관례적인 그리스어 축약을 채운 것이므로, 서비스의 표기 규칙에 맞춰 바꿔도 된다. NOT NULL이라 비워 둘 수는 없다.

**66행이 아니라 27행인 이유는 안전 문제다.**

`fetch_books()`는 `book_order BETWEEN start AND end`로 읽으므로, 27행만 있으면 기본 실행(`1..66`)이 자연히 신약 27권만 돈다. 66행을 넣으면 구약 39권 929장의 URL을 요청하게 되는데, 그 URL은 **404가 아니라 200**이고 빈 `div.passage`를 돌려준다. 그 페이지를 지금 파이프라인에 넣어 봤다.

```
$ studybible.info /Nestle/Genesis 1 을 현재 파이프라인으로 파싱
  뽑힌 절 2개:
     1 | "John 1:1"
     2 | "Peter 3:5"
```

**1절로 시작하므로 CLI의 방어를 통과한다.** 즉 66행을 넣으면 창세기 1장에 가짜 절 두 개가 커밋될 수 있다. 방어를 두 겹으로 둔다.

1. `bible_book` 27행 — 구약 URL을 **애초에 요청하지 않는다**(1차).
2. `_build_studybible_url()`의 `book_order >= 40` 검사 — 다른 경로로 요청이 들어와도 `ValueError`로 막는다(2차, [5.1](#51-scraperpy--소스-판별과-url)).

> **파서가 `[]` 대신 예외를 던져 막는 방법은 쓰지 않는다.** 소스별 파서가 `[]`를 돌려준다는 것은 "내 페이지가 아니니 다음으로 넘겨라"라는 뜻이고, 예외는 체인 계약을 깬다. 빈 페이지와 남의 페이지를 파서 안에서 구별할 방법이 없으므로 **요청 자체를 막는 것이 옳은 자리**다.

### 6.6 `bible_book_description` — `el`

`en/es/ja/ko/zh` 각 66행이 있고 그리스어(`el`)는 없다. 신약 27행만 필요하다. **본문 적재와는 독립이고 이 도구는 이 표를 읽지 않는다.** 넣지 않아도 적재는 완결된다.

---

## 7. 검증

`:tid`는 `N1904`의 `translation_id`다.

### 7.1 구조 검증

```sql
SELECT COUNT(DISTINCT b.id) AS books, COUNT(DISTINCT c.id) AS chapters, COUNT(v.id) AS verses
FROM public.bible_book b
JOIN public.bible_chapter c ON c.book_id = b.id
JOIN public.bible_verse v ON v.chapter_id = c.id
WHERE b.translation_id = :tid;
-- 기대: 27 / 260 / 7942
```

```sql
-- 장 수가 KJV와 다른 책 (기대: 0행)
SELECT b.book_order, COUNT(DISTINCT c.chapter_number) AS chapters
FROM public.bible_book b
JOIN public.bible_chapter c ON c.book_id = b.id
WHERE b.translation_id = :tid
GROUP BY 1
HAVING COUNT(DISTINCT c.chapter_number) <> (
  SELECT COUNT(DISTINCT c2.chapter_number)
  FROM public.bible_book b2 JOIN public.bible_chapter c2 ON c2.book_id = b2.id
  WHERE b2.translation_id = 10 AND b2.book_order = b.book_order);
```

```sql
-- 1절로 시작하지 않는 장 (기대: 0행)
SELECT b.book_order, c.chapter_number
FROM public.bible_book b
JOIN public.bible_chapter c ON c.book_id = b.id
JOIN public.bible_verse v ON v.chapter_id = c.id
WHERE b.translation_id = :tid
GROUP BY 1, 2 HAVING MIN(v.verse_number) <> 1;
```

### 7.2 KJV 대조 — −17 +2

```sql
WITH n AS (
  SELECT b.book_order, c.chapter_number, v.verse_number
  FROM public.bible_book b
  JOIN public.bible_chapter c ON c.book_id = b.id
  JOIN public.bible_verse v ON v.chapter_id = c.id
  WHERE b.translation_id = :tid
), k AS (
  SELECT b.book_order, c.chapter_number, v.verse_number
  FROM public.bible_book b
  JOIN public.bible_chapter c ON c.book_id = b.id
  JOIN public.bible_verse v ON v.chapter_id = c.id
  WHERE b.translation_id = 10 AND b.book_order >= 40
)
SELECT 'KJV에만' AS side, * FROM (SELECT * FROM k EXCEPT SELECT * FROM n) a
UNION ALL
SELECT 'N1904에만', * FROM (SELECT * FROM n EXCEPT SELECT * FROM k) b
ORDER BY 1, 2, 3, 4;
```

**기대 결과는 정확히 19행이다.**

```
KJV에만  (17)  40/17/21  40/18/11  40/23/14  41/7/16  41/9/44  41/9/46  41/11/26
               41/15/28  42/17/36  42/23/17  44/8/37  44/15/34  44/19/41  44/24/7
               44/28/29  45/16/24  47/13/14
N1904에만 (2)  64/1/15   66/12/18
```

**한 행이라도 다르면 적재를 다시 본다.** 총계(7,942)만 맞추면 안 된다 — −17 +2가 상쇄되는 조합은 얼마든지 있다.

### 7.3 구멍 검증 — 연속성 대신 기대 목록

이 역본에는 연속성 불변식이 없다([4.3](#43-함정-1-kjv에-있는-17절이-없다)). 대신 **구멍이 정확히 15곳인지**를 본다.

```sql
-- 번호가 끊긴 자리 (기대: 정확히 15행, 그리고 7.2의 'KJV에만' 목록의 부분집합)
WITH n AS (
  SELECT b.book_order, c.chapter_number, v.verse_number,
         LEAD(v.verse_number) OVER (PARTITION BY b.book_order, c.chapter_number
                                    ORDER BY v.verse_number) AS next_number
  FROM public.bible_book b
  JOIN public.bible_chapter c ON c.book_id = b.id
  JOIN public.bible_verse v ON v.chapter_id = c.id
  WHERE b.translation_id = :tid
)
SELECT book_order, chapter_number, verse_number + 1 AS missing_from, next_number - 1 AS missing_to
FROM n WHERE next_number IS NOT NULL AND next_number <> verse_number + 1
ORDER BY 1, 2, 3;
```

- **15행**이고 각 행이 한 절짜리 구멍이어야 한다(`missing_from = missing_to`).
- 나머지 두 개(행 19:41, 고후 13:14)는 **장 끝**이라 이 질의에 잡히지 않는다. 그것들은 [7.2](#72-kjv-대조--17-2)에서만 확인된다 — **그래서 두 질의를 모두 돌려야 한다**([4.4](#44-함정-2-구멍-없이-짧아지는-장이-둘-있다)).
- 같은 질의를 `translation_id = 23`(ASV)으로 돌리면 **16행**이 나오고, 그 목록은 위 15행에 요 5:4를 더한 것이다. 질의가 맞게 동작하는지 **적재 전에** 이렇게 확인할 수 있다.

### 7.4 문자 검증

```sql
-- 라틴 문자가 들어간 절 (기대: 0)  — 내비게이션·역본 안내가 새면 여기 걸린다
SELECT COUNT(*) FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid AND v.text ~ '[A-Za-z]';

-- 숫자가 들어간 절 (기대: 0)  — 절 번호가 본문에 남으면 여기 걸린다
SELECT COUNT(*) FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid AND v.text ~ '[0-9]';

-- 그리스 문자가 하나도 없는 절 (기대: 0)
SELECT COUNT(*) FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid AND v.text !~ '[Ͱ-Ͽἀ-῿]';

-- NFC 정규화를 적용했다면 (기대: 0)
SELECT COUNT(*) FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid AND v.text <> normalize(v.text, NFC);

-- 정규화가 실제로 걸렸는지 (기대: 1행 이상)  — 마태 1:1이 정상 입력과 매칭돼야 한다
SELECT v.verse_number, left(v.text, 30) FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid AND b.book_order = 40 AND c.chapter_number = 1
  AND v.text LIKE 'Βίβλος%';
```

마지막 질의가 **정규화를 하지 않으면 0행**이 된다. `Βίβλος`를 키보드로 입력하면 U+03AF가 들어가고 소스는 U+1F77을 쓰기 때문이다([4.6](#46-함정-4-본문의-271가-nfc가-아니다)).

> **문자 클래스는 콜레이션에 따라 달라진다.** PostgreSQL의 정규식 범위는 콜레이션 의존이라 `[A-Za-z]`가 악센트 문자까지 잡는 환경이 있을 수 있다. 이 서버(`en_US.UTF-8`)에서는 `'Βίβλος' ~ '[A-Za-z]'`가 거짓, `'Nestle' ~ '[A-Za-z]'`가 참, `'text' ~ '[Ͱ-Ͽἀ-῿]'`가 거짓임을 확인했다. **다른 서버에서 돌린다면 이 세 줄을 먼저 확인한다** — 라틴 문자 검사가 조용히 전량 통과하거나 전량 실패한다.

`normalize(text, NFC)`는 PostgreSQL 13 이상에서 쓸 수 있다(현재 서버는 **17.6**, 확인함). 그 아래 버전이면 이 검사는 파이썬 쪽에서 한다. `SELECT normalize(U&'\0387', NFC) = '·'`가 참이라는 것도 확인했다 — 즉 이 서버의 NFC가 [4.6](#46-함정-4-본문의-271가-nfc가-아니다)에서 설명한 그대로 접는다.

### 7.5 판본 검증 — Nestle 1904인지 확인

철자가 판본을 가른다. 두 소스를 같은 방법으로 센 실측값이다(**출현 횟수 / 그 낱말이 든 절 수**).

| 지표 | Nestle 1904 (studybible) | 공인본문 (eBible `grctr`) |
| --- | --- | --- |
| `Ἰωάν-` (ν 하나) | **132 / 128** | 0 / 0 |
| `Ἰωάνν-` (ν 둘) | **0 / 0** | 135 / 132 |
| `Μαθθα-` (θθ) | **5 / 5** | 0 / 0 |
| `Ματθα-` (τθ) | **0 / 0** | 5 / 5 |
| `Δαυείδ / Δαυεὶδ` | **59 / 54** | 0 / 0 |
| `Δαβίδ / Δαβὶδ` | **0 / 0** | 59 / 54 |

```sql
SELECT
  COUNT(*) FILTER (WHERE v.text ~ 'Ἰωάν[ηοε]')  AS iwan_single_nu,   -- 기대 128
  COUNT(*) FILTER (WHERE v.text ~ 'Ἰωάνν')      AS iwan_double_nu,   -- 기대 0
  COUNT(*) FILTER (WHERE v.text ~ 'Μαθθα')      AS maththa,          -- 기대 5
  COUNT(*) FILTER (WHERE v.text ~ 'Ματθα')      AS mattha,           -- 기대 0
  COUNT(*) FILTER (WHERE v.text ~ 'Δαυε[ίὶ]δ')  AS daueid,           -- 기대 54
  COUNT(*) FILTER (WHERE v.text ~ 'Δαβ[ίὶ]δ')   AS dabid             -- 기대 0
FROM public.bible_verse v
JOIN public.bible_chapter c ON c.id = v.chapter_id
JOIN public.bible_book b ON b.id = c.book_id
WHERE b.translation_id = :tid;
```

**`Ἰωάνης`(ν 하나)와 `Δαυείδ`가 함께 나오는 것이 지문이다.** 공인본문은 정확히 반대 조합을 쓴다(위 표). 현대 비평본문(NA28 등)은 `Ἰωάννης` + `Δαυίδ`를 쓰지만 **권리가 있어 대조하지 않았다** — 그 열은 실측이 아니므로 표에서 뺐다.

> **다른 eBible 그리스어 번들을 이 표에 넣으면 안 된다.** `grc-tisch`는 형태소 주석이 본문과 함께 들어 있어 같은 절에서 두 철자가 모두 잡히고(`Δαυείδ` 59 / `Δαβίδ` 59), `grcmt`는 악센트 표기가 달라 여섯 지표가 전부 0이 나온다. 두 번들은 **절 번호 구조 대조에만**([7.6](#76-제2-증인--구조-대조)) 쓴다.

### 7.6 제2 증인 — 구조 대조

낱말을 대조할 독립 증인이 없으므로([4.9](#49-함정-7-제2-증인이-존재하지-않는다)) **절 번호 집합**을 Tischendorf 8판(eBible `grc-tisch`, `public domain`)과 맞댄다. 사전 실측 결과다.

```
260장 중 절 번호 집합이 완전히 같은 장   254
                            다른 장       6
```

| 장 | Nestle에만 | Tischendorf에만 | 설명 |
| --- | --- | --- | --- |
| 마 21 | 44 | — | 티셴도르프가 21:44를 뺀다 |
| 눅 24 | 12, 40 | — | 이른바 서방 비삽입. Nestle은 `[[ ]]`로 실었다([4.5](#45-함정-3-편집-괄호가-본문-안에-있다)) |
| 요 1 | — | 52 | 티셴도르프가 1:51을 둘로 나눈다 |
| 요 5 | 4 | — | Nestle은 `< >`로 실었다 |
| 요 21 | 25 | — | 티셴도르프가 21:25를 뺀다 |
| 행 19 | — | 41 | Nestle이 19:40–41을 합쳤다([4.4](#44-함정-2-구멍-없이-짧아지는-장이-둘-있다)) |

**여섯 건 모두 판본 차이로 설명된다.** 설명되지 않는 차이가 하나라도 늘면 파싱 누락을 의심한다. Tischendorf 총계는 7,939절이고, 이는 eBible이 배포 목록에 적은 수와 같다 — 대조 스크립트가 맞게 동작한다는 확인이기도 하다.

### 7.7 잘못 적재 방지 검증

```bash
# 소스는 맞고 역본이 틀린 경우 — 막혀야 한다
BIBLE_TRANSLATION_TYPE=KJV python scrape_bible_to_db.py \
  --entry-url "https://studybible.info/Nestle/Matthew%201" --start-book 40 --end-book 40

# 역본은 맞고 소스가 틀린 경우 — 막혀야 한다
BIBLE_TRANSLATION_TYPE=N1904 python scrape_bible_to_db.py \
  --entry-url "https://studybible.info/KJV/Matthew%201" --start-book 40 --end-book 40
```

두 번째가 **`version` 토큰을 채워야 하는 이유**다([5.3](#53-scrape_bible_to_dbpy--역본-등록)). 비워 두면 `studybible.info`의 어떤 역본 URL이라도 `N1904`로 통과한다.

---

## 8. 테스트 설계

인라인 HTML 픽스처로 `tests/test_scraper.py`에 추가한다. **네트워크를 타는 테스트는 넣지 않는다.**

| 테스트 | 확인 |
| --- | --- |
| `studybible_source_is_recognised` | `get_source_name() == "studybible"`, `get_source_version() == "Nestle"`, `sleep_min >= 1.0` |
| `studybible_parses_verses` | 마커 사이 누적, 번호는 `title`에서, 본문에 번호가 남지 않음 |
| `studybible_drops_the_version_link` | 컨테이너 앞의 `Nestle (i)`가 1절에 붙지 않음 |
| `studybible_normalises_to_nfc` | U+0387과 U+1F77이 들어간 픽스처가 NFC로 저장됨. **`Βίβλος`가 U+03AF로 매칭됨** |
| `studybible_keeps_editorial_brackets` | `[[`, `]]`, `<`, `>`가 살아 있음 |
| `studybible_allows_a_numbering_gap` | 1,2,4 픽스처가 세 절 그대로 나옴 — `(omitted)`를 만들지 않음 |
| `studybible_rejects_a_page_that_mixes_chapters` | `title`의 장이 둘이면 `[]` + 경고 |
| `studybible_returns_empty_for_an_empty_passage_box` | `a.verse_ref`가 없으면 `[]` |
| `studybible_parser_returns_empty_for_other_sources` | bskorea·eBible·jpn.bible·wikisource 픽스처에 `[]` |
| `studybible_chapter_urls` | `%20` 인코딩, 27권 장 수, **book_order 39 이하에서 `ValueError`** |
| `studybible_book_names_match_the_shared_table` | `BIBLEGATEWAY_BOOK_NAMES[39:66]`을 그대로 쓴다는 사실을 고정 |

`tests/test_pipeline.py`의 `FakeScraper`에 `_is_studybible_source`·`_get_studybible_version`을 **실제 메서드에서 빌려 온다**. 직전 두 작업에서 이 단계를 빠뜨려 13개 테스트가 깨졌다.

---

## 9. 운영 계획

### 9.1 요청 간격과 소요

```
요청 수      260 (역본 1개, 장 단위)
전송량       10.7 MB  (장당 평균 42.3 KB, 실측)
지연         1.0 ~ 2.0초  → 약 4 ~ 9분
```

- `studybible.info/robots.txt`는 `Baiduspider`·`Amazonbot`·`Sogou`에만 `Crawl-delay: 30`을 두고 일반 UA에는 제한을 두지 않는다. 그래도 다른 소스와 같은 1.0초 하한을 쓴다.
- 참고: 원 전사본 사이트(Google Sites)를 골랐다면 장당 489 KB × 260 = **약 124 MB**가 된다. 12배 차이다.
- 429/5xx 재시도와 스로틀 배수는 기존 로직을 그대로 쓴다.

### 9.2 실행 예

```bash
# 파서만 확인 (DB 미접속)
python scrape_bible_to_db.py --test-book 40 --test-chapter 1 \
  --entry-url "https://studybible.info/Nestle/Matthew%201"

# 전권 (신약 27권)
BIBLE_TRANSLATION_TYPE=N1904 N1904_ENTRY_URL="https://studybible.info/Nestle/Matthew%201" \
  python scrape_bible_to_db.py --start-book 40 --end-book 66
```

`--start-book`을 생략해도 `bible_book`에 27행만 있으면 같은 결과다([6.5](#65-bible_book-27행--66행이-아닌-이유)).

### 9.3 갱신 문제

- 소스는 **`Version 2.2 (July 27, 2012)`로 고정**된 전사본이다. 개정될 가능성이 낮다.
- 그래도 삽입은 누락분만 채우므로 소스가 고쳐져도 재실행으로는 반영되지 않는다. 표시 문자열을 `scripts/check_translation_drift.py`로 감시하고, 바뀌면 **절 → 장 순서로 지우고** 다시 적재한다. 순서를 바꾸면 절이 고아가 된다.

---

## 10. 대안 경로

### 10.1 그리스어 신약 — 코드를 한 줄도 안 쓰는 길

**"Nestle 1904여야 한다"가 아니라 "퍼블릭 도메인 그리스어 신약이면 된다"라면 새 어댑터가 필요 없다.** eBible.org에 배포 표기가 `public domain`인 그리스어 신약이 6종 있고, 기존 eBible 어댑터가 그대로 동작한다.

| ID | 본문 | 절 수 |
| --- | --- | --- |
| `grc-tisch` | Tischendorf 8판 | 7,939 |
| `grctr` | Textus Receptus | 7,957 |
| `grcmt` | Robinson-Pierpont 다수본문 2018 | 7,957 |
| `grcbyz` | 1904년 총대주교판 | 7,958 |
| `grcsr` | Solid Rock | 7,961 |
| `grctcgnt` | 본문비평 주석판 | 7,954 |

`grc-tisch`의 USFM 머리말은 **`This text and its analysis are in the Public Domain. Copy freely.`** 라고 직접 적고 있다 — 이 문서가 조회한 것 중 표기가 가장 분명하다.

> **주의 — `grcbyz`는 Nestle 1904가 아니다.** 제목이 `1904 Patriarchal Greek New Testament`라 연도가 같지만, 이것은 **1904년 콘스탄티노폴리스 총대주교청판(Antoniades)** 으로 계보가 전혀 다르다. 검색으로 "1904 Greek NT"를 찾다가 이것을 집어 오기 쉽다.

`grctr`·`grcmt`가 KJV와 절 수(7,957)까지 같다는 점도 실무적으로는 크다. [4.3](#43-함정-1-kjv에-있는-17절이-없다)~[4.4](#44-함정-2-구멍-없이-짧아지는-장이-둘-있다)의 함정이 전부 사라진다.

**대신 잃는 것**: Nestle 1904는 20세기 전반 표준 비평본문이고 NA/UBS 계보의 직계 조상이다. 공인본문·다수본문과는 성격이 다르다. **판본이 목적이라면 이 대안은 답이 아니다.**

### 10.2 그리스어 구약 — 퍼블릭 도메인은 있다. 맞지 않을 뿐이다

**권리가 문제였던 적은 없다.** 권리 표기가 깨끗한 그리스어 구약이 셋 있고, 그중 하나는 이 문서가 만든 어댑터로 **코드 한 줄 없이 바로 읽힌다**.

| 소스 | 본문 | 권리 표기 | 어댑터 |
| --- | --- | --- | --- |
| `studybible.info/Brenton_Greek/` | Brenton 칠십인역 그리스어(1851) | 사이트 표기 `free of known copyright restrictions` | **이 문서의 어댑터 그대로** — 창세기 1장 31절 파싱 확인 |
| `ebible.org/grcbrent/` | 같은 Brenton | `public domain` | 기존 eBible 어댑터 |
| `ebible.org/grclxx/` | 정교회 칠십인역 | `public domain` | 기존 eBible 어댑터 |

**막는 것은 라이선스가 아니라 절 구분이다.** 둘을 KJV 격자와 대조한 실측이다.

| | 전체 | 비교한 장 | 절 수 다름 | 가장 심한 책 |
| --- | --- | --- | --- | --- |
| `grclxx` | 52권 1,088장 27,766절 | 931 | **296 (32%)** | 시편 139/150, 렘 36/52, 왕상 13/22 |
| `grcbrent` | 52권 1,104장 28,281절 | 931 | **302 (32%)** | 시편 138/150, 렘 36/52, 잠 15/31 |

`grcbrent`는 여기에 더해 **느헤미야가 독립된 책으로 없다**(에스드라 Β에 합쳐져 있어 `book_order` 16에 대응이 없다).

선택지는 셋이다.

1. **스키마를 바꾼다.** `bible_book`을 역본별 가변 정경으로 만들고, 이중 본문을 표현할 자리를 만든다. 지금까지의 계약을 다시 쓰는 일이다.
2. **현대 그리스어 역본을 쓴다 — 이것이 66권 표에 맞는 유일한 길이다.** Νεόφυτος Βάμβας(1850)는 히브리어 원전에서 옮겨 66권·마소라 번호를 따르고, CrossWire의 `GreVamvas` 모듈이 `Distribution License: Public Domain`으로 배포한다. **eBible에는 현대 그리스어(`ell`) 역본이 하나도 없고**, BibleGateway의 그리스어는 SBLGNT·THGNT 둘뿐이며 둘 다 저작권이 있고, **studybible.info에도 없다**(171개 버전 목록 확인). 웹에서 닿는 곳은 조회 범위 안에서 둘이다.
   - `stepbible.org/rest/bible/getBibleText/GreVamvas/Gen.1` — JSON 안에 HTML. 악센트가 살아 있다.
   - `newchristianbiblestudy.org/bible/greek-modern/…` — 평문 HTML이지만 **악센트가 전부 빠져 있다**(`Εν αρχη εποιησεν`). 본문 품질이 다르므로 그대로 쓰면 안 된다.

   즉 **어댑터를 새로 써야 하고, 그 전에 두 소스의 판본 동일성부터 확인해야 한다.** 이 문서의 범위 밖이다.
3. **칠십인역을 별도 역본으로 넣되 구조 불일치를 감수한다.** 권하지 않는다. 시편 139장이 어긋난 채로 들어간다.

> **`studybible.info/Vamvas/`는 없다.** 요청하면 [6.5](#65-bible_book-27행--66행이-아닌-이유)에서 본 그 응답 — 200에 빈 `div.passage` — 이 돌아온다. 새 파서는 `[]`를 돌려주지만 일반 체인이 이어받아 `John 1:1`·`Peter 3:5` 두 절을 만들어 낸다. 다른 역본 이름으로 재확인된 함정이다.

### 10.3 Rahlfs를 반드시 써야 한다면

권리 쪽만 정리하면 이렇다.

1. **CCAT에 서면 동의를 신청한다.** 사용자 서약서 (1)항이 요구하는 절차다. 소유자/인코더 목록은 CCAT의 `readme` 문서에 있다.
2. **Deutsche Bibelgesellschaft에 문의한다.** 현재 판매 중인 것은 Rahlfs-Hanhart 2006년판이며 권리 관계가 별개다.
3. **1935년 인쇄본 스캔에서 새로 전사한다.** CCAT/TLG 계보를 벗어나는 유일한 방법이지만 스크래핑이 아니다.

**어느 쪽을 택해도 [1.4](#14-권리를-다-풀어도-lxx는-이-저장소의-66권-표에-들어가지-않는다)의 구조 문제는 그대로 남는다.**

---

## 11. 구현 순서

1. `scraper.py`에 상수·`_is_studybible_source`·`_get_studybible_version`·`_build_studybible_url`·`_discover_chapter_urls_for_studybible`을 넣고, `get_source_name`/`get_source_version`/`_build_chapter_url`/`discover_chapter_urls_for_book`/`__init__` 지연 하한에 분기를 더한다.
2. `_extract_verses_from_studybible_page`를 쓰고 체인의 wikisource 뒤에 끼운다.
3. `tests/test_scraper.py`에 [8장](#8-테스트-설계)의 테스트를, `tests/test_pipeline.py`의 `FakeScraper`에 두 메서드를 더한다. **여기까지 하고 `pytest -q`가 전부 통과해야 한다.**
4. `scrape_bible_to_db.py`의 세 표(`ENTRY_URL_ENV_BY_TRANSLATION_TYPE`, `TRANSLATION_TYPES_BY_LANGUAGE_CODE`, `TRANSLATION_SOURCE_REQUIREMENTS`)에 `N1904`를 등록한다.
5. `--test-book 40 --test-chapter 1`과 `--test-book 41 --test-chapter 16`(막 16장, `[[ ]]`), `--test-book 64 --test-chapter 1`(요삼, 15절)로 **DB 없이** 확인한다.
6. DB 준비: CHECK 둘([6.2](#62-language_code-check--그리스어-코드-추가), [6.3](#63-translation_type-check--34번째-값)) → `bible_translation` 1행 → `bible_book` 27행.
7. [7.7](#77-잘못-적재-방지-검증)의 두 명령이 **실패하는지** 먼저 본다.
8. 마태복음만(`--start-book 40 --end-book 40`) 적재하고 [7.1](#71-구조-검증)·[7.4](#74-문자-검증)를 돌린다. 마 17:21 구멍과 `Βίβλος` 매칭을 눈으로 확인한다.
9. 전권 적재 후 [7장](#7-검증) 전체를 돌린다.
10. `CLAUDE.md`·`README.md`의 소스 표·파서 체인·엔트리 URL 목록·파서 계약을 갱신한다.

---

## 12. 리스크

### 리스크 1. 구약을 어떻게든 넣으려고 한다 (가장 큼)

요청이 "구약+신약"이므로 신약만 들어간 상태가 미완으로 보인다. 그러나 [1.4](#14-권리를-다-풀어도-lxx는-이-저장소의-66권-표에-들어가지-않는다)의 296개 장 불일치는 소스를 바꿔서 사라지지 않는다. **장 수만 맞춰 밀어 넣으면 시편 139장이 다른 시편을 가리키는 DB가 된다.** 총계 검사·연속성 검사·빈 절 검사를 전부 통과하면서.

### 리스크 2. `(omitted)` 마커를 넣고 싶어진다

14개 장의 구멍이 눈에 거슬려 하드코딩 목록으로 채우려는 유혹이 생긴다. 그러면 소스가 주지 않은 15개 행이 DB에 들어가고, 나중에 파서가 고장 나 절을 놓쳐도 같은 모양이 되어 구별할 수 없다. **구멍을 남기고 [7.3](#73-구멍-검증--연속성-대신-기대-목록)으로 검사한다** — ASV가 이미 같은 방식으로 16곳을 담고 있다([4.3](#43-함정-1-kjv에-있는-17절이-없다)).

### 리스크 3. NFC를 잊는다

기본값으로 두면 전량 검사(라틴 문자 0, 숫자 0, 그리스 문자 존재)를 **전부 통과한다.** 드러나는 곳은 서비스의 검색창이고, 그때는 이미 적재가 끝나 있다. [7.4](#74-문자-검증) 마지막 질의를 반드시 넣는다.

### 리스크 4. 행 19장·고후 13장을 놓친다

절 수가 KJV보다 하나 적은데 번호는 연속이다. **KJV 대조 없이는 어떤 검사도 잡지 못한다.**

### 리스크 5. `grcbyz`를 Nestle 1904로 오인한다

eBible의 `1904 Patriarchal Greek New Testament`는 연도만 같은 다른 판본이다([10.1](#101-그리스어-신약--코드를-한-줄도-안-쓰는-길)). 기존 eBible 어댑터로 곧장 적재되기까지 해서 더 위험하다. [7.5](#75-판본-검증--nestle-1904인지-확인)의 철자 지표로 걸러진다.

### 리스크 6. 구약 URL이 200을 돌려준다

`bible_book`을 66행으로 넣으면 가짜 절이 커밋될 수 있다([6.5](#65-bible_book-27행--66행이-아닌-이유)). 27행 + `ValueError` 두 겹으로 막는다.

### 리스크 7. 클래스명이 바뀐다

`div.passage`·`a.verse_ref`는 의미 있는 이름이라 안정적으로 보이지만, 사이트 개편으로 바뀌면 파서가 `[]`를 돌려주고 체인이 일반 파서로 넘어간다. 그때 나오는 것이 [4.2](#42-dom-구조)에서 본 `Samuel 7:13`이다. **1절로 시작하지 않으므로 CLI 방어에 걸려 기록되지는 않지만**, 로그를 보지 않으면 "장을 건너뛰었다"로만 남는다. 재적재 전에 [7.1](#71-구조-검증)의 260장 확인이 필수다.

### 리스크 8. BibleHub로 소스를 바꾼다

DOM이 가장 깨끗해서 유혹이 크다. **이용약관 6(d)가 상용 사용을 금지한다**([1.5](#15-후보-소스-비교)). 본문 자체가 퍼블릭 도메인인 것과 그 사이트를 통해 얻는 것은 별개다.

### 리스크 9. `language_code` CHECK 재작성에서 값을 빠뜨린다

`translation_type`과 달리 이 제약은 지금까지 손댄 적이 없다. 재작성할 때 기존 7개 값을 그대로 유지해야 한다. 하나라도 빠지면 그 언어 역본의 이후 삽입이 막힌다.

---

## 12.5 적재 결과 (실측)

구현하고 적재한 뒤 [7장](#7-검증)을 그대로 돌린 결과다. **이 문서가 예측한 값이 전부 맞았다.**

```
translation_id=41  N1904  Η Καινή Διαθήκη (Nestle 1904)  grc  translation_order=37
27권 / 260장 / 7,942절

7.1  장 수가 KJV와 다른 책 0 · 1절로 시작하지 않는 장 0
7.2  KJV에만 17개 / N1904에만 2개 — 기대 목록과 완전 일치
7.3  구멍 15개, 전부 한 절짜리, 전부 7.2의 부분집합 (같은 질의로 ASV는 16행)
7.4  라틴 문자 0 · 숫자 0 · 그리스 문자 없는 절 0 · NFC 아닌 절 0 · 빈 절 0
     정상 입력한 'Βίβλος'로 마태 1:1 매칭됨
7.5  Ἰωάν- 128 / Ἰωάνν- 0 / Μαθθα- 5 / Ματθα- 0 / Δαυείδ 54 / Δαβίδ 0
     편집 괄호 [ ] 8절 · < > 5절
7.6  Tischendorf와 절 번호 집합이 같은 장 254 / 다른 장 6 — 여섯 건 모두 판본 차이
```

재실행은 `inserted=0, skipped=25`로 총계가 변하지 않는다(유다서로 확인).

> **이후 변경 (2026-09-27 조회).** 위 첫 줄의 `grc`는 적재 당시 값이다. 지금 N1904 행의 `language_code`는 `el`이고 CHECK 목록도 `grc` 대신 `el`을 담고 있다. 본문 행은 그대로다(27권/260장/7,942절). 코드·README·CLAUDE.md를 `el`로 맞췄다([5.4](#54-기존-동작이-바뀐다--언어-코드)).

### 구현하며 드러난 것

- **`tests/test_pipeline.py`의 `FakeScraper`에 두 메서드를 빌려 오는 단계를 또 빠뜨리면 13개 테스트가 깨진다.** [8장](#8-테스트-설계)에 적어 둔 그대로 깨졌고, `_is_studybible_source`·`_get_studybible_version`을 더해 복구했다. 세 번째 반복이다.
- **NFC 테스트는 눈으로 읽을 수 없다.** 픽스처의 U+1F77과 단언의 U+03AF가 화면에서 같은 글자로 보여서, 누가 다시 타이핑하면 테스트가 조용히 무력화된다. 코드포인트를 `\u` 이스케이프로 적고 이름을 붙였다. 정규화를 빼면 실제로 실패하는지도 확인했다.
- **`.env`가 `BIBLE_TRANSLATION_ID=2`로 고정돼 있다.** `.env`는 `setdefault()`로 읽히므로 셸 환경변수가 이긴다. 적재는 `BIBLE_TRANSLATION_ID=41`을 셸에서 주고 `--entry-url`을 함께 넘겨야 한다([9.2](#92-실행-예)).
- **CHECK 제약은 손으로 다시 적지 않았다.** `pg_get_constraintdef()`에서 기존 33개·7개 값을 읽어 뒤에 붙이고, 읽은 개수가 적으면 멈추도록 했다([6.2](#62-language_code-check--그리스어-코드-추가)의 리스크 9). 드라이런에서 identity 시퀀스가 한 번 소모되어 `translation_id`가 40이 아니라 **41**이 됐다 — `sync_identity_sequences()`가 시작할 때 정렬하므로 문제가 되지 않는다.
- **적재 시간은 260장에 약 9분**이었다(장당 약 2초).

---

## 13. 결론

**요청 조합의 절반만 채택한다.**

| | 판정 | 이유 |
| --- | --- | --- |
| **신약 — Nestle 1904** | **채택** | 권리가 관할을 가리지 않고 깨끗하다. 전자본 표기도 분명하다. 27권 260장 7,942절이 66권 표의 40~66번에 그대로 들어간다 |
| **구약 — Rahlfs LXX 1935** | **불채택** | (가) 쓸 수 있는 전자본이 전부 CCAT 계보이고 **상용 사용이 서면 동의 사항**이다. (나) 권리를 풀어도 칠십인역은 **931장 중 296장이 이 스키마의 격자와 맞지 않는다** |

요청문의 마지막 문장 — "어떠한 라이선스 고지 의무나 법적 분쟁 리스크 없이 상용에 안전하게 사용 가능" — 은 **Nestle 1904에는 그대로 맞고, Rahlfs 1935에는 인쇄본에만 맞는다.** 인쇄본이 자유롭다는 것과 내려받을 수 있는 파일이 자유롭다는 것은 다른 문장이며, Rahlfs에서는 그 둘이 갈라진다.

그리스어 신약이 목적이고 판본은 상관없다면 **코드를 한 줄도 쓰지 않는 길이 있다**([10.1](#101-그리스어-신약--코드를-한-줄도-안-쓰는-길)). 그리스어 구약이 목적이라면 **스키마 변경 없이는 답이 없다**([10.2](#102-그리스어-구약--퍼블릭-도메인은-있다-맞지-않을-뿐이다)).

> **구약 보류 (결정).** 신약 적재 후 "구약도 코이네로 넣어야 하지 않느냐"는 검토가 있었다. 권리는 걸림돌이 아니다 — `studybible.info/Brenton_Greek/`는 이 문서의 어댑터로 이미 읽히고 eBible에도 퍼블릭 도메인 칠십인역이 둘 있다([10.2](#102-그리스어-구약--퍼블릭-도메인은-있다-맞지-않을-뿐이다)). **구조가 어긋나므로 넣지 않기로 했다.** 재개하려면 [10.2](#102-그리스어-구약--퍼블릭-도메인은-있다-맞지-않을-뿐이다)의 세 선택지 중 하나를 먼저 정해야 한다.
