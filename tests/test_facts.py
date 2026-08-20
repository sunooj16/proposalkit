"""facts.py — 로더와 파생 fact 평가."""

import textwrap
from datetime import date

import pytest

from ppsk.facts import COUNT_THRESHOLD, eval_all_derived, eval_derived, load_facts

SINGLE = textwrap.dedent(
    """\
    pilot_n_2025:
      value: "참여자 67명"
      num: 67
      source: "2025 예비연구 결과보고서 p.7"
      verified: 2026-06-01
      stability: volatile
      recheck_days: 90

    patent_personalization:
      value: "10-2024-0012345"
      source: "특허등록원부"
      verified: 2026-01-10
      stability: fixed

    sessions_per_user_2025:
      expr: "total_sessions_2025 / pilot_n_2025"
      format: "1인당 {v:.1f}회"
    """
)


def write(root, text, name="facts.yaml"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return root


def rules(findings):
    return sorted(f.rule for f in findings)


def test_loads_single_file(tmp_path):
    facts, findings = load_facts(write(tmp_path, SINGLE))

    assert findings == []
    assert list(facts) == ["pilot_n_2025", "patent_personalization", "sessions_per_user_2025"]

    pilot = facts["pilot_n_2025"]
    assert pilot.value == "참여자 67명"
    assert pilot.num == 67
    assert pilot.verified == date(2026, 6, 1)
    assert pilot.stability == "volatile"
    assert pilot.recheck_days == 90
    assert pilot.derived is False


def test_derived_fact_is_flagged(tmp_path):
    facts, _ = load_facts(write(tmp_path, SINGLE))

    derived = facts["sessions_per_user_2025"]
    assert derived.derived is True
    assert derived.expr == "total_sessions_2025 / pilot_n_2025"
    assert derived.num is None


def test_directory_wins_over_single_file(tmp_path):
    """분할은 파일 이동 한 번이어야 한다 — facts/ 가 있으면 그쪽만 읽는다."""
    write(tmp_path, "only_in_single:\n  value: \"낡은 값\"\n")
    write(tmp_path, "in_dir:\n  value: \"새 값\"\n", name="facts/market.yaml")

    facts, findings = load_facts(tmp_path)

    assert findings == []
    assert list(facts) == ["in_dir"]


def test_directory_files_are_merged_in_path_order(tmp_path):
    write(tmp_path, "b_fact:\n  value: \"b\"\n", name="facts/b.yaml")
    write(tmp_path, "a_fact:\n  value: \"a\"\n", name="facts/a.yaml")

    facts, findings = load_facts(tmp_path)

    assert findings == []
    assert list(facts) == ["a_fact", "b_fact"]  # 출력이 재현 가능해야 한다


def test_duplicate_id_across_files_is_error(tmp_path):
    """id 가 전역 유일이어야 {{fact_id}} 참조가 분할에도 흔들리지 않는다."""
    write(tmp_path, "shared_id:\n  value: \"먼저\"\n", name="facts/a.yaml")
    write(tmp_path, "shared_id:\n  value: \"나중\"\n", name="facts/b.yaml")

    facts, findings = load_facts(tmp_path)

    assert rules(findings) == ["facts.duplicate_id"]
    assert facts["shared_id"].value == "먼저"  # 먼저 읽은 쪽을 유지


def test_file_project_is_inherited(tmp_path):
    text = "_project: cogtrain\n\na:\n  value: \"가\"\n\nb:\n  value: \"나\"\n"
    facts, findings = load_facts(write(tmp_path, text, name="facts/cogtrain.yaml"))

    assert findings == []
    assert facts["a"].projects == ["cogtrain"]
    assert facts["b"].projects == ["cogtrain"]


def test_entry_projects_override_file_default(tmp_path):
    text = "_project: cogtrain\n\nshared:\n  value: \"둘 다\"\n  projects: [cogtrain, ncore]\n"
    facts, _ = load_facts(write(tmp_path, text, name="facts/cogtrain.yaml"))

    assert facts["shared"].projects == ["cogtrain", "ncore"]


def test_without_project_declaration_fact_is_shared(tmp_path):
    facts, _ = load_facts(write(tmp_path, SINGLE))

    assert facts["pilot_n_2025"].projects == []


def test_project_accepts_single_string_on_entry(tmp_path):
    facts, findings = load_facts(write(tmp_path, "a:\n  value: \"가\"\n  projects: cogtrain\n"))

    assert findings == []
    assert facts["a"].projects == ["cogtrain"]


def test_count_threshold_is_a_notice_not_a_failure(tmp_path):
    text = "".join(f"fact_{i:03d}:\n  value: \"{i}\"\n" for i in range(COUNT_THRESHOLD + 1))
    facts, findings = load_facts(write(tmp_path, text))

    assert len(facts) == COUNT_THRESHOLD + 1
    assert [f.level for f in findings] == ["notice"]
    assert rules(findings) == ["facts.count_threshold"]


def test_count_threshold_is_not_raised_at_the_boundary(tmp_path):
    text = "".join(f"fact_{i:03d}:\n  value: \"{i}\"\n" for i in range(COUNT_THRESHOLD))
    _, findings = load_facts(write(tmp_path, text))

    assert findings == []


def test_missing_files_are_not_an_error(tmp_path):
    facts, findings = load_facts(tmp_path)

    assert facts == {} and findings == []


def test_bad_field_types_are_errors_and_skip_the_fact(tmp_path):
    text = textwrap.dedent(
        """\
        good:
          value: "정상"
        bad_num:
          value: "숫자 아님"
          num: 사십이
        bad_date:
          value: "날짜 아님"
          verified: 어제
        bad_stability:
          value: "등급 아님"
          stability: 영구
        """
    )
    facts, findings = load_facts(write(tmp_path, text))

    assert list(facts) == ["good"]
    assert rules(findings) == ["facts.malformed"] * 3


def test_unknown_field_is_warn_and_fact_still_loads(tmp_path):
    facts, findings = load_facts(write(tmp_path, "a:\n  value: \"가\"\n  valid_until: 2027-01-01\n"))

    assert list(facts) == ["a"]  # 경고지 거부가 아니다
    assert rules(findings) == ["facts.unknown_field"]
    assert findings[0].level == "warn"


def test_broken_yaml_is_error(tmp_path):
    facts, findings = load_facts(write(tmp_path, "a:\n  value: \"닫히지 않음\n"))

    assert facts == {}
    assert rules(findings) == ["facts.malformed"]


def test_entry_that_is_not_a_mapping_is_error(tmp_path):
    facts, findings = load_facts(write(tmp_path, 'a: "값만 적음"\nb:\n  value: "정상"\n'))

    assert list(facts) == ["b"]
    assert rules(findings) == ["facts.malformed"]


# ── 파생 fact 평가 (T-09) ────────────────────────────────────────────────

DERIVED = textwrap.dedent(
    """\
    pilot_n_2025:
      value: "참여자 67명"
      num: 67
      source: "예비연구 결과보고서 p.7"
      verified: 2026-06-01
      stability: volatile
      recheck_days: 90

    total_sessions_2025:
      value: "총 161회"
      num: 161
      source: "세션 로그 집계"
      verified: 2026-03-01
      stability: volatile
      recheck_days: 180

    patent_no:
      value: "10-2024-0012345"
      num: 1
      source: "특허등록원부"
      verified: 2020-01-01
      stability: fixed

    sessions_per_user:
      expr: "total_sessions_2025 / pilot_n_2025"
      format: "1인당 {v:.1f}회"
    """
)


def derived_from(tmp_path, text=DERIVED):
    facts, findings = load_facts(write(tmp_path, text))
    assert [f for f in findings if f.level == "error"] == []
    return facts


def test_derived_value_is_computed_and_formatted(tmp_path):
    facts = derived_from(tmp_path)
    results, findings = eval_all_derived(facts)

    assert findings == []
    assert results["sessions_per_user"].value == "1인당 2.4회"
    assert results["sessions_per_user"].inputs == ["total_sessions_2025", "pilot_n_2025"]


def test_verified_is_inherited_as_the_oldest_input(tmp_path):
    facts = derived_from(tmp_path)
    result, _ = eval_derived(facts["sessions_per_user"], facts)

    assert result.verified == date(2026, 3, 1)  # 둘 중 오래된 쪽


def test_recheck_due_is_the_earliest_deadline(tmp_path):
    facts = derived_from(tmp_path)
    result, _ = eval_derived(facts["sessions_per_user"], facts)

    # pilot 2026-06-01 + 90일 = 2026-08-30, sessions 2026-03-01 + 180일 = 2026-08-28
    assert result.recheck_due == date(2026, 8, 28)


def test_fixed_input_is_excluded_from_the_deadline(tmp_path):
    """특허번호·설립일은 영구 통과다. 기한 계산에 끼면 파생이 상시 만료된다."""
    text = DERIVED.replace(
        'sessions_per_user:\n  expr: "total_sessions_2025 / pilot_n_2025"',
        'with_patent:\n  expr: "patent_no * 2"',
    )
    facts = derived_from(tmp_path, text)
    result, findings = eval_derived(facts["with_patent"], facts)

    assert findings == []
    assert result.recheck_due is None


def test_source_lists_inputs_and_the_expression(tmp_path):
    facts = derived_from(tmp_path)
    result, _ = eval_derived(facts["sessions_per_user"], facts)

    assert "세션 로그 집계" in result.source
    assert "예비연구 결과보고서 p.7" in result.source
    assert "계산: total_sessions_2025 / pilot_n_2025" in result.source


def test_derived_may_not_declare_inherited_fields(tmp_path):
    """선언하면 같은 값에 소유자가 둘 생긴다 (기획 8장)."""
    text = DERIVED + '  verified: 2026-08-01\n  source: "직접 적음"\n'
    facts, _ = load_facts(write(tmp_path, text))
    result, findings = eval_derived(facts["sessions_per_user"], facts)

    assert result is None
    assert rules(findings) == ["derived.forbidden_field"] * 2


def test_derived_may_not_reference_another_derived(tmp_path):
    text = DERIVED + '\nnested:\n  expr: "sessions_per_user * 2"\n  format: "{v}"\n'
    facts = derived_from(tmp_path, text)
    result, findings = eval_derived(facts["nested"], facts)

    assert result is None
    assert rules(findings) == ["derived.nested"]


def test_input_without_num_is_error(tmp_path):
    """'참여자 42명'에서 42를 자동 추출하지 않는다 — 조용히 틀릴 위험이 크다."""
    text = 'headcount:\n  value: "직원 12명"\n\ndouble:\n  expr: "headcount * 2"\n  format: "{v}"\n'
    facts = derived_from(tmp_path, text)
    result, findings = eval_derived(facts["double"], facts)

    assert result is None
    assert rules(findings) == ["derived.missing_num"]


def test_unknown_input_is_error(tmp_path):
    text = 'a:\n  expr: "nowhere * 2"\n  format: "{v}"\n'
    facts = derived_from(tmp_path, text)
    _, findings = eval_derived(facts["a"], facts)

    assert rules(findings) == ["derived.unknown_input"]


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os').system('echo')",  # 함수 호출
        "open('secret').read()",
        "pilot_n_2025.__class__",  # 속성 접근
        "[pilot_n_2025]",  # 자료구조
        "pilot_n_2025 if 1 else 2",  # 조건식
        "pilot_n_2025 ** 99999999",  # 허용하지 않은 연산자
        "lambda: 1",
    ],
)
def test_expression_whitelist_rejects_anything_else(tmp_path, expr):
    """eval() 에 문자열을 넘기지 않는다. 허용 노드 밖은 전부 거부한다."""
    facts = derived_from(tmp_path, f'a:\n  expr: "{expr}"\n  format: "{{v}}"\n')
    result, findings = eval_derived(facts["a"], facts)

    assert result is None
    assert rules(findings) == ["derived.invalid_expr"]


