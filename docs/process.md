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

*(없음 — 다음: T-05 `scaffold.py` + `cmd_init`)*

---

## 앞으로 진행할 작업

### 1단계 — 임포트로 씨앗 만들기

| id | 작업 | 산출물 | 완료 조건 | 영향 |
|---|---|---|---|---|
| T-05 | `scaffold.py` + `cmd_init` | `ppsk/scaffold.py`, `ppsk/commands/init.py`, `templates/` | 빈 디렉터리에서 골격 + `CLAUDE.md`/`AGENTS.md` 포인터 생성 | T-06,15 |
| T-06 | `cmd_import` — 문단 분할 스캐폴드 | `ppsk/commands/import_.py` | `import/<name>/`에 `status: draft` 블록 후보 + fact/tag 후보 | T-10 (정규식 코퍼스) |
| T-07 | `cmd_index` — `INDEX.md` 생성 | `ppsk/commands/index.py` | 경로·layer·정규형 tags·summary 출력 | — |
| T-G1 | **1단계 게이트** — 과거 제안서 2건 임포트, 승인/병합, `tags.yaml` 초안 확정, 숫자 클래스 코퍼스 수집 | 채워진 리포지토리, `tests/fixtures/` | 코드 아님. 이 결과로 T-10 정규식과 devplan §7 미확정 1건 확정 | T-10, devplan §7 |

### 2단계 — 조립 경로

| id | 작업 | 산출물 | 완료 조건 | 영향 |
|---|---|---|---|---|
| T-08 | `facts.py` 로더 — 단일 파일 / `facts/` 양쪽 | `ppsk/facts.py`, `tests/test_facts.py` | id 중복 error, 80건 초과 notice | T-09,11,12,14,18 |
| T-09 | `facts.py` 파생 평가 — AST 화이트리스트 + 상속 | 위 파일 확장 | `eval()` 미사용, 깊이 1 강제, 금지 필드 error | T-12,14,19 |
| T-10 | `numbers.py` — 주장성 수치 탐지 | `ppsk/numbers.py`, `tests/test_numbers.py` | T-G1 코퍼스 전건 통과 (제외 우선) | T-12 |
| T-11 | `check.py` 뼈대 — `run_checks` + level→exit code | `ppsk/check.py` | Finding 수집·정렬·요약만 | T-12,13,17,22 |
| T-12 | 검증 규칙 — `fact.*`, `derived.*`, `exempt.usage`, `facts.count_threshold` | `check.py` 확장, `tests/test_check.py` | 규칙 id별 최소 1케이스 | T-17,19 |
| T-13 | 검증 규칙 — `tag.unregistered`, `block.stale`, `block.draft_used`, `angle.no_match`, `strict.not_verbatim`, `generated_from.mismatch` | 위와 동일 | 공백 정규화 후 축자 대조 | T-16,17 |
| T-14 | `render.py` — `{{fact}}` 치환, 인라인 마커, `report.md` | `ppsk/render.py` | `--preview` 마커 삽입 / 잔존 시 build 거부 | T-17,19 |
| T-15 | `cmd_new` — 제안서 스캐폴드 + angle 템플릿 상속 | `ppsk/commands/new.py` | 5파일 생성, `extends` 해석 | T-16 |
| T-16 | `cmd_collect` — 태그 가중치 정렬 + `generated_from` 갱신 | `ppsk/commands/collect.py` | 동점 시 경로 사전순(재현성 테스트) | T-13 |
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
| T-04 | `tags.py` | `feat: tags.py — 통제 어휘 로더·alias 정규화 (T-04)` | `Tags` 데이터클래스(`normalize`/`normalize_all`/`unregistered_findings`) + `load_tags`. `난제` → `기술난제` 매칭, 대소문자·공백 무시. 미등록은 원문 유지 + `Counter` 누적. `_config.unregistered`로 warn/error 승격. `tags.yaml` 부재는 빈 어휘(오류 아님) |
| T-03 | `blocks.py` | `feat: blocks.py — frontmatter 파싱·블록 스캔 (T-03)` | `parse_frontmatter`/`sha`/`load_block`/`load_blocks`. 해시는 본문만 + CRLF 정규화. 필수 필드·enum 위반 `block.malformed` error, 미지 필드 `block.unknown_field` warn. `load_blocks`는 `(blocks, findings)` 튜플 반환 — devplan §3.1 시그니처에서 변경. `tags` 정규화는 T-04 이후 |
| T-02 | `model.py` | `feat: model.py — Block/Fact/Finding (T-02)` | `Block`/`Fact`/`Finding` + `Layer`/`Status`/`Editable`/`Stability`/`Level` Literal 별칭. `Fact.derived`만 로직. 선택 필드는 기본값, 리스트는 `field(default_factory=list)` |
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
