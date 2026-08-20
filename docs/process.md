# proposalkit 작업 관리 (process)

`docs/devplan.md`를 단위 작업으로 쪼갠 진행 보드. **작업 상태의 단일 소유자**는 이 파일이다.

## 운영 규칙

1. 작업 단위 하나가 끝나면 **커밋 1개**. 커밋 메시지 끝에 작업 id를 붙인다 — 예: `feat: frontmatter 파서 (T-03)`
2. 작업을 시작하면 "진행 중"으로 옮기고, 끝나면 "완료"로 옮긴다. **진행 중은 항상 1개 이하.**
3. 요구사항이 바뀌면 **바뀐 작업과 그 `영향` 칸에 적힌 후속 작업을 함께** 수정한다. 아래 의존 그래프가 그 추적 근거다.
4. 완료된 작업이 바뀌면 완료 목록에서 되돌리지 말고, **재작업 항목을 새 id로 추가**하고 원래 항목에 `→ T-xx로 개정` 주석을 단다. 이력이 사라지지 않게.
5. `docs/plan.md`(기획)와 충돌하면 기획이 우선. 기획이 바뀌면 devplan → process 순으로 내려온다.

## 의존 그래프

```
T-01 프로젝트 골격
  └ T-02 model.py
      ├ T-03 blocks.py ──┬ T-05 cmd_init/scaffold
      │                  ├ T-06 cmd_import
      │                  └ T-07 cmd_index
      └ T-04 tags.py ────┘
                            │
        [1단계 게이트: 실제 제안서 2건 임포트]
                            │
      ┌─────────────────────┴──────────────┐
   T-08 facts.py 로더                  T-10 numbers.py
   T-09 facts.py 파생 평가                  │
      └──────────┬──────────────────────────┘
              T-11 check.py 뼈대
                 ├ T-12 검증 규칙 (fact/derived)
                 ├ T-13 검증 규칙 (tag/block/angle/strict)
                 └ T-14 render.py 치환·마커·report
                       ├ T-15 cmd_new
                       ├ T-16 cmd_collect
                       ├ T-17 cmd_check
                       ├ T-18 cmd_verify
                       └ T-19 cmd_build
                            │
        [2단계 게이트: 실제 제안서 1건 완주]
                            │
                       T-20 lock.py
                         ├ T-21 cmd_core_update
                         ├ T-22 core.lock 검증 규칙 + deviation 기록
                         └ T-23 cmd_review
                              T-24 태그 어휘 error 승격 검토
                              T-25 선택적 훅
```

---

## 진행 중

*(없음 — 다음: T-30 `cmd_import` 개정)*

---

## 앞으로 진행할 작업

### 1단계 — 임포트로 씨앗 만들기

| id | 작업 | 산출물 | 완료 조건 | 영향 |
|---|---|---|---|---|
| T-30 | `cmd_import` 개정 — `--project <id>` 로 후보에 소속 스탬프 | `ppsk/commands/import_.py` | 미지정 시 `projects: []` + 안내 1줄 | T-G1 |
| T-31 | `cmd_index` 개정 — `--project` 필터 + projects 열 | `ppsk/commands/index.py` | 미등록 id 지정 시 exit 1 (오타가 조용한 빈 인덱스가 되지 않게) | — |
| T-G1 | **1단계 게이트** — 과거 제안서 2건 임포트, 승인/병합, `tags.yaml`·`projects.yaml` 초안 확정, 숫자 클래스 코퍼스 수집 | 채워진 리포지토리, `tests/fixtures/` | 코드 아님. 이 결과로 T-10 정규식과 devplan §7 미확정 항목 확정. 프로젝트 등록부도 여기서 실물로 확정 | T-10, T-26, devplan §7 |

### 2단계 — 조립 경로

