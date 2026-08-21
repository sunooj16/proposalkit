"""검증 규칙 실행과 요약.

`run_checks` 가 로더를 전부 돌려 `Finding` 을 한 자리에 모으고, 정렬해서
돌려준다. 콘솔 출력과 `report.md` 는 커맨드(T-17)가, 개별 검증 규칙은
T-12/T-13 이 여기에 붙는다.

**판정과 종료코드는 이 모듈이 단독으로 소유한다** — `ppsk index` 처럼 리포트만
하는 커맨드는 Finding 을 출력하되 exit code 에 반영하지 않는다.
"""

from pathlib import Path

from .blocks import load_blocks
from .facts import eval_all_derived, load_facts
from .projects import load_projects
from .tags import load_tags

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


def run_checks(root, proposal=None):
    """`list[Finding]`. `proposal` 은 `proposals/<slug>/` 경로 — 없으면 리포지토리 전역 검사만.

    로더가 낸 Finding(`*.malformed`, `*.unknown_field`, `facts.duplicate_id`,
    `facts.count_threshold`, `derived.*`)은 여기서 합류한다. 예외로 던지지 않고
    Finding 으로 넘기는 이유가 이것 — 첫 번째 깨진 파일에서 멈추지 않고 전부
    모아 한 번에 보여준다.
    """
    root = Path(root)
    findings = []

    def collect(loaded):
        value, found = loaded
        findings.extend(found)
        return value

    collect(load_blocks(root))
    facts = collect(load_facts(root))
    collect(eval_all_derived(facts))
    collect(load_tags(root))
    collect(load_projects(root))

    # ponytail: 규칙은 T-12(fact/derived/project)·T-13(tag/block/angle/strict)에서
    # 이 아래에 붙는다. proposal 을 쓰는 규칙도 그때부터다.
    return sort_findings(findings)
