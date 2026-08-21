"""검증 규칙 실행과 요약.

`run_checks` 가 로더를 전부 돌려 `Finding` 을 한 자리에 모으고, 규칙을 적용한
뒤 정렬해서 돌려준다. 콘솔 출력과 `report.md` 는 커맨드(T-17)가 만든다.

**판정과 종료코드는 이 모듈이 단독으로 소유한다** — `ppsk index` 처럼 리포트만
하는 커맨드는 Finding 을 출력하되 exit code 에 반영하지 않는다.
"""

import re
from datetime import date, timedelta
from pathlib import Path

from .angle import ANGLE_FILE, load_angle
from .blocks import load_blocks
from .facts import FACTS_FILE, eval_all_derived, load_facts
from .model import Finding
from .numbers import EXEMPT_MARKER, FACT_REF, find_claims
from .projects import load_projects, selects
from .tags import load_tags

DRAFT_FILE = "draft.md"

# 심각한 순. 정렬과 요약 순서를 여기 하나로 고정한다.
LEVELS = ("error", "warn", "notice", "report")
_RANK = {level: rank for rank, level in enumerate(LEVELS)}


def sort_findings(findings):
    """레벨(심각한 순) → 규칙 id → 위치 → 문구.

    같은 리포지토리를 두 번 검사하면 같은 순서가 나와야 한다. 규칙이 도는
    순서나 파일 시스템 순회 순서가 리포트에 새지 않게.
    """
    return sorted(
        findings,
        # 모르는 레벨은 맨 뒤로. 조용히 error 로 승격되거나 사라지는 것보다 낫다.
        key=lambda f: (_RANK.get(f.level, len(LEVELS)), f.level, f.rule, f.location or "", f.message),
    )


def counts(findings):
    """레벨별 건수. 0건인 레벨도 키는 있다 — 호출부가 없는 키를 다루지 않게."""
    result = dict.fromkeys(LEVELS, 0)
    for finding in findings:
        result[finding.level] = result.get(finding.level, 0) + 1
    return result


def summary(findings):
    """`"error 2, warn 1"` — 0건인 레벨은 빼고, 전부 0이면 `"이상 없음"`."""
    parts = [f"{level} {n}" for level, n in counts(findings).items() if n]
    return ", ".join(parts) if parts else "이상 없음"


def exit_code(findings):
    """error 1건이라도 있으면 1. warn 이하는 통과시킨다 (기획 8장)."""
    return 1 if any(f.level == "error" for f in findings) else 0


def _line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def _squeeze(text):
    """공백만 정규화한다. 마크다운 구조는 건드리지 않는다 (devplan §3.6)."""
    return re.sub(r"\s+", " ", text).strip()


def recheck_due(fact, derived=None):
    """이 fact 의 재확인 기한. `None` 이면 기한 없음 — 영구 통과다.

    파생 fact 는 자기 기한을 갖지 않고 입력에서 상속한다(T-09가 계산). 평가에
    실패한 파생 fact 는 이미 `derived.*` error 가 났으므로 기한을 따지지 않는다.
    """
    if fact.derived:
        result = (derived or {}).get(fact.id)
        return result.recheck_due if result is not None else None
    # stability: fixed 는 특허번호·설립일이다. 주기를 선언해도 기한이 없다.
    if fact.stability == "fixed" or fact.verified is None or fact.recheck_days is None:
        return None
    return fact.verified + timedelta(days=fact.recheck_days)


# ── 프로젝트 규칙 (기획 2장 축 3) ────────────────────────────────────────


def _check_projects(blocks, facts, projects):
    """`project.unregistered` / `project.unassigned`.

    오타 하나가 조용한 빈 결과가 되는 축이라 미등록은 처음부터 error 다.
    소속 미선언은 오류가 아니라 "공용으로 취급한다"는 알림이다.
    """
    findings = []
    # 블록 먼저, 그다음 fact. 정렬이 최종 순서를 잡으므로 여기서는 재현성만 지킨다.
    # as_posix — report.md 는 커밋되는 파일이다. 구분자가 OS 마다 달라지면 안 된다.
    items = [(b.path.as_posix(), b.projects) for b in blocks]
    items += [(f"{FACTS_FILE}:{f.id}", f.projects) for f in facts.values()]

    for location, declared in items:
        if not declared:
            if projects.entries:
                # 등록부가 비어 있으면 전부 공용이 정상이다. 그때는 알리지 않는다.
                findings.append(
                    Finding(
                        level=projects.unassigned_level,
                        rule="project.unassigned",
                        message="소속 미선언 — 전 프로젝트 공용으로 취급한다",
                        location=location,
                    )
                )
            continue

        _, unknown = projects.resolve_all(declared)
        for name in unknown:
            findings.append(
                Finding(
                    level="error",
                    rule="project.unregistered",
                    message=f"미등록 프로젝트: {name} — projects.yaml 에 등록하거나 오타를 고칠 것",
                    location=location,
                )
            )
    return findings