| id | 작업 | 산출물 | 완료 조건 | 영향 |
|---|---|---|---|---|
| T-08 | `facts.py` 로더 — 단일 파일 / `facts/` 양쪽 + 파일 단위 `_project` 상속 | `ppsk/facts.py`, `tests/test_facts.py` | id 중복 error, 80건 초과 notice, `_project`가 파일 내 전 fact에 적용되고 항목별 `projects`가 덮어씀 | T-09,11,12,14,18 |
| T-09 | `facts.py` 파생 평가 — AST 화이트리스트 + 상속 | 위 파일 확장 | `eval()` 미사용, 깊이 1 강제, 금지 필드 error | T-12,14,19 |
| T-10 | `numbers.py` — T-G1 코퍼스로 정규식 조정 | `ppsk/numbers.py` 수정, `tests/test_numbers.py` 확장 | 코퍼스 전건 통과 (제외 우선). 뼈대와 초기 케이스는 T-06에서 선작성 | T-12 |
| T-11 | `check.py` 뼈대 — `run_checks` + level→exit code | `ppsk/check.py` | Finding 수집·정렬·요약만 | T-12,13,17,22 |
| T-12 | 검증 규칙 — `fact.*`, `derived.*`, `exempt.usage`, `facts.count_threshold`, `project.unregistered`, `project.mismatch`, `project.unassigned` | `check.py` 확장, `tests/test_check.py` | 규칙 id별 최소 1케이스 | T-17,19 |
| T-13 | 검증 규칙 — `tag.unregistered`, `block.stale`, `block.draft_used`, `angle.no_match`, `strict.not_verbatim`, `generated_from.mismatch` | 위와 동일 | 공백 정규화 후 축자 대조 | T-16,17 |
| T-14 | `render.py` — `{{fact}}` 치환, 인라인 마커, `report.md` | `ppsk/render.py` | `--preview` 마커 삽입 / 잔존 시 build 거부 | T-17,19 |
| T-15 | `cmd_new` — 제안서 스캐폴드 + angle 템플릿 상속 | `ppsk/commands/new.py` | 5파일 생성, `extends` 해석, `--project`를 `angle.md`의 `project:`로 기록 | T-16 |
| T-16 | `cmd_collect` — 프로젝트 하드 필터 → 태그 가중치 정렬 + `generated_from` 갱신 | `ppsk/commands/collect.py` | **필터가 정렬보다 먼저**. 동점 시 경로 사전순(재현성 테스트). 필터 결과 0건은 정렬 이전에 실패 | T-13 |
| T-17 | `cmd_check` — 콘솔 요약 + `report.md` | `ppsk/commands/check.py` | error 있으면 exit 1 | — |
| T-18 | `cmd_verify` — `verified:` 줄만 정규식 치환 | `ppsk/commands/verify.py` | 주석·키 순서 보존, 파생 fact 거부, 타 fact 무변경 테스트 | — |
| T-19 | `cmd_build` — 검증 통과 시 `final.md` | `ppsk/commands/build.py` | 마커 잔존/check 실패 시 exit 1 | — |
| T-G2 | **2단계 게이트** — 실제 제안서 1건 처음부터 끝까지 작성 | `proposals/<slug>/final.md` | 여기서 드러난 문제로 스키마 조정 (조정분은 새 T-id로) | 스키마 관련 전 작업 |

### 3단계 — 잠금과 검토 루프

| id | 작업 | 산출물 | 완료 조건 | 영향 |
|---|---|---|---|---|
| T-20 | `lock.py` — `core.lock` 생성·대조, deviation append | `ppsk/lock.py` | `status: active`만 잠금, 부재 시 무검사(error 아님) | T-21,22,23 |
| T-21 | `cmd_core_update` — lock 갱신 + CHANGELOG 기록 | `ppsk/commands/core_update.py` | `--reason` 필수 | T-23 |
| T-22 | `core.lock_mismatch` 규칙 + deviation 자동 기록 | `check.py` 확장 | 불일치 시 error + `deviations.md` append | T-23 |
| T-23 | `cmd_review` — deviation 취합, `--close` | `ppsk/commands/review.py` | 이벤트(3건/동일 블록 2회) + 90일 백스톱, `--close`는 `상태: closed`로 표시 | — |
| T-24 | 태그 어휘 `unregistered: error` 승격 검토 | `tags.yaml` 한 줄 | 미등록 태그 리포트가 안정된 뒤에만 | T-04,13 |
| T-25 | 선택적 `.claude/hooks/` 조기 경보 | `.claude/hooks/` | 없어도 `ppsk check`이 동일하게 막는지 확인 | — |

---

## 완료된 작업

