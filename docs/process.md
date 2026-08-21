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

*(없음 — 다음: T-16 `cmd_collect` — 프로젝트 하드 필터 → 태그 가중치 정렬)*

---

## 앞으로 진행할 작업

### 1단계 — 임포트로 씨앗 만들기

| id | 작업 | 산출물 | 완료 조건 | 영향 |
|---|---|---|---|---|

### 2단계 — 조립 경로

| id | 작업 | 산출물 | 완료 조건 | 영향 |
|---|---|---|---|---|
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
| T-15 | `cmd_new` | `feat: cmd_new — 제안서 스캐폴드 + angle 상속 (T-15)` | **4파일**(brief/angle/draft/deviations). `extends` 는 여기서 한 번 펼치고 출처로 남긴다. 앵글 템플릿은 패키지가 아니라 리포지토리의 `templates/angles/` 를 읽는다. `--project` 는 `angle.md` 의 `project:` 로, 미등록 id 는 쓰기 전에 exit 1. slug 경로 탈출 차단, 기존 폴더는 덮지 않음 |
| T-14 | `render.py` | `feat: render.py — fact 치환·인라인 마커·report.md (T-14)` | `substitute`(미등록·무값 참조는 원문 유지 + error), `has_markers`, `render_report`/`write_report`. `value_of` 는 facts.py 소유(check·render 공용). `fact.no_value` 신설 — check 에서도 발화 |
| T-13 | 검증 규칙 — tag/block/angle/strict | `feat: check.py — 블록·앵글 검증 규칙 (T-13)` | `angle.py` 신설(로더). `tag.unregistered`(정규화 1회), `block.stale`(계층 주기, `identity` 무기한), `block.draft_used`, `angle.no_match`(강조 태그·고정 포함·**제외** 경로), `strict.not_verbatim`(공백 정규화 후 부분 문자열), `generated_from.mismatch`(해시 접두 + 블록 실종), 블록 `project.mismatch`(T-12에서 이월) |
| T-12 | 검증 규칙 — fact/derived/project | `feat: check.py — fact·project 검증 규칙 (T-12)` | `fact.unregistered`(미등록 `{{id}}` 참조 + 잔존 주장성 수치), `fact.stale`(파생은 입력 상속 기한, `fixed` 는 영구 통과), `project.unregistered`(블록·fact·`angle.md`), `project.mismatch`(초안이 쓴 타 프로젝트 전용 fact), `project.unassigned`(등록부 있을 때만), `exempt.usage`. 같은 fact 는 여러 번 참조돼도 한 번만 신고. `angle.malformed` 신설 |
| T-11 | `check.py` 뼈대 | `feat: check.py — run_checks 뼈대 (T-11)` | `run_checks(root, proposal=None)` 가 로더 4종 + 파생 평가 Finding 을 합류. `sort_findings`(레벨→규칙→위치→문구, 미지 레벨은 뒤), `counts`/`summary`, `exit_code`(error 1건이면 1). 규칙은 없음 |
| T-31 | `cmd_index` 개정 (T-07 개정) | `feat: cmd_index — --project 필터 + 프로젝트 열 (T-31)` | 공용 블록은 항상 포함, 타 프로젝트 전용은 차단. 미등록 id는 exit 1. 프로젝트 열은 소속 없으면 `공용`. `-o/--output` 추가 |
| T-30 | `cmd_import` 개정 (T-06 개정) | `feat: cmd_import — --project 로 후보 소속 스탬프 (T-30)` | alias 흡수(`cog`→`cogtrain`), 미등록 id는 임포트 전에 exit 1. 미지정 시 `projects: []` + 안내 1줄. fact 후보는 파일 단위 `_project` 한 줄 |
| T-29 | `scaffold`/`cmd_init` 개정 (T-05 개정) | `feat: scaffold — projects.yaml 템플릿 + rules 프로젝트 절 (T-29)` | 빈 등록부 + 주석 예시. `docs/rules.md`에 프로젝트 절 추가. 기존 리포지토리에서 `ppsk init` 재실행 시 `projects.yaml`만 추가됨(실행 확인) |
| T-28 | `blocks.py` 개정 (T-03 개정) | `feat: blocks.py — projects 필드 파싱 (T-28)` | 알려진 선택 필드로 승격(미지 필드 warn 대상에서 제외), 문자열 1개도 목록으로 흡수. 미등록 id 판정은 check |
| T-27 | `model.py` 개정 (T-02 개정) | `feat: model.py — Block/Fact 에 projects 필드 (T-27)` | `Block.projects`/`Fact.projects`, 기본값 빈 목록 = 공용 |
| T-09 | `facts.py` 파생 평가 | `feat: facts.py — 파생 fact 평가 (T-09)` | `eval_derived`/`eval_all_derived`, `Derived` 데이터클래스. AST 화이트리스트(`eval()` 미사용), 깊이 1, `num` 없는 입력 거부, `verified`/`recheck_due`/`source` 상속(`fixed` 입력은 기한에서 제외), `format` 슬롯 1개 강제 |
| T-08 | `facts.py` 로더 | `feat: facts.py — facts 로더 (T-08)` | `load_facts` → `(dict[id, Fact], findings)`. `facts/` 있으면 그쪽만(사전순 병합), 없으면 `facts.yaml`. id 중복 error(먼저 읽은 쪽 유지), 파일 단위 `_project` 상속·항목이 덮어씀, 80건 초과 notice, 타입 위반 error·미지 필드 warn |
| T-G1 | **1단계 게이트** — 과거 제안서 2건 임포트·승인·병합 | `chore: 과거 제안서 2건 임포트·승인 (T-G1)` (콘텐츠 리포지토리) | 블록 38건(thesis 16 / evidence 6 / strategy 16, 공용 2), `projects.yaml` 2건, `tags.yaml` 어휘 28개 확정. 숫자 코퍼스로 T-10 완료. 전 블록 `status: draft` — 본문 문구 검토가 남음. `tests/fixtures/`는 T-08에서 만든다 |
| T-33 | `tags.py` 중복 제거 (T-04 개정) | `fix: tags.py — 정규화 후 중복 태그 제거 (T-33)` | `normalize_all`이 선언 순서를 유지하며 중복 제거. 미등록 카운트는 등장한 만큼 유지 |
| T-32 | `cmd_import` 분할 단위 조정 (T-06 개정) | `fix: cmd_import — h2까지만 분할 (T-32)` | `SPLIT_DEPTH = 2`, `split_sections(text, depth)`. 재임포트 결과 tips-ad 38 → 16건, mvp-cogcare 71 → 18건 |
| T-10 | `numbers.py` 코퍼스 조정 | `fix: numbers.py — T-G1 코퍼스로 정규식 조정 (T-10)` | 만/억/조 배수+단위, 달러, 범위 표현, 근사 접두어 통합, 겹침 매치 병합, 쉼표 단독 매치 버그. 제외 추가: 연월일·일정 표기·각주 번호·연령·N차. 실제 문장 21건 `CORPUS` 고정 |
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
| 2026-08-20 | T-30에서 미등록 프로젝트 id를 임포트 **전에** 막기로(커맨드에서 exit 1). 원칙상 판정은 check 소유지만, 오타를 그대로 찍으면 승인까지 끝난 뒤 수십 개 파일을 되돌려야 한다 | T-30, T-12 |
| 2026-08-20 | **프로젝트 축 코드 작업 완료(T-26~T-31).** 1단계 파이프라인(init → import → index)이 프로젝트 축을 태우고 동작. 나머지 반영분은 2단계 작업(T-08 `_project` 상속, T-12 `project.*` 규칙, T-15 `--project`, T-16 하드 필터)에 남아 있음 | T-08,12,15,16 |
| 2026-08-20 | **T-G1 임포트 실행.** 과거 제안서 2건(TIPS 투자제안서 → `ad-samd`, MVP 공동개발 사업계획서 → `cogcare`)을 별도 콘텐츠 리포지토리에 임포트. 도구 리포지토리와 분리 — 회사 자료와 도구 이력이 섞이지 않게 | T-G1 |
| 2026-08-20 | T-10 완료. 코퍼스가 드러낸 구멍 5가지(배수 뒤 단위 누락, 달러 미지원, 근사 표현 중복 계상, 범위 앞쪽 유실, 쉼표 단독 매치). 접두어를 각 패턴에 흡수하고 겹침은 긴 매치만 남기는 방식으로 해결 | T-12 |
| 2026-08-20 | devplan §7 미확정 **문단 분할 단위 확정 — h2까지만**. 실물에서 h1~h6 전부 자르니 부모 헤딩이 껍데기 블록(364바이트)이 되고 109건이 나옴. 개정은 T-32 | T-06, T-32, devplan §7 |
| 2026-08-20 | T-32 완료. h2 분할로 재임포트 — 블록 후보 109건 → 34건. `depth` 를 인자로 열어둠(기본 2) — 문서마다 헤딩 관례가 달라 재임포트 시 조정 여지가 필요 | T-G1 |
| 2026-08-20 | T-33. T-G1 승인 중 `[문제정의, 고객문제]`처럼 정규형과 alias를 같이 단 블록이 나와 인덱스에 `문제정의, 문제정의`가 출력됨. `normalize_all`에서 중복 제거 — 호출부마다 고치면 collect에서 또 샌다 | T-04, T-07, T-16 |
| 2026-08-20 | **T-G1 완료.** 블록 38건 승인·병합, `tags.yaml` 28개 어휘 귀납. 분할 기준은 "h2 본문이 비고 하위 절이 각 300자 이상이면 쪼갠다" — 12장(각 130~195자)처럼 잘면 부모 유지 | T-G1, T-32 |
| 2026-08-20 | T-G1 승인 시 전 블록을 `status: draft`로 둠. 계층·태그·소속은 승인됐지만 본문에 "프레젠테이션의 도식은" 같은 원문 참조 문구가 남아 있어 그대로 제안서에 넣을 수 없다. `active` 승격은 본문 검토 뒤 | T-11, T-13 |
| 2026-08-20 | `tests/fixtures/` 최소 리포지토리는 T-08에서 만든다. 실물 블록이 38건이라 그중 4건을 잘라 쓰면 된다 | T-08 |
| 2026-08-20 | T-08 완료. `tests/fixtures/` 최소 리포지토리는 만들지 않음 — facts 테스트가 전부 인라인 YAML로 충분했다. 전체 리포지토리가 실제로 필요한 T-12·T-17에서 만든다 | T-12, T-17, devplan §6 |
| 2026-08-20 | T-09 완료. devplan §3.6 규칙 표에 없던 id 3개 추가 — `derived.unknown_input`, `derived.invalid_expr`, `derived.invalid_format`. 로더가 내는 `*.malformed`·`*.unknown_field`도 함께 표에 반영 | T-11, T-12, devplan §3.6 |
| 2026-08-20 | 파생 fact의 `format` 은 선택으로 둠(기본 `{v:g}`). 필수로 하면 계산 결과를 그냥 쓰고 싶을 때도 한 줄을 강제하게 된다 | T-09, T-14 |
| 2026-08-21 | T-11 완료. `run_checks`는 로더가 낸 Finding 을 합류시키기만 한다 — 규칙은 T-12/13이 이 파일에 붙인다. 블록 `tags` 정규화(→ `tag.unregistered` 발화)는 뼈대에 넣지 않고 T-13이 소유. 미지 레벨은 error 로 올리지도 버리지도 않고 정렬 맨 뒤 | T-12, T-13, T-17 |
| 2026-08-21 | T-12 완료. 규칙 표에 없던 `angle.malformed`(error) 신설 — `angle.md` frontmatter 가 깨지면 `project:` 를 못 읽어 소속 검사가 조용히 통과한다. `Finding.location` 은 `as_posix()` 로 고정(blocks.py 포함) — `report.md` 는 커밋되는 파일이라 구분자가 OS 마다 달라지면 안 된다. `numbers.FACT_REF` 에 캡처 그룹 추가 | T-13, T-14, T-17, devplan §3.6 |
| 2026-08-21 | 블록의 `project.mismatch` 는 T-13 으로. 초안이 어떤 블록을 썼는지는 `angle.md` 의 `generated_from` 목록으로만 알 수 있고, 그 목록은 `generated_from.mismatch`(T-13)가 이미 읽는다. 두 곳에서 파싱하지 않게 | T-13 |
| 2026-08-21 | `tests/fixtures/` 최소 리포지토리는 T-12 에서도 만들지 않음 — `tmp_path` 에 리포지토리를 세우는 헬퍼 하나로 충분했다. 커맨드 레벨 테스트가 필요한 T-17 에서 다시 판단 | T-17, devplan §6 |
| 2026-08-21 | T-13 완료. `angle.md` 로더를 `ppsk/angle.py` 로 분리 — check(T-13)와 collect(T-16)가 같은 파일을 읽는다. 두 곳에서 절 파싱을 따로 하면 `## 강조` 서식이 갈라진다. devplan §1 코드 구조에 추가 | T-16, devplan §1 |
| 2026-08-21 | `angle.no_match` 를 **제외 경로**에도 적용. 오타 난 제외는 조용히 무효가 되고 빼려던 블록이 그대로 실린다 — 매칭 실패 중 가장 위험한 쪽이다 | T-13, T-16 |
| 2026-08-21 | 앵글 매칭 대상은 프로젝트 필터를 통과한 블록뿐. `collect` 이 거른 뒤 정렬하는 순서와 같아야 "정렬 결과에 없는 태그"가 매칭 성공으로 뜨지 않는다 | T-16 |
| 2026-08-21 | 태그 정규화는 `run_checks` 에서 딱 한 번. `Tags.normalize` 가 미등록 카운트를 올리므로 두 번 돌리면 `tag.unregistered` 건수가 부풀려진다 | T-04, T-17 |
| 2026-08-21 | 앵글의 `extends` 는 로더가 해석하지 않는다(값만 보관). 상속 병합은 `ppsk new` 시점 한 번이면 되고, check 이 또 병합하면 두 소유자가 생긴다 | T-15 |
| 2026-08-21 | T-14 완료. `report.md` 는 기획 8장 샘플의 규칙별 전용 서식 대신 **레벨별 그룹 + `규칙 id — 위치 — 문구`** 한 줄로. 판정 문구는 이미 `Finding.message` 가 다음 행동까지 들고 있고, 규칙마다 서식을 짜면 규칙을 늘릴 때마다 두 곳을 고친다 | T-17, 기획 8장 |
| 2026-08-21 | `fact.no_value`(error) 신설. 값도 `num` 도 없는 fact 는 치환할 수 없다. render 에서만 잡으면 check 를 통과한 초안이 build 에서 죽으므로 `check` 에서도 발화한다 | T-12, T-17, T-19, devplan §3.6 |
| 2026-08-21 | 미등록·무값 fact 참조는 치환하지 않고 **원문을 남긴다**. 빈칸으로 바꾸면 문장이 조용히 거짓말을 한다 | T-19 |
| 2026-08-21 | `value_of` 는 facts.py 소유. check(`fact.no_value`)와 render(치환)가 같이 쓰는데 render 는 이미 check 를 import 하므로 반대 방향 의존이 생기면 순환한다 | T-14 |
| 2026-08-21 | T-15 완료. devplan §4 의 "5파일" 대신 **4파일**만 만든다 — `final.md`·`report.md` 는 build·check 만이 만든다. 빈 파일이 놓여 있으면 검증을 통과한 산출물처럼 보인다 | T-17, T-19, devplan §4 |
| 2026-08-21 | `extends` 는 `ppsk new` 가 한 번 펼치고 `extends:` 는 출처 표시로만 남긴다. 검사 때마다 다시 해석하면 템플릿을 고쳤을 때 이미 확정한 앵글이 조용히 바뀐다 | T-13, T-16 |
| 2026-08-21 | 앵글 템플릿은 패키지가 아니라 **리포지토리**의 `templates/angles/` 에서 읽는다. 스캐폴드 이후 사람이 고쳐 쓰는 파일이고, 유형을 추가하려면 파일 하나만 놓으면 된다 | T-15 |
| 2026-08-21 | 커맨드 루트 인자 표기가 갈렸다 — `init`/`index` 는 위치 인자 `path`, `new` 는 `--root`(위치 인자는 slug 가 차지). 남은 커맨드도 slug 를 받으므로 `--root` 로 간다 | T-16~19, T-21, T-23 |
