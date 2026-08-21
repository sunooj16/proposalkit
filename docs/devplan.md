# proposalkit 개발 계획 (devplan)

`docs/plan.md`(기획)를 코드로 옮기기 위한 명세. 기획이 "무엇을/왜"라면 이 문서는 **"어떤 파일에 어떤 함수로"**다.
기획과 충돌하면 기획이 우선한다.

---

## 0. 기술 선택

| 항목 | 선택 | 이유 |
|---|---|---|
| 언어 | Python 3.11+ | Windows/macOS 동일 동작, 표준 라이브러리로 해시·정규식·날짜 전부 해결 |
| 의존성 | `PyYAML` **하나** | frontmatter/facts/tags가 전부 YAML. 직접 파서 작성은 손해 |
| CLI 파서 | `argparse` (stdlib) | 서브커맨드 10개 수준에 Typer/Click 불필요 |
| 배포 | `pyproject.toml` + `pip install -e .` → `ppsk` 콘솔 스크립트 | PowerShell/bash 양쪽에서 `ppsk` 한 단어 |
| 테스트 | `pytest` + `tmp_path` 픽스처 | 검증기가 핵심 자산이므로 여기만 제대로 테스트 |

LLM 호출 없음(기획 원칙 4). 네트워크 접근 없음. 파일시스템만 만진다.

---

## 1. 코드 구조

```
ppsk/
├── __init__.py
├── __main__.py          # argparse 서브커맨드 등록 → cmd_* 디스패치
├── model.py             # Block, Fact, Finding 데이터클래스
├── facts.py             # facts.yaml / facts/ 로더, 파생 fact 평가
├── tags.py              # tags.yaml 로더, alias 정규화
├── projects.py          # projects.yaml 로더, 소속 판정 (하드 필터)
├── blocks.py            # frontmatter 파싱, core/ evidence/ strategy/ 스캔
├── numbers.py           # 주장성 수치 탐지 정규식
├── lock.py              # core.lock 생성·대조, deviations 기록
├── check.py             # 검증 규칙 전체 → Finding 목록
├── render.py            # {{fact}} 치환, 인라인 마커, report.md 생성
├── scaffold.py          # init / new / import 템플릿
└── commands/            # cmd_init, cmd_index, ... 각 파일 1커맨드
tests/
└── test_*.py
templates/               # scaffold가 복사하는 원본 (패키지 데이터)
```

**레이어 규칙:** `commands/`는 입출력과 종료코드만 담당한다. 판정 로직은 전부 `check.py` 등 순수 함수에 두고 데이터를 인자로 받는다. 테스트가 CLI를 거치지 않게 하려는 것.

---

## 2. 핵심 자료구조

```python
@dataclass
class Block:
    path: Path              # 리포지토리 루트 기준 상대경로
    id: str
    layer: Literal["identity", "thesis", "evidence", "strategy"]
    status: Literal["draft", "active"]
    editable: Literal["strict", "free"]
    last_verified: date | None
    facts_used: list[str]
    tags: list[str]         # 정규형으로 치환된 상태
    projects: list[str]     # 빈 목록 = 전 프로젝트 공용
    summary: str
    body: str
    sha: str                # sha256(정규화된 body), core.lock·generated_from 공용

@dataclass
class Fact:
    id: str
    value: str | None       # 기본 fact
    num: float | None
    source: str | None
    verified: date | None
    stability: Literal["fixed", "volatile"] | None
    recheck_days: int | None
    expr: str | None        # 파생 fact
    format: str | None
    projects: list[str]     # 빈 목록 = 공용. facts 파일의 _project 를 상속

    @property
    def derived(self) -> bool:
        return self.expr is not None

@dataclass
class Finding:
    level: Literal["error", "warn", "notice", "report"]
    rule: str               # "fact.unregistered" 등 안정적인 식별자
    message: str
    location: str | None    # "draft.md:L34"
```

`Finding.level`이 종료코드를 결정한다 — error 1건이라도 있으면 exit 1, 나머지는 exit 0.

