"""render.py — {{fact}} 치환, 인라인 마커, report.md."""

import textwrap
from datetime import date

from ppsk.facts import eval_all_derived, load_facts
from ppsk.model import Finding
from ppsk.render import (
    MARKER_PREFIX,
    REPORT_HEADER,
    has_markers,
    render_report,
    substitute,
    write_report,
)

TODAY = date(2026, 8, 21)

FACTS = textwrap.dedent(
    """\
    pilot_n:
      value: "67명"
      num: 67
      verified: 2026-08-01
      stability: volatile
      recheck_days: 90

    market_size:
      value: "3,200억 원"
      num: 320000000000
      verified: 2025-09-01
      stability: volatile
      recheck_days: 180

    patent:
      value: "10-2024-0012345"
      verified: 2020-01-01
      stability: fixed
      recheck_days: 30

    total_sessions:
      num: 160

    per_user:
      expr: "total_sessions / pilot_n"
      format: "1인당 {v:.1f}회"
    """
)


def facts_of(tmp_path):
    (tmp_path / "facts.yaml").write_text(FACTS, encoding="utf-8")
    facts, _ = load_facts(tmp_path)
    derived, _ = eval_all_derived(facts)
    return facts, derived


def test_substitutes_facts_derived_and_exempt(tmp_path):
    facts, derived = facts_of(tmp_path)
    text, findings = substitute(
        "참여자 {{pilot_n}} 이 {{!12개월}} 동안 {{per_user}} 를 수행했다.", facts, TODAY, derived
    )
    assert text == "참여자 67명 이 12개월 동안 1인당 2.4회 를 수행했다."
    assert findings == []


def test_value_falls_back_to_num(tmp_path):
    facts, derived = facts_of(tmp_path)
    text, findings = substitute("총 {{total_sessions}}", facts, TODAY, derived)
    assert text == "총 160"
    assert findings == []


def test_unknown_reference_is_left_alone(tmp_path):
    """치환한 척하고 넘어가면 final.md 에 근거 없는 숫자가 남는다."""
    facts, derived = facts_of(tmp_path)
    text, findings = substitute("값은 {{nope}} 다.", facts, TODAY, derived)
    assert text == "값은 {{nope}} 다."
    assert [(f.rule, f.location) for f in findings] == [("fact.unregistered", "L1")]


def test_fact_without_value_or_num(tmp_path):
    (tmp_path / "facts.yaml").write_text("empty:\n  source: 어딘가\n", encoding="utf-8")
    facts, _ = load_facts(tmp_path)
    text, findings = substitute("값은 {{empty}} 다.", facts, TODAY)
    assert text == "값은 {{empty}} 다."
    assert [f.rule for f in findings] == ["fact.no_value"]


def test_preview_marks_only_stale_facts(tmp_path):
    facts, derived = facts_of(tmp_path)
    text, _ = substitute(
        "시장 {{market_size}}, 참여자 {{pilot_n}}, 특허 {{patent}}.", facts, TODAY, derived, preview=True
    )
    assert text == f"시장 {MARKER_PREFIX} 재확인 필요: market_size -->3,200억 원, 참여자 67명, 특허 10-2024-0012345."
    assert has_markers(text)


def test_build_mode_inserts_no_markers(tmp_path):
    facts, derived = facts_of(tmp_path)
    text, _ = substitute("시장 {{market_size}}.", facts, TODAY, derived)
    assert text == "시장 3,200억 원."
    assert not has_markers(text)


def test_derived_marker_follows_its_inputs(tmp_path):
    """파생 fact 는 기한을 입력에서 상속한다 — 마커도 같은 기준을 따른다."""
    (tmp_path / "facts.yaml").write_text(
        textwrap.dedent(
            """\
            old:
              num: 160
              verified: 2025-01-01
              stability: volatile
              recheck_days: 90

            n:
              num: 67

            per_user:
              expr: "old / n"
            """
        ),
        encoding="utf-8",
    )
    facts, _ = load_facts(tmp_path)
    derived, _ = eval_all_derived(facts)
    text, _ = substitute("{{per_user}}", facts, TODAY, derived, preview=True)
    assert text.startswith(f"{MARKER_PREFIX} 재확인 필요: per_user -->")


# ── report.md ────────────────────────────────────────────────────────────


def test_report_groups_by_level(tmp_path):
    findings = [
        Finding(level="error", rule="fact.stale", message="기한 경과", location="draft.md:L4"),
        Finding(level="warn", rule="block.draft_used", message="draft 블록"),
        Finding(level="report", rule="exempt.usage", message="면제 마커"),
    ]
    text = render_report(findings, title="2026-08-tips-rnd")
    assert text.startswith(REPORT_HEADER)
    assert "# 2026-08-tips-rnd" in text
    assert "## 오류 (1건)" in text
    assert "- `fact.stale` — `draft.md:L4` — 기한 경과" in text
    assert "## 경고 (1건)" in text and "## 리포트 (1건)" in text
    assert "## 알림" not in text  # 0건인 레벨은 절 자체가 없다


def test_report_keeps_unknown_levels(tmp_path):
    text = render_report([Finding(level="wat", rule="x.y", message="어쩌지")])
    assert "알 수 없는 레벨 (1건)" in text


def test_write_report_is_utf8_lf(tmp_path):
    path = write_report(tmp_path, [])
    assert path.name == "report.md"
    assert "이상 없음" in path.read_text(encoding="utf-8")
    assert b"\r\n" not in path.read_bytes()
