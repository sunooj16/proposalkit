"""`{{fact}}` 치환과 리포트 생성.

`draft.md` 와 `final.md` 를 분리하는 것이 기획 6장 수치 검증의 전제다. 검증은
초안에만 적용되고, `final.md` 는 통과한 결과물이다. 한 파일에 두 역할을 맡기면
"치환된 숫자"와 "지어낸 숫자"를 구별할 수 없다.
"""

from pathlib import Path

from .check import LEVELS, recheck_due
from .facts import value_of
from .model import Finding
from .numbers import EXEMPT_MARKER, FACT_REF

REPORT_FILE = "report.md"
REPORT_HEADER = "<!-- 자동 생성 — ppsk check. 편집 금지 -->"

# 터미널 경고는 스크롤에 묻히지만 문서 안의 주석은 편집하다 반드시 마주친다 (기획 8장).
MARKER_PREFIX = "<!-- ⚠"
MARKER = MARKER_PREFIX + " 재확인 필요: {id} -->"

LEVEL_TITLES = {"error": "오류", "warn": "경고", "notice": "알림", "report": "리포트"}


def has_markers(text):
    """인라인 마커가 남아 있는가. `ppsk build` 는 남아 있으면 변환을 거부한다."""
    return MARKER_PREFIX in text


def substitute(text, facts, today, derived=None, preview=False):
    """`(치환된 텍스트, findings)`.

    `{{id}}` 는 값으로, `{{!x}}` 는 `x` 로 바꾼다. 미등록 참조는 **그대로 둔다** —
    치환한 척하고 넘어가면 `final.md` 에 근거 없는 숫자가 남는다.

    `preview` 면 재확인이 필요한 fact 자리에 인라인 마커를 남긴다.
    """
    findings = []

    def replace(match):
        fact_id = match.group(1)
        fact = facts.get(fact_id)
        location = "L%d" % (text.count("\n", 0, match.start()) + 1)

        def bad(rule, message):
            findings.append(Finding(level="error", rule=rule, message=message, location=location))
            return match.group(0)  # 원문 유지 — 빈칸으로 치환하면 문장이 조용히 거짓말을 한다

        if fact is None:
            return bad("fact.unregistered", f"미등록 fact 참조: {match.group(0)}")

        value = value_of(fact, derived)
        if value is None:
            return bad("fact.no_value", f"값이 없는 fact: {fact_id} — value 또는 num 이 있어야 치환한다")

        due = recheck_due(fact, derived)
        if preview and due is not None and due < today:
            return MARKER.format(id=fact_id) + value
        return value

    text = FACT_REF.sub(replace, text)
    # 면제 마커는 껍데기만 벗긴다. `{{!12개월}}` → `12개월`
    text = EXEMPT_MARKER.sub(lambda m: m.group(0)[3:-2], text)
    return text, findings


def render_report(findings, title=None):
    """`report.md` 내용. 레벨별로 묶고, 각 줄은 규칙 id·위치·문구.

    ponytail: 규칙마다 전용 서식을 짜지 않는다. 판정 문구는 이미 Finding.message
    가 들고 있고(`· ppsk verify <id>` 같은 다음 행동 포함), 규칙 id 는
    `docs/rules.md` 가 설명한다. 서식이 늘면 규칙을 늘릴 때마다 두 곳을 고친다.
    """
    lines = [REPORT_HEADER, ""]
    if title:
        lines += [f"# {title}", ""]

    if not findings:
        return "\n".join(lines + ["이상 없음.", ""])

    for level in LEVELS:
        group = [f for f in findings if f.level == level]
        if not group:
            continue
        lines += [f"## {LEVEL_TITLES[level]} ({len(group)}건)", ""]
        for finding in group:
            where = f" — `{finding.location}`" if finding.location else ""
            lines.append(f"- `{finding.rule}`{where} — {finding.message}")
        lines.append("")

    # 레벨을 모르는 Finding 도 버리지 않는다. 조용히 사라지는 판정이 없어야 한다.
    rest = [f for f in findings if f.level not in LEVEL_TITLES]
    if rest:
        lines += [f"## 알 수 없는 레벨 ({len(rest)}건)", ""]
        lines += [f"- `{f.level}` / `{f.rule}` — {f.message}" for f in rest]
        lines.append("")

    return "\n".join(lines)


def write_report(proposal_dir, findings, title=None):
    """`report.md` 를 쓰고 경로를 돌려준다. 사람이 편집하는 파일이 아니다 (기획 8장)."""
    path = Path(proposal_dir) / REPORT_FILE
    path.write_text(render_report(findings, title), encoding="utf-8", newline="\n")
    return path