def _resolve_project(declared, projects, location, findings):
    """선언된 프로젝트를 정규 id 로. 미등록이면 error 를 남기고 None."""
    if declared in (None, ""):
        return None
    resolved = projects.resolve(declared)
    if resolved is None:
        findings.append(
            Finding(
                level="error",
                rule="project.unregistered",
                message=f"미등록 프로젝트: {declared} — projects.yaml 에 등록하거나 오타를 고칠 것",
                location=location,
            )
        )
    return resolved


# ── 블록 규칙 (기획 3장·8장) ─────────────────────────────────────────────

# 계층별 신선도 주기(일). identity 는 회사·팀이라 기한이 없다 (devplan §3.6).
FRESHNESS = {"identity": None, "thesis": 180, "evidence": 90, "strategy": 180}


def _check_block_freshness(blocks, today):
    """`block.stale` — `last_verified` 가 계층 주기를 넘었는가.

    `last_verified` 가 없는 블록은 기한도 없다. 승인 시점을 안 적었다는 뜻이지
    낡았다는 뜻이 아니다.
    """
    findings = []
    for block in blocks:
        days = FRESHNESS.get(block.layer)
        if days is None or block.last_verified is None:
            continue
        due = block.last_verified + timedelta(days=days)
        if due < today:
            findings.append(
                Finding(
                    level="warn",
                    rule="block.stale",
                    message=f"마지막 확인 {block.last_verified} — {block.layer} 주기 {days}일을 {(today - due).days}일 초과",
                    location=block.path.as_posix(),
                )
            )
    return findings


def _matches(block, entry):
    """`core/thesis/core-claim` 이 파일(`.md` 생략)과 디렉터리 접두를 모두 받는다.

    사람이 `angle.md` 에 손으로 쓰는 칸이라 확장자를 붙이는지가 일정하지 않다.
    """
    path = block.path.as_posix()
    entry = entry.strip().strip("/")
    return path == entry or path == f"{entry}.md" or path.startswith(f"{entry}/")


def _check_angle(angle, visible, normalized, tags, location):
    """`angle.no_match` — 강조 태그·고정 포함·제외가 어떤 블록과도 맞지 않음.

    제외 경로도 함께 본다. 오타 난 제외는 조용히 무효가 되고, 빼려던 블록이
    그대로 제안서에 실린다 — 매칭 실패 중 가장 위험한 쪽이다.
    """
    findings = []

    def no_match(what, value):
        findings.append(
            Finding(
                level="error",
                rule="angle.no_match",
                message=f"{what}이(가) 어떤 블록과도 맞지 않는다: {value}",
                location=location,
            )
        )

    present = {tag for block in visible for tag in normalized.get(block.path, [])}

    for tag, _grade in angle.emphasis:
        if tags.normalize(tag) not in present:
            no_match("강조 태그", tag)

    for entry in angle.include:
        if not any(_matches(block, entry) for block in visible):
            no_match("고정 포함 경로", entry)

    for entry in angle.exclude:
        if not any(_matches(block, entry) for block in visible):
            no_match("제외 경로", entry)

    return findings


def _check_used_blocks(angle, blocks, draft, project, location):
    """`generated_from` 이 가리키는 블록들 — 초안이 실제로 쓴 것이 이 목록이다.

    `generated_from.mismatch` / `block.draft_used` / `project.mismatch` /
    `strict.not_verbatim`.
    """
    findings = []
    by_path = {block.path.as_posix(): block for block in blocks}
    normalized_draft = _squeeze(draft) if draft is not None else None

    def add(level, rule, message):
        findings.append(Finding(level=level, rule=rule, message=message, location=location))

    for path, digest in angle.generated_from:
        block = by_path.get(path)
        if block is None:
            add("warn", "generated_from.mismatch", f"블록이 없다: {path} — 이름이 바뀌었거나 지워졌다")
            continue

        if digest and not block.sha.startswith(digest):
            add(
                "warn",
                "generated_from.mismatch",
                f"{path} — 수집 당시 {digest}, 현재 {block.sha[: len(digest)]}. `ppsk collect` 로 다시 뽑을 것",
            )

        if block.status == "draft":
            add("warn", "block.draft_used", f"draft 상태 블록 사용: {path}")

        if not selects(block.projects, project):
            add(
                "error",
                "project.mismatch",
                f"다른 프로젝트 전용 블록: {path} ({', '.join(block.projects)}) — 이 제안서는 {project}",
            )

        # strict 블록은 문구가 자산이다. 초안이 바꿔 썼으면 core 를 고치거나 free 로 내려야 한다.
        if block.editable == "strict" and normalized_draft is not None:
            body = _squeeze(block.body)
            if body and body not in normalized_draft:
                add("error", "strict.not_verbatim", f"strict 블록 본문이 초안에 축자 등장하지 않는다: {path}")

    return findings


# ── 초안 규칙 (기획 6장·8장) ─────────────────────────────────────────────


