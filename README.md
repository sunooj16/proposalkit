# proposalkit (`ppsk`)

제안서를 **블록과 fact로 쪼개 관리하고, 조립 결과를 기계로 검증하는** CLI 도구.

같은 회사가 같은 주장을 여러 제안서에 반복해서 쓴다. 그런데 매번 복사·수정하다 보면
core 주장이 문서마다 갈라지고, 작년에 쓴 숫자가 올해 제안서에 그대로 들어간다.
`ppsk`는 그 두 가지를 구조로 막는다.

- **주장은 한 곳에만 있다.** `core/`에 원본 하나. 앵글별 파생본을 저장하지 않는다.
- **수치는 `facts.yaml`이 단독으로 소유한다.** 본문에는 `{{fact_id}}`로만 쓴다.
- **선언은 부탁이고 `ppsk check`이 강제다.** frontmatter에 `editable: strict`라고 적어도
  그건 부탁이다. 실제 방어선은 환경과 무관하게 도는 검증기 하나뿐이다.

LLM 호출 없음. 네트워크 접근 없음. 파일시스템만 만진다. 의존성은 PyYAML 하나.

---

## 설치

```bash
git clone <this-repo>
cd proposalkit
pip install -e .
ppsk --version
```

Python 3.11+. Windows / macOS 동일 동작.

---

## 지금 되는 것

**1단계 — 임포트로 씨앗 만들기.** 과거 제안서에서 블록 라이브러리를 뽑아내는 경로가 동작한다.

```bash
mkdir my-proposals && cd my-proposals
ppsk init .                                   # 골격 + 규약 + 빈 어휘 파일
ppsk import archive/2025-plan.md --project ad-samd
ppsk index                                    # INDEX.md 생성
ppsk index --project ad-samd                  # 그 프로젝트에서 보이는 블록만
```

| 커맨드 | 하는 일 |
|---|---|
| `ppsk init [path]` | 디렉터리 골격, `docs/rules.md`, 한 줄 포인터 `CLAUDE.md`/`AGENTS.md`, 빈 `facts.yaml`/`tags.yaml`/`projects.yaml`, angle 템플릿 3종. 기존 파일은 덮지 않아 재실행이 안전하다 |
| `ppsk import <file> [--project <id>] [--name <n>] [--force]` | 원본 문서를 h1~h2 헤딩 기준으로 잘라 `import/<name>/`에 블록 후보 + `facts.candidates.yaml` + `tags.candidates.txt`를 만든다. **분해하지 않는다** — 계층 판정과 병합은 사람이 한다 |
| `ppsk index [path] [--project <id>] [-o <file>]` | frontmatter를 모아 `INDEX.md`를 만든다. 에이전트는 인덱스를 먼저 읽고 필요한 파일만 연다 |

라이브러리로는 다음이 준비돼 있다 (커맨드는 아직 없다).

- `ppsk.blocks` — frontmatter 파싱, 블록 스캔, 본문 해시(CRLF 정규화 포함)
- `ppsk.facts` — `facts.yaml` / `facts/` 로더, 파생 fact 평가(AST 화이트리스트)
- `ppsk.tags` — 통제 어휘 + alias 정규화
- `ppsk.projects` — 프로젝트 등록부와 소속 판정
- `ppsk.numbers` — 주장성 수치 탐지

## 아직 안 되는 것

`new`, `collect`, `check`, `verify`, `build`, `core-update`, `review`는 미구현이다.
진행 상황은 [`docs/process.md`](docs/process.md)가 단일 소유자다.

---

## 데이터 모델

### 블록

`core/`·`evidence/`·`strategy/` 아래 마크다운 파일 하나가 블록 하나다.

```yaml
---
id: ad-core-claim
layer: thesis                  # identity | thesis | evidence | strategy
status: active                 # draft | active — draft 사용은 경고
editable: free                 # strict | free — strict 는 축자 인용 강제
last_verified: 2026-07-10
facts_used: [pilot_n_2025]
tags: [기술난제, 개인화]         # tags.yaml 의 정규형
projects: [ad-samd]            # 생략하면 전 프로젝트 공용
summary: 기존 개인화는 난이도 조절에 머물러 있고 우리는 훈련 소재를 개인화한다
---
```

**세 개의 축으로 자른다.**

| 축 | 질문 | 쓰임 |
|---|---|---|
| 계층 `layer` | 내용이 무엇인가 | 권한과 신선도 주기 |
| 태그 `tags` | 얼마나 관련 있는가 | 앵글 매칭 — **정렬** |
| 프로젝트 `projects` | 여기 들어가도 되는가 | 사업 간 누출 — **차단** |

프로젝트를 태그로 표현하지 않는 이유가 여기 있다. 태그는 가중치로 순위를 매기는 부드러운
장치이고, 프로젝트는 A 사업 실적이 B 사업 제안서에 새는 것을 막는 단단한 장치다.
`ppsk collect`는 정렬하기 **전에** 프로젝트로 먼저 거른다.

### fact

