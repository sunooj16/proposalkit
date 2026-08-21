"""check.py — Finding 수집·정렬·요약과 종료코드."""

import textwrap

from ppsk.check import counts, exit_code, run_checks, sort_findings, summary
from ppsk.model import Finding


def f(level, rule="x.y", message="m", location=None):
    return Finding(level=level, rule=rule, message=message, location=location)


def test_sort_puts_errors_first_then_rule_then_location():
    findings = sort_findings(
        [
            f("notice", "facts.count_threshold"),
            f("error", "block.malformed", location="core/b.md"),
            f("warn", "tag.unregistered"),
            f("error", "block.malformed", location="core/a.md"),
            f("report", "exempt.usage"),
        ]
    )
    assert [(x.level, x.location) for x in findings] == [
        ("error", "core/a.md"),
        ("error", "core/b.md"),
        ("warn", None),
        ("notice", None),
        ("report", None),
    ]


def test_sort_is_stable_across_input_order():
    findings = [f("warn", "b.r"), f("error", "a.r"), f("notice", "c.r")]
    assert [x.rule for x in sort_findings(findings)] == [x.rule for x in sort_findings(findings[::-1])]


def test_unknown_level_goes_last_not_silently_promoted():
    findings = sort_findings([f("wat"), f("report", "exempt.usage")])
    assert [x.level for x in findings] == ["report", "wat"]
    assert exit_code(findings) == 0


def test_exit_code_and_summary():
    assert exit_code([]) == 0
    assert summary([]) == "이상 없음"
    assert exit_code([f("warn"), f("notice")]) == 0
    assert summary([f("warn"), f("notice")]) == "warn 1, notice 1"
    assert exit_code([f("warn"), f("error")]) == 1
    assert counts([f("error"), f("error")])["error"] == 2


def repo(root, facts="", tags="", block=None):
    (root / "core" / "thesis").mkdir(parents=True)
    (root / "facts.yaml").write_text(facts, encoding="utf-8")
    (root / "tags.yaml").write_text(tags, encoding="utf-8")
    if block is not None:
        (root / "core" / "thesis" / "b.md").write_text(block, encoding="utf-8")
    return root


def test_run_checks_on_clean_repo_is_silent(tmp_path):
    repo(
        tmp_path,
        block=textwrap.dedent(
            """\
            ---
            id: core-claim
            layer: thesis
            status: active
            editable: strict
            summary: 한 줄 요약
            ---

            본문.
            """
        ),
    )
    assert run_checks(tmp_path) == []


def test_run_checks_gathers_from_every_loader(tmp_path):
    """깨진 파일 하나에서 멈추지 않고 전부 모은다."""
    repo(
        tmp_path,
        facts="a: [1, 2]\n",  # 매핑이 아님 → facts.malformed
        tags="- 하나\n",  # 최상위가 목록 → tags.malformed
        block="본문만 있고 frontmatter 가 없다\n",  # → block.malformed
    )
    (tmp_path / "projects.yaml").write_text("- 하나\n", encoding="utf-8")

    findings = run_checks(tmp_path)
    assert [x.rule for x in findings] == ["block.malformed", "facts.malformed", "projects.malformed", "tags.malformed"]
    assert exit_code(findings) == 1


def test_run_checks_evaluates_derived_facts(tmp_path):
    repo(tmp_path, facts=textwrap.dedent("""\
        n:
          value: "67명"
          num: 67

        ratio:
          expr: "n / missing_input"
        """))
    assert [x.rule for x in run_checks(tmp_path)] == ["derived.unknown_input"]
