# 규약

이 리포지토리에서 일하는 사람과 에이전트가 공유하는 규칙. 규약 원본은 이 파일 하나다
(`CLAUDE.md`·`AGENTS.md`는 여기를 가리키는 한 줄 포인터).

이 문서는 **선언**이지 강제가 아니다. 실제 방어선은 `ppsk check` 이며 환경과 무관하게 동작한다.

## 계층별 권한

| 경로 | 무엇이 사는가 | 에이전트 권한 |
|---|---|---|
| `core/identity/` | 회사·팀·보유자산 | 읽기. 수정은 사람이 `ppsk core-update` 로 |
| `core/thesis/` | 문제 정의, 기존 한계, 핵심 주장, 역량 근거 | 위와 같음 |
| `evidence/` | 근거 블록 — 값의 **해석**이 산다. 값 자체는 `facts.yaml` | 제안 가능, 승인 후 반영 |
| `strategy/` | 가격·GTM 등 상황에 따라 바뀌는 것 | 제안 가능 |
| `proposals/<slug>/draft.md` | 이번 건의 초안 | 자유롭게 작성 |
| `proposals/<slug>/angle.md` | 이번 건의 강조점 | 사람이 확정. 제안까지만 |
| `proposals/<slug>/final.md`, `report.md` | 자동 생성 | 편집 금지 |
| `import/` | 승인 전 격리 구역 | 여기서 `core/`·`evidence/` 로 옮기는 것은 사람이 한다 |

`editable: strict` 블록의 본문은 **축자 그대로** 초안에 들어가야 한다. 다듬고 싶으면 블록을
고쳐라 — 초안에서 고치면 `ppsk check` 이 막는다.

## 프로젝트

사업이 여럿이면 블록과 fact 가 어느 사업에 속하는지 선언한다.

```yaml
projects: [cogtrain]      # 이 프로젝트 전용
# 생략                     → 전 프로젝트 공용
```

- **생략이 공용이다.** 회사 소개·팀·보유자산처럼 실제로 공용인 것은 그냥 두면 된다.
- 쓸 수 있는 id 는 `projects.yaml` 에 등록된 것뿐이다. 미등록 id 는 오타이므로 `ppsk check` 이 막는다.
- 프로젝트는 태그가 아니다. 태그는 순위를 매기고, 프로젝트는 차단한다. A 사업의 실적이
  B 사업 제안서에 들어가면 안 되므로 `ppsk collect` 는 정렬 이전에 프로젝트로 먼저 거른다.
- 제안서는 `angle.md` 의 `project:` 로 소속을 정한다. 생략하면 회사 단위(IR 등)로 보고 전부를 후보로 삼는다.

## 수치

- 주장성 수치는 전부 `facts.yaml` 에 등록하고 본문에는 `{{fact_id}}` 로 쓴다.
- 날짜·순번·기간·단계는 주장이 아니므로 등록 대상이 아니다.
- 정말 예외라면 `{{!17개 기관}}` 으로 면제한다. 면제는 리포트에 건수로 남는다.
- 값을 다시 확인했으면 `ppsk verify <fact-id> --note "..."`. 확인은 제안서가 아니라 fact 가 소유한다.

## 작업 흐름

```
ppsk new <slug> --type rnd --project <id>
                               공고문을 brief.md 에 붙여넣기
                               angle.md 확정                    ← 사람의 판단 ①
ppsk collect <slug>            선별된 블록만 출력 → 그것만 읽고 초안 작성
ppsk check <slug>              error 가 남아 있으면 진행 불가   ← 사람의 판단 ②
ppsk build <slug>              final.md
```

경고와 알림은 흐름을 멈추지 않는다. 멈추는 것은 error 뿐이다.