`rule` 문자열을 안정적으로 유지하는 이유: 테스트가 메시지 문구가 아니라 규칙 id로 단언해야 문구를 다듬어도 테스트가 깨지지 않는다.

---

## 3. 모듈 명세

### 3.1 blocks.py

- `parse_frontmatter(text) -> (dict, body)` — `---` 구분자 2개. 없으면 오류.
- `load_blocks(root) -> list[Block]` — `core/`, `evidence/`, `strategy/` 하위 `*.md` 전부. `docs/`, `archive/`, `proposals/`, `templates/`, `import/`는 제외.
- `sha(body)` — **본문만** 해시한다. frontmatter를 포함하면 `last_verified` 갱신만으로 core.lock이 깨지고, 그 순간 잠금이 노이즈가 된다.
- 필수 필드 누락은 error, 알 수 없는 필드는 warn.

### 3.2 facts.py

```
load_facts(root):
    facts/ 디렉터리 존재  → facts/*.yaml 전부 병합 (id 중복 시 error)
    없으면               → facts.yaml
```

파생 fact 평가 (`eval_derived`):

1. `expr`를 `ast.parse(mode="eval")`로 파싱한다.
2. 화이트리스트 워크 — 허용 노드: `Expression`, `BinOp`, `Add/Sub/Mult/Div`, `UnaryOp/USub`, `Name`, `Constant(int|float)`. 그 외 노드 발견 즉시 error. **`eval()`에 문자열을 그대로 넘기지 않는다.**
3. `Name`은 등록된 비파생 fact id만 허용. 파생 fact 참조는 error (깊이 1 고정).
4. 입력 fact에 `num`이 없으면 error.
5. 결과를 `format`의 `{v}` 슬롯에 삽입. 슬롯이 2개 이상이면 error.

상속 (`derived_status`):

- `verified` = 입력들 중 최소(가장 오래된 것)
- 재확인 기한 = 입력별 `verified + recheck_days` 중 최소. `stability: fixed` 입력은 기한 계산에서 제외.
- `source` = `"{입력 source들} · 계산: {expr}"`
- 파생 fact가 `verified`/`stability`/`recheck_days`/`source`를 선언하면 error (기획 8장)

캐시 없음. `ppsk build`마다 재계산.

### 3.3 tags.py

- `load_tags(root)` → `{정규형: [alias...]}` + `_config.unregistered`
- `normalize(tag)` → alias 역인덱스 조회. 없으면 원문 그대로 반환하고 미등록 카운트를 올린다.
- 미등록 태그의 등급은 `_config.unregistered` 값을 따른다. 기본 `warn`.

### 3.3.1 projects.py

```
load_projects(root) -> (Projects, findings)
    projects.yaml 없음 → 빈 등록부. 전부 공용이므로 필터가 항상 통과한다 (오류 아님)
```

- `Projects.resolve(name)` → 등록된 id. alias 도 흡수한다. 미등록이면 `None`.
- `Projects.selects(declared, project)` → 이 항목이 해당 프로젝트에서 보이는가.

```python
def selects(declared, project):
    if not declared:      # 소속 미선언 = 공용
        return True
    if project is None:   # 프로젝트를 특정하지 않은 수집 = 전부
        return True
    return project in declared
```

**필터는 정렬보다 먼저 돈다.** `collect` 는 후보 목록을 만들 때 `selects` 로 거르고, 그 뒤에 태그 가중치로 정렬한다. 순서를 바꾸면 다른 프로젝트 블록이 상위에 올라와 사람이 그것을 지우는 작업이 생긴다.

`core.lock` 은 프로젝트와 무관하다. 잠금 대상은 경로와 해시이며 소속이 바뀐다고 본문이 바뀌지는 않는다.

### 3.4 numbers.py — 주장성 수치 탐지

기획 6장 분류표의 코드화. **제외 패턴을 먼저 소거한 뒤 대상 패턴을 찾는다** (제외가 우선).

