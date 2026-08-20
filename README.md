# proposalkit (`ppsk`)

`proposalkit`은 반복해서 작성하는 제안서의 핵심 주장, 근거, 수치, 태그를 파일 기반으로 관리하기 위한 CLI 도구입니다.

같은 회사 소개나 핵심 주장이 여러 제안서에 복사되면 시간이 지나면서 문서마다 표현과 수치가 조금씩 달라집니다. `ppsk`는 제안서를 작은 블록으로 나누고, 검증 가능한 수치는 `facts.yaml`에 따로 모아 이런 drift를 줄이는 것을 목표로 합니다.

현재 구현된 명령은 `init`, `import`, `index`입니다. `check`, `build`, `verify` 등은 설계 문서에 남아 있는 다음 단계 기능입니다.

---

## 설치

```bash
git clone <this-repo>
cd proposalkit
pip install -e .
ppsk --version
```

요구 사항:

- Python 3.11 이상
- Windows, macOS, Linux
- 런타임 의존성: `PyYAML`

개발 환경은 다음처럼 설치합니다.

```bash
pip install -e ".[dev]"
pytest -q
```

---

## 빠른 시작

```bash
mkdir my-proposals
cd my-proposals

ppsk init .
ppsk import archive/2025-plan.md --project ad-samd
ppsk index
ppsk index --project ad-samd
```

### 명령 요약

| 명령 | 설명 |
|---|---|
| `ppsk init [path]` | 제안서 콘텐츠 저장소의 기본 디렉터리와 템플릿 파일을 만듭니다. 기존 파일은 덮어쓰지 않습니다. |
| `ppsk import <file>` | 기존 Markdown 또는 텍스트 문서를 heading 기준으로 나누어 `import/<name>/`에 블록 후보를 만듭니다. |
| `ppsk index [path]` | `core/`, `evidence/`, `strategy/`의 frontmatter를 읽어 `INDEX.md`를 생성합니다. |

`ppsk import`는 최종 블록을 자동으로 확정하지 않습니다. 가져온 결과는 후보이며, 사람이 `layer`, `summary`, `facts_used`, `tags`, `projects`를 확인한 뒤 필요한 위치로 옮기는 흐름을 전제로 합니다.

---

## 기본 개념

### 블록

블록은 하나의 주장이나 근거를 담은 Markdown 파일입니다. `core/`, `evidence/`, `strategy/` 아래에 저장하며, 파일 상단에는 YAML frontmatter를 둡니다.

```yaml
---
id: ad-core-claim
layer: thesis                  # identity | thesis | evidence | strategy
status: active                 # draft | active
editable: free                 # strict | free
last_verified: 2026-07-10
facts_used: [pilot_n_2025]
tags: [기술체계, 개인화]
projects: [ad-samd]            # 비우면 모든 프로젝트에서 공용
summary: 기존 개인화는 사용자 상태 조절에 머물고, 우리는 훈련 소재를 개인화한다.
---
```

블록은 세 가지 축으로 분류합니다.

| 축 | 질문 | 역할 |
|---|---|---|
| `layer` | 이 내용은 무엇인가? | 주장, 근거, 전략의 위치를 정합니다. |
| `tags` | 어떤 주제와 관련 있는가? | 검색과 매칭에 사용합니다. |
| `projects` | 어느 사업에 들어가도 되는가? | 프로젝트 전용 블록이 다른 제안서에 섞이지 않도록 막습니다. |

### fact

검증 가능한 수치와 출처는 본문에 직접 쓰지 않고 `facts.yaml`에 모읍니다. 본문에서는 `{{fact_id}}`로 참조합니다.

```yaml
pilot_n_2025:
  value: "참여자 67명"
  num: 67
  source: "2025 파일럿 결과보고서 p.7"
  verified: 2026-06-01
  stability: volatile          # fixed | volatile
  recheck_days: 90

sessions_per_user:
  expr: "total_sessions_2025 / pilot_n_2025"
  format: "1인당 {v:.1f}회"
```