| id | 작업 | 커밋 | 비고 |
|---|---|---|---|
| T-29 | `scaffold`/`cmd_init` 개정 (T-05 개정) | `feat: scaffold — projects.yaml 템플릿 + rules 프로젝트 절 (T-29)` | 빈 등록부 + 주석 예시. `docs/rules.md`에 프로젝트 절 추가. 기존 리포지토리에서 `ppsk init` 재실행 시 `projects.yaml`만 추가됨(실행 확인) |
| T-28 | `blocks.py` 개정 (T-03 개정) | `feat: blocks.py — projects 필드 파싱 (T-28)` | 알려진 선택 필드로 승격(미지 필드 warn 대상에서 제외), 문자열 1개도 목록으로 흡수. 미등록 id 판정은 check |
| T-27 | `model.py` 개정 (T-02 개정) | `feat: model.py — Block/Fact 에 projects 필드 (T-27)` | `Block.projects`/`Fact.projects`, 기본값 빈 목록 = 공용 |
| T-26 | `projects.py` + `projects.yaml` 스키마 | `feat: projects.py — 프로젝트 등록부·소속 판정 (T-26)` | `selects(declared, project)` 순수 함수(미선언=공용, 미지정 수집=전부), `resolve`/`resolve_all`(alias·대소문자 흡수, 미등록은 `None`), `is_archived`/`active_ids`. 파일 부재는 빈 등록부 |
| T-07 | `cmd_index` | `feat: cmd_index — INDEX.md 생성 (T-07)` | layer별 표(경로·정규형 tags·summary), draft 표시, 미등록 태그 경고 출력. 태그 정규화는 여기서(T-03 결정). 판정이 아니므로 항상 exit 0 → T-31로 개정 |
| T-06 | `cmd_import` + `numbers.py` 뼈대 | `feat: cmd_import — 문단 분할 스캐폴드 (T-06)` | 헤딩 기준 분할(없으면 빈 줄), `import/<name>/`에 `status: draft`·`layer: TODO` 블록 후보 + `facts.candidates.yaml` + `tags.candidates.txt`. devplan §3.4 정규식을 `numbers.py`로 선작성 → T-30로 개정 |
| T-05 | `scaffold.py` + `cmd_init` | `feat: scaffold.py + cmd_init — 리포지토리 골격 (T-05)` | `ppsk/templates/` 트리를 그대로 복사. 디렉터리 목록을 코드에 중복 선언하지 않음(빈 디렉터리는 `.gitkeep`). 기존 파일은 덮지 않아 재실행 안전. `docs/rules.md` + 한 줄 포인터 `CLAUDE.md`/`AGENTS.md`, 주석만 든 `facts.yaml`/`tags.yaml`, angle 템플릿 3종 → T-29로 개정 |
| T-04 | `tags.py` | `feat: tags.py — 통제 어휘 로더·alias 정규화 (T-04)` | `Tags` 데이터클래스(`normalize`/`normalize_all`/`unregistered_findings`) + `load_tags`. `난제` → `기술난제` 매칭, 대소문자·공백 무시. 미등록은 원문 유지 + `Counter` 누적. `_config.unregistered`로 warn/error 승격. `tags.yaml` 부재는 빈 어휘(오류 아님) |
| T-03 | `blocks.py` | `feat: blocks.py — frontmatter 파싱·블록 스캔 (T-03)` | `parse_frontmatter`/`sha`/`load_block`/`load_blocks`. 해시는 본문만 + CRLF 정규화. 필수 필드·enum 위반 `block.malformed` error, 미지 필드 `block.unknown_field` warn. `load_blocks`는 `(blocks, findings)` 튜플 반환 — devplan §3.1 시그니처에서 변경. `tags` 정규화는 T-04 이후 → T-28로 개정 |
| T-02 | `model.py` | `feat: model.py — Block/Fact/Finding (T-02)` | `Block`/`Fact`/`Finding` + `Layer`/`Status`/`Editable`/`Stability`/`Level` Literal 별칭. `Fact.derived`만 로직. 선택 필드는 기본값, 리스트는 `field(default_factory=list)` → T-27로 개정 |
| T-01 | 프로젝트 골격 | `chore: 프로젝트 골격 (T-01)` | `pyproject.toml`(PyYAML 1개), `ppsk/__main__.py` 디스패치, `.gitignore`. `ppsk --version`/`--help` 동작 확인 |

---

## 변경 이력

작업 정의가 바뀔 때마다 한 줄씩 추가. 어떤 요구사항이 어떤 작업들을 건드렸는지 남긴다.