```python
EXEMPT_MARKER = r"\{\{![^}]*\}\}"          # 면제 마커 — 스캔 전 제거, 건수만 센다
FACT_REF      = r"\{\{[a-z0-9_]+\}\}"      # fact 참조 — 스캔 전 제거

EXCLUDE = [
    r"\d{4}-\d{2}-\d{2}",                        # 날짜
    r"제?\s*\d+\s*(장|절|항|조)",                 # 순번·구조
    r"(표|그림|그래프)\s*\d+",
    r"^\s*\d+\.\s",                              # 목록 번호 (MULTILINE)
    r"\d+\s*(개월|주|일차|차년도|년차)",           # 기간·연차
    r"TRL\s*\d+",                                # 단계·등급
    r"\d+\s*단계",
    r"\d+\s*가지",                               # 목록 개수
]

CLAIM = [
    r"[\d,]+(\.\d+)?\s*(억|조|만)?\s*원",         # 금액
    r"\$[\d,]+(\.\d+)?\s*[KMB]?",
    r"[\d,]+\s*(명|건|개\s*기관|개사|곳|회|세션)",  # 규모·실적
    r"\d+(\.\d+)?\s*(%|%p|배)",                   # 비율·배수
    r"\d{2}-\d{4}-\d{7}",                         # 등록번호
    r"약\s*[\d,]+(\.\d+)?",                       # 근사 표현도 대상
    r"[\d,]+\s*(원대|명대|건대)",                  # 범위 표현
]
```

`find_claims(text) -> list[(line_no, matched_text)]`.

**이 정규식들은 가설이다.** 1단계 임포트 결과로 조정하고, 조정할 때마다 `tests/test_numbers.py`에 실제 문장을 케이스로 추가한다. 그 테스트가 곧 숫자 클래스 정의의 실체가 된다.

### 3.5 lock.py

- `write_lock(root)` — `core/` 하위 **`status: active` 블록만** 대상. draft는 잠그지 않는다(기획 3장).
- `verify_lock(root)` → 불일치 목록
- `append_deviation(proposal_dir, path, old_sha, new_sha, diff)` — `deviations.md`에 append:

```markdown
## 2026-08-18 core/thesis/core-claim.md
- 잠금 해시: a3f21c9 / 현재: 8c1e04b
- 상태: open
- 시도된 변경:

      - 기존 문장
      + 바뀐 문장
```

`상태: open|closed`가 `ppsk review --close`의 처리 표시다. 파일에서 항목을 지우지 않고 `closed`로 바꾼 뒤 카운트에서 제외한다 — 삭제하면 이력이 사라지고, 남겨두기만 하면 알림이 상시화된다.

### 3.6 check.py

`run_checks(root, proposal) -> list[Finding]`. 기획 8장 검증 규칙 요약표를 그대로 구현하고, 표의 각 행에 `rule` id를 하나씩 부여한다.

| rule id | level |
|---|---|
| `fact.unregistered` | error |
| `fact.stale` | error |
| `derived.nested` | error |
| `derived.unknown_input` | error |
| `derived.invalid_expr` | error |
| `derived.invalid_format` | error |
| `derived.missing_num` | error |
| `derived.forbidden_field` | error |
| `core.lock_mismatch` | error (+ deviation 자동 기록) |
| `angle.no_match` | error |
| `angle.malformed` | error |
| `block.malformed` | error |
| `facts.malformed` / `facts.duplicate_id` | error |
| `tags.malformed` / `projects.malformed` | error |
| `project.unregistered` | error |
| `project.mismatch` | error |
| `strict.not_verbatim` | error |
| `tag.unregistered` | warn (config로 error 승격) |
| `block.stale` | warn |
| `generated_from.mismatch` | warn |
| `block.draft_used` | warn |
| `block.unknown_field` / `facts.unknown_field` | warn |
| `review.due` | notice |
| `facts.count_threshold` | notice |
| `project.unassigned` | notice (config로 승격) |
| `exempt.usage` | report |