파생 fact는 `expr`와 `format`으로 정의합니다. 계산식은 임의 코드를 실행하지 않고 제한된 산술식만 허용하는 방향으로 설계되어 있습니다.

### claim number

제안서 본문에 등장하는 주장성 수치는 fact로 관리하는 것이 원칙입니다. 날짜, 순번, 기간, 단계처럼 구조를 설명하는 숫자는 예외가 될 수 있습니다.

```markdown
파일럿 참여자는 {{pilot_n_2025}}였고, 평균 {{sessions_per_user}}를 수행했다.
1차년도에는 {{!12개월}} 동안 TRL {{!6}}단계까지 도달한다.
```

`{{!...}}`는 fact가 아닌 숫자임을 명시하는 면제 마커입니다.

---

## 저장소 구조

`ppsk init`이 만드는 콘텐츠 저장소는 도구 자체의 소스 저장소가 아니라 제안서 재료를 담는 작업 공간입니다.

```text
facts.yaml            # 모든 수치의 단일 소스
tags.yaml             # 태그 사전과 alias
projects.yaml         # 프로젝트 등록부
core.lock             # core 파일별 해시, 이후 단계에서 사용 예정
docs/rules.md         # 작성 규칙 원본
core/
  identity/           # 회사, 팀, 보유 자산
  thesis/             # 문제 정의, 핵심 주장
evidence/
  research/
  validation/
  market/
strategy/
  active/
  archive/
templates/angles/     # rnd.md, ir.md, commercialization.md
proposals/<slug>/     # 개별 제안서 작업물
archive/              # 과거 제안서 원본
import/               # 가져오기 결과 후보
```

핵심 원칙은 원본을 한 곳에 두는 것입니다. 프로젝트별 변형 텍스트를 별도로 저장하지 않고, 공용 블록과 프로젝트 전용 블록을 명시적으로 구분합니다.

---

## 설계 원칙

1. **선언은 약속이고, 검증은 코드가 한다.** frontmatter에 적힌 규칙은 사람이 지키는 규약이고, 실제 방어선은 `ppsk check` 같은 결정론적 검증기로 둡니다.
2. **반복 텍스트를 저장하지 않는다.** angle별 파생 본문을 저장하면 원본 변경이 조용히 누락되기 쉽습니다.
3. **수치는 본문에서 분리한다.** 같은 값은 `facts.yaml`에 한 번만 두고, 본문에서는 참조합니다.
4. **프로젝트와 태그를 섞지 않는다.** 태그는 주제 분류이고, 프로젝트는 포함 가능 여부를 결정하는 필터입니다.
5. **경고는 흐름을 멈추지 않고, 오류만 멈춘다.** 확인이 필요한 상태는 보이게 만들되, 작업을 막는 조건은 명확해야 합니다.

---

## 개발

```bash
pip install -e ".[dev]"
pytest -q
```

주요 코드 위치:

| 경로 | 역할 |
|---|---|
| `ppsk/__main__.py` | CLI 진입점과 명령 등록 |
| `ppsk/commands/init.py` | 기본 저장소 골격 생성 |
| `ppsk/commands/import_.py` | 기존 문서를 블록 후보로 분리 |
| `ppsk/commands/index.py` | 블록 frontmatter를 모아 `INDEX.md` 생성 |
| `ppsk/blocks.py` | 블록 로딩과 frontmatter 처리 |
| `ppsk/facts.py` | fact 로딩과 파생 fact 계산 |
| `ppsk/numbers.py` | 주장성 수치 탐지 |
| `tests/` | 현재 구현된 동작의 테스트 |

관련 문서:

| 문서 | 내용 |
|---|---|
| `docs/plan.md` | 전체 설계와 결정 기록 |
| `docs/devplan.md` | 구현 계획과 작업 단위 |
| `docs/process.md` | 작업 진행 상태 |

커밋 메시지에는 관련 작업 id를 붙이는 방식을 권장합니다.

```text
feat: import command splits markdown by h1/h2 (T-09)
```