모든 주장성 수치는 `facts.yaml`에 등록하고 본문에는 `{{id}}`로 쓴다.

```yaml
pilot_n_2025:
  value: "참여자 67명"
  num: 67                     # 파생 계산에 쓰일 때만 필요
  source: "2025 파일럿 결과보고서 p.7"
  verified: 2026-06-01
  stability: volatile         # fixed | volatile — fixed 는 영구 통과
  recheck_days: 90

sessions_per_user:            # 파생 fact
  expr: "total_sessions_2025 / pilot_n_2025"
  format: "1인당 {v:.1f}회"
```

파생 fact는 `verified`·`stability`·`recheck_days`·`source`를 **선언할 수 없다**. 입력에서
상속한다 — 확인일은 입력 중 가장 오래된 것, 재확인 기한은 가장 이른 것(`fixed` 입력은 제외).
같은 값에 소유자가 둘 생기는 것을 막는다.

`expr`는 `eval()`로 실행하지 않는다. `ast.parse` 후 사칙연산과 숫자 상수, 등록된 비파생
fact 참조만 통과시키고 직접 계산한다. 파생의 파생은 금지(깊이 1).

### 검사 대상 숫자

주장성 수치만 잡는다. 날짜·순번·기간·단계·연령은 주장이 아니므로 등록 대상이 아니다.

```
잡는다    3,200억 원 · 약 100만 명 · 12.5% · 약 5~10% · 평균 25만~30만 원 · 132억 달러
안 잡는다  2026-08-01 · 제 3장 · 3개월 · TRL 6 · 4단계 · 65세 · 1차 시도 · [11, 12]
```

정말 예외라면 `{{!17개 기관}}`으로 면제한다. 면제는 리포트에 건수로 남는다.

이 정규식들은 실제 제안서 2건에서 조정했고, `tests/test_numbers.py`의 `CORPUS`가 그
정의의 실체다. 고칠 때는 **실제 문장을 먼저 테스트에 추가한다**.

---

## 리포지토리 구조

`ppsk init`이 만드는 것 — 도구 리포지토리가 아니라 **제안서 콘텐츠 리포지토리**다.

```
facts.yaml            # 모든 수치의 단일 소유자
tags.yaml             # 통제 어휘 + alias
projects.yaml         # 프로젝트 등록부
core.lock             # 자동 생성 — core/ 파일별 해시 (미구현)
docs/rules.md         # 규약 원본 하나. CLAUDE.md·AGENTS.md 는 한 줄 포인터
core/
  identity/           # 회사·팀·보유자산
  thesis/             # 문제 정의, 기존 한계, 핵심 주장, 역량 근거
evidence/
  research/ validation/ market/
strategy/
  active/ archive/
templates/angles/     # rnd.md, ir.md, commercialization.md
proposals/<slug>/     # brief · angle · draft · final · report · deviations
archive/              # 과거 제안서 원본
import/               # 승인 전 격리 구역
```

**도구와 콘텐츠를 같은 리포지토리에 두지 말 것.** 회사 자료와 도구 이력이 섞인다.

---

## 설계 원칙

1. **불변성은 저장 속성이 아니라 검증 대상이다.** frontmatter의 선언은 부탁이고
   `ppsk check`이 강제다. 에이전트는 리포지토리 전체에 쓰기 권한을 갖는다.
2. **파생 텍스트를 저장하지 않는다.** 앵글별 파생본을 만들면 원본이 바뀔 때 조용히 낡는다.
   git diff는 그것을 잡아주지 않는다.
3. **결정을 미룰 때는 마이그레이션 비용을 먼저 0으로 만든다.** `facts.yaml` 하나로 시작하되
   `facts/` 디렉터리도 읽는다 — 분할은 파일 이동 한 번이고 본문 수정이 없다.
4. **검증은 결정론적이어야 한다.** 검증까지 LLM에 맡기면 초안을 쓴 것과 같은 판단이 같은
   실수를 통과시킨다.
5. **경고와 알림은 흐름을 멈추지 않는다.** 멈추는 것은 error뿐이다.

---

## 개발

```bash
pip install -e ".[dev]"
pytest -q
```

테스트는 **결정론적 판정 로직만** 다룬다 — 파생 fact 평가, 숫자 클래스 정규식, 검증 규칙,
정렬 재현성. 디렉터리 생성이나 콘솔 출력 포맷은 테스트하지 않는다.

| 문서 | 역할 |
|---|---|
| [`docs/plan.md`](docs/plan.md) | 기획 — 무엇을, 왜. 충돌 시 이 문서가 우선 |
| [`docs/devplan.md`](docs/devplan.md) | 개발 계획 — 어떤 파일에 어떤 함수로 |
| [`docs/process.md`](docs/process.md) | 작업 보드 — **작업 상태의 단일 소유자** |

작업 하나가 끝나면 커밋 하나. 커밋 메시지 끝에 작업 id를 붙인다 (`feat: ... (T-09)`).
완료된 작업이 바뀌면 되돌리지 않고 새 id로 개정 항목을 세운다.