`strict.not_verbatim` 검사: 블록 본문과 초안 양쪽에 공백 정규화(`re.sub(r"\s+", " ", s).strip()`)를 적용한 뒤 부분 문자열 포함으로 판정한다. 마크다운 구조는 건드리지 않는다.

블록 신선도 주기는 계층별 상수:

```python
FRESHNESS = {"identity": None, "thesis": 180, "evidence": 90, "strategy": 180}
```

### 3.7 render.py

- `substitute(text, facts, today) -> (final_text, findings)` — `{{id}}`는 값으로, `{{!x}}`는 `x`로 치환.
- `--preview`: 재확인 필요 fact 위치에 `<!-- ⚠ 재확인 필요: id -->` 삽입.
- `ppsk build`(preview 아님)는 `<!-- ⚠` 잔존 시 변환 거부(exit 1).
- `write_report(proposal_dir, findings)` → `report.md`. 첫 줄에 `<!-- 자동 생성 — 편집 금지 -->`.

---

## 4. 커맨드별 계약

| 커맨드 | 입력 | 출력 | exit |
|---|---|---|---|
| `ppsk init` | 없음 | 디렉터리 골격 + `CLAUDE.md`/`AGENTS.md` 포인터 + 빈 `facts.yaml`/`tags.yaml` | 0 |
| `ppsk import <file> [--project <id>]` | 원본 문서 | `import/<name>/`에 블록 후보 `.md`(전부 `status: draft`) + `facts.candidates.yaml` + `tags.candidates.txt` | 0 |
| `ppsk index [--project <id>]` | — | `INDEX.md` (경로·layer·정규형 tags·projects·summary) | 0 |
| `ppsk new <slug> --type [--project <id>]` | 템플릿 | `proposals/<날짜>-<slug>/` 5파일, `angle.md`가 `templates/angles/<type>.md` 상속 | 0 |
| `ppsk collect <slug>` | `angle.md` | `angle.md`의 `project` 로 먼저 거른 뒤 선별 블록을 stdout 연결 출력 + `generated_from` 갱신 | 매칭 0건이면 1 |
| `ppsk check <slug>` | 전체 | 콘솔 요약 + `report.md` | error 있으면 1 |
| `ppsk verify <fact-id> [--note]` | — | `facts.yaml`의 `verified`를 오늘로 갱신 | 파생 fact면 1 |
| `ppsk build <slug> [--preview]` | `draft.md` | `final.md` | check 실패 또는 마커 잔존 시 1 |
| `ppsk core-update <path> --reason` | — | `core.lock` 갱신 + `core/CHANGELOG.md` append | 0 |
| `ppsk review [--close]` | `proposals/**/deviations.md` | core 블록별 그룹 출력 / `--close`는 `closed` 표시 + CHANGELOG 기록 | 0 |

**`ppsk import`는 분해하지 않는다.** 원본을 문단 단위로 잘라 스캐폴드만 만들고, 계층 판정과 병합은 에이전트가 한다(기획 9장 역할 분담). `import/`는 승인 전 격리 구역이며, 사람이 승인한 파일만 `core/`·`evidence/`로 옮긴다.

**`ppsk collect` 필터:** `angle.md` 의 `project` 와 각 블록의 `projects` 를 `selects` 로 대조해 후보를 먼저 줄인다. `project` 가 없는 제안서(회사 단위 IR 등)는 전부를 후보로 본다. 필터 결과가 0건이면 정렬 이전에 실패다.

**`ppsk collect` 정렬:** 태그 가중치 `강=3`, `배경=1`. 블록 점수 = 매칭 태그 가중치 합. 동점은 경로 사전순(출력이 재현 가능해야 한다). 고정 포함은 점수와 무관하게 선두, 제외는 점수와 무관하게 배제.

**`ppsk verify`의 YAML 쓰기:** `yaml.dump`로 전체를 다시 쓰면 주석과 키 순서가 날아간다. 정규식으로 해당 fact 블록의 `verified:` 줄만 치환한다. `--note`는 그 줄 끝에 주석(`# 2026-08-18: ...`)으로 붙인다.