def _check_draft(text, location, facts, derived, project, today):
    """`fact.unregistered` / `fact.stale` / `project.mismatch` / `exempt.usage`.

    fact 는 여러 번 참조돼도 한 번만 신고한다 — 기한 경과나 소속 불일치는
    참조의 속성이 아니라 fact 의 속성이다. 리포트가 같은 줄로 부풀지 않게.
    """
    findings = []
    reported = set()  # (rule, fact_id)

    def once(rule, fact_id, level, message, line):
        if (rule, fact_id) in reported:
            return
        reported.add((rule, fact_id))
        findings.append(Finding(level=level, rule=rule, message=message, location=f"{location}:L{line}"))

    for match in FACT_REF.finditer(text):
        fact_id = match.group(1)
        line = _line_of(text, match.start())
        fact = facts.get(fact_id)

        if fact is None:
            once("fact.unregistered", fact_id, "error", f"미등록 fact 참조: {match.group(0)}", line)
            continue

        if not selects(fact.projects, project):
            once(
                "project.mismatch",
                fact_id,
                "error",
                f"다른 프로젝트 전용 fact: {fact_id} ({', '.join(fact.projects)}) — 이 제안서는 {project}",
                line,
            )

        due = recheck_due(fact, derived)
        if due is not None and due < today:
            hint = " (파생 — 입력 기준)" if fact.derived else f" · ppsk verify {fact_id}"
            once(
                "fact.stale",
                fact_id,
                "error",
                f"재확인 기한 경과: {fact_id} — 기한 {due} ({(today - due).days}일 초과)" + hint,
                line,
            )

    # 면제 마커는 판정이 아니라 리포트다. 늘어나는 게 보여야 숫자 클래스를 고친다 (기획 6장).
    for match in EXEMPT_MARKER.finditer(text):
        findings.append(
            Finding(
                level="report",
                rule="exempt.usage",
                message=f"면제 마커: {match.group(0)}",
                location=f"{location}:L{_line_of(text, match.start())}",
            )
        )

    # 남은 주장성 수치는 등록되지 않은 것이다. 면제 마커와 fact 참조는 이미 지워졌다.
    for line, matched in find_claims(text):
        findings.append(
            Finding(
                level="error",
                rule="fact.unregistered",
                message=f"미등록 주장성 수치: {matched} — facts.yaml 에 등록하거나 면제 마커로 감쌀 것",
                location=f"{location}:L{line}",
            )
        )

    return findings


def run_checks(root, proposal=None, today=None):
    """`list[Finding]`. `proposal` 은 `proposals/<slug>/` 경로 — 없으면 리포지토리 전역 검사만.

    로더가 낸 Finding(`*.malformed`, `*.unknown_field`, `facts.duplicate_id`,
    `facts.count_threshold`, `derived.*`)은 여기서 합류한다. 예외로 던지지 않고
    Finding 으로 넘기는 이유가 이것 — 첫 번째 깨진 파일에서 멈추지 않고 전부
    모아 한 번에 보여준다.
    """
    root = Path(root)
    today = today or date.today()
    findings = []

    def collect(loaded):
        value, found = loaded
        findings.extend(found)
        return value

    blocks = collect(load_blocks(root))
    facts = collect(load_facts(root))
    derived = collect(eval_all_derived(facts))
    tags = collect(load_tags(root))
    projects = collect(load_projects(root))

    # 태그 정규화는 딱 한 번만 돈다. `normalize` 가 미등록 카운트를 올리므로
    # 두 번 돌리면 `tag.unregistered` 건수가 부풀려진다 (T-04).
    normalized = {block.path: tags.normalize_all(block.tags) for block in blocks}

    findings += _check_projects(blocks, facts, projects)
    findings += _check_block_freshness(blocks, today)

    if proposal is not None:
        proposal = Path(proposal)
        angle_location = f"{proposal.name}/{ANGLE_FILE}"
        angle_path = proposal / ANGLE_FILE
        angle, error = load_angle(angle_path) if angle_path.exists() else (None, "")
        if error:
            findings.append(Finding(level="error", rule="angle.malformed", message=error, location=angle_location))

        project = _resolve_project(angle.project if angle else None, projects, angle_location, findings)
        draft_path = proposal / DRAFT_FILE
        draft = draft_path.read_text(encoding="utf-8") if draft_path.exists() else None

        if draft is not None:
            findings += _check_draft(draft, f"{proposal.name}/{DRAFT_FILE}", facts, derived, project, today)

        if angle is not None:
            # 매칭 대상은 이 프로젝트에서 보이는 블록뿐이다. collect 이 거른 뒤 정렬하는
            # 것과 같은 순서여야 "정렬 결과에 없는 태그"가 매칭 성공으로 뜨지 않는다.
            visible = [block for block in blocks if selects(block.projects, project)]
            findings += _check_angle(angle, visible, normalized, tags, angle_location)
            findings += _check_used_blocks(angle, blocks, draft, project, angle_location)

    # 미등록 태그 카운트는 위의 정규화가 전부 끝난 뒤에 뽑는다.
    findings += tags.unregistered_findings()
    return sort_findings(findings)
