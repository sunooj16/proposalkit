"""facts.py 로더 — 단일 파일 / facts/ 디렉터리, 파일 단위 소속 상속, id 중복."""

import textwrap
from datetime import date

from ppsk.facts import COUNT_THRESHOLD, load_facts

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