| 날짜 | 변경 내용 | 영향받은 작업 |
|---|---|---|
| 2026-08-18 | 최초 작성 (devplan 기준) | — |
| 2026-08-18 | T-01 완료. 커맨드 등록 방식 확정 — 각 모듈이 `add_parser(subparsers)`로 파서를 반환하고 `run(args)`가 종료코드를 반환. `__main__`은 디스패치만 | T-05~07, T-15~19, T-21, T-23 (커맨드 모듈 전부) |
| 2026-08-20 | T-02 완료. 계층/상태 Literal을 `model.py`의 이름있는 별칭(`Layer` 등)으로 노출 — blocks/facts/check가 문자열 리터럴을 재선언하지 않게 | T-03,04,08~14 |
| 2026-08-20 | T-03 완료. `load_blocks`가 `list[Block]`이 아니라 `(list[Block], list[Finding])`을 반환 — 필수 필드/미지 필드 판정 결과를 예외 대신 Finding으로 넘겨야 check.py가 한 번에 취합한다. `core/CHANGELOG.md` 등은 `SKIP_NAMES`로 스캔 제외 | T-05,06,07,11,20, devplan §3.1 |
| 2026-08-20 | 블록 `tags` 정규형 치환은 `load_blocks`가 아니라 호출부(T-07 index, T-16 collect)에서 하기로. blocks.py가 tags.py에 의존하지 않게 | T-04,07,13,16 |
| 2026-08-20 | T-04 완료. 미등록 카운트를 모듈 전역이 아니라 `Tags` 인스턴스에 담음 — 테스트·다중 리포지토리에서 상태가 새지 않게. 태그 매칭 키는 공백 제거 + casefold (`기술 난제`/`kpi` 흡수) | T-07,13,16,24 |
| 2026-08-20 | T-05 완료. 골격 정의를 `ppsk/templates/` 파일 트리 자체로 둠 — 코드의 디렉터리 목록과 템플릿이 어긋날 여지를 없앰. Windows 콘솔 cp949 인코딩 크래시를 `__main__._force_utf8_output()`에서 일괄 처리(커맨드별 문구 검열 대신) | T-06,15, 커맨드 모듈 전부 |
| 2026-08-20 | T-06에서 `numbers.py`를 선작성. import의 fact 후보 추출에 주장성 수치 탐지가 필요한데, 임시 정규식을 커맨드에 심으면 T-10에서 두 벌이 된다. T-10은 "작성"이 아니라 "T-G1 코퍼스로 조정"으로 축소 | T-10, T-12 |
| 2026-08-20 | devplan §7 미확정 — 문단 분할 단위를 **헤딩 우선, 헤딩 없으면 빈 줄** 로 잠정 결정. 실제 제안서 2건을 아직 못 봐서 T-G1에서 재확인 | T-06, T-G1, devplan §7 |
| 2026-08-20 | 임포트 블록의 `layer`를 추측하지 않고 `TODO`(허용값 아님)로 남김. 계층 미판정 상태로 `core/`에 옮기면 `ppsk check`이 곧바로 error를 내게 — 조용히 틀린 계층이 박히는 것보다 낫다 | T-03,11,12 |
| 2026-08-20 | T-07 완료. `ppsk index`는 미등록 태그를 출력하되 종료코드에 반영하지 않음 — 판정과 exit code는 `ppsk check`이 단독 소유 | T-11,17 |
| 2026-08-20 | **1단계 코드 작업 전부 완료(T-02~T-07).** 다음은 T-G1 게이트 — 과거 제안서 2건 임포트가 있어야 T-10 정규식 조정과 devplan §7 분할 단위 확정이 가능 | T-G1, T-10 |
| 2026-08-20 | **요구사항 추가 — 프로젝트 축.** 회사에 사업이 여럿이라 한 리포지토리 안에서 프로젝트별 필터링이 필요. 블록/fact frontmatter의 `projects:` 목록 + `projects.yaml` 등록부로 구현하고, 생략은 공용으로 본다. 태그로 대신하지 않는 이유: 태그는 가중치 정렬(부드러움), 프로젝트는 누출 차단(단단함) | T-26~31 신설, T-02·03·05·06·07 개정, T-08·12·15·16 표 수정, plan §2·4·5·6·7·8 / devplan §1·2·3.3.1·3.6·4·7 |
| 2026-08-20 | 프로젝트 축을 T-G1 게이트 **앞**에 넣기로. 임포트·승인을 먼저 하면 승인된 블록에 소속을 나중에 전부 손으로 채워야 한다 | T-26~31, T-G1 |
| 2026-08-20 | 프로젝트별 태그 어휘 분리는 하지 않음(devplan §7 미확정으로 기록). 어휘가 실제로 갈라지는 것을 본 뒤에 나눈다 | T-04, T-24 |
| 2026-08-20 | T-26 완료. 미등록 프로젝트 판정을 로더가 아니라 호출부에 남김 — `resolve`는 `None`을 돌려주고 `project.unregistered` error 발화는 T-12 check이 소유. tags.py와 같은 구조 |
| 2026-08-20 | 템플릿 `projects.yaml`은 빈 등록부로 시작 — 프로젝트 목록도 `tags.yaml`처럼 실물에서 확정한다. 다만 `ppsk init` 재실행은 기존 파일을 덮지 않으므로 이미 만들어진 리포지토리의 `docs/rules.md`에는 프로젝트 절이 추가되지 않는다(수동 반영 필요) | T-29, T-G1 |