def test_arithmetic_and_constants_are_allowed(tmp_path):
    text = 'n:\n  num: 10\n  value: "10"\n\ncalc:\n  expr: "-(n + 2) * 3 - 4 / 2"\n  format: "{v:g}"\n'
    facts = derived_from(tmp_path, text)
    result, findings = eval_derived(facts["calc"], facts)

    assert findings == []
    assert result.value == "-38"


def test_division_by_zero_is_error_not_a_crash(tmp_path):
    text = 'z:\n  num: 0\n  value: "0"\n\nbad:\n  expr: "10 / z"\n  format: "{v}"\n'
    facts = derived_from(tmp_path, text)
    result, findings = eval_derived(facts["bad"], facts)

    assert result is None
    assert rules(findings) == ["derived.invalid_expr"]


def test_format_must_have_exactly_one_slot(tmp_path):
    text = 'n:\n  num: 2\n  value: "2"\n\nbad:\n  expr: "n * 2"\n  format: "{v} 와 {v}"\n'
    facts = derived_from(tmp_path, text)
    result, findings = eval_derived(facts["bad"], facts)

    assert result is None
    assert rules(findings) == ["derived.invalid_format"]


def test_format_slot_must_be_v(tmp_path):
    text = 'n:\n  num: 2\n  value: "2"\n\nbad:\n  expr: "n * 2"\n  format: "{value}"\n'
    facts = derived_from(tmp_path, text)
    _, findings = eval_derived(facts["bad"], facts)

    assert rules(findings) == ["derived.invalid_format"]


def test_format_is_optional(tmp_path):
    text = 'n:\n  num: 2\n  value: "2"\n\nplain:\n  expr: "n * 3"\n'
    facts = derived_from(tmp_path, text)
    result, findings = eval_derived(facts["plain"], facts)

    assert findings == []
    assert result.value == "6"


def test_eval_all_derived_skips_plain_facts(tmp_path):
    facts = derived_from(tmp_path)
    results, findings = eval_all_derived(facts)

    assert list(results) == ["sessions_per_user"]
    assert findings == []