---

## 5. 구현 순서 (기획 13장 매핑)

### 1단계 — 임포트로 씨앗 만들기

- `model.py`, `blocks.py`, `tags.py`(정규화만), `scaffold.py`
- `cmd_init`, `cmd_import`, `cmd_index`
- 테스트: `test_blocks.py`(frontmatter 파싱·필수 필드), `test_tags.py`(alias 정규화)
- 산출물은 코드가 아니라 **채워진 리포지토리**. 이 단계에서 `numbers.py` 정규식과 `tags.yaml` 초안을 실제 문장으로 확정한다.

### 2단계 — 조립 경로

- `facts.py`(로더 → 파생 평가 순), `numbers.py`, `check.py`, `render.py`
- `cmd_new`, `cmd_collect`, `cmd_check`, `cmd_verify`, `cmd_build`
- 테스트: `test_facts.py`(파생 AST 화이트리스트·상속·금지 필드), `test_numbers.py`(1단계에서 모은 실제 문장), `test_check.py`(규칙 id별 최소 1케이스)
- 실제 제안서 1건 완주 → 드러난 문제로 스키마 조정

파생 fact 지원은 **실제 계산값이 필요해진 뒤** 붙인다. 그전까지 `expr` 선언은 "미지원" error로 두면 된다.

### 3단계 — 잠금과 검토 루프

- `lock.py`, `cmd_core_update`, `cmd_review`
- `check.py`에 `core.lock_mismatch` 규칙 + deviation 자동 기록 추가
- 태그 어휘 안정화 확인 후 `unregistered: error` 승격
- 선택적 `.claude/hooks/` — 있으면 편한 조기 경보, 없어도 방어선은 유지된다

잠금이 마지막인 이유는 기획 13장 그대로다. 2단계까지의 `ppsk check`은 `core.lock` 없이도 정상 동작해야 한다 — **`core.lock` 부재는 error가 아니라 무검사다.**

---

## 6. 테스트 전략

전부 테스트하지 않는다. **결정론적 판정 로직만** 테스트한다.

| 테스트함 | 안 함 |
|---|---|
| 파생 fact 평가·상속·금지 필드 | `cmd_init` 디렉터리 생성 |
| 숫자 클래스 정규식 (실제 문장 코퍼스) | `INDEX.md` 문자열 포맷 |
| 검증 규칙 id별 발화 여부 | 콘솔 출력 색상 |
| `collect` 정렬 결과의 재현성 | argparse 파싱 |
| `verify`가 다른 fact를 건드리지 않음 | 스캐폴드 템플릿 내용 |

`tests/fixtures/`에 최소 리포지토리 하나(블록 4개, fact 5개, 제안서 1건)를 두고, 대부분의 테스트가 그것을 `tmp_path`로 복사해 쓴다.

---

## 7. 미확정 — 구현 중 결정

**확정됨 (2026-08-20, T-G1):** `ppsk import` 의 분할 단위는 **h1~h2 헤딩**이다. 실제 제안서 2건을 h1~h6 전부로 자르니 부모 헤딩이 본문 두 줄짜리 껍데기 블록이 되고 109건이 나왔다. h3 이하는 부모 본문에 포함한다.

- **프로젝트별 태그 어휘 분리** — 지금은 `tags.yaml` 하나를 전 프로젝트가 공유한다. 어휘가 프로젝트마다 갈라지는 것이 실제로 관찰된 뒤에 나눈다.
- **`num` 없는 fact의 파생 참조** — 지금은 error. `"참여자 42명"`에서 42를 자동 추출하는 것은 조용히 틀릴 위험이 커서 하지 않는다.
- **`generated_from` 해시 길이** — 저장은 전체, 표시는 7자.
- **줄바꿈 정규화** — 읽기는 텍스트 모드(자동 변환), 쓰기는 `\n` 고정, **해시 계산 전 `\r\n` → `\n` 정규화 필수**. 빼먹으면 `core.lock`이 OS마다 다르게 나와 잠금이 무의미해진다.
