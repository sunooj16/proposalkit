"""projects.py — 등록부 로더와 소속 판정."""

import textwrap

import pytest

from ppsk.projects import load_projects, selects

REGISTRY = textwrap.dedent(
    """\
    _config:
      unassigned: notice

    cogtrain:
      name: 인지훈련 개인화
      status: active
      aliases: [cog, 인지훈련]

    ncore:
      name: N-Core 플랫폼
      status: active

    legacy:
      name: 구형 사업
      status: archived
    """
)


def write(root, text=REGISTRY):
    (root / "projects.yaml").write_text(text, encoding="utf-8", newline="\n")
    return root


@pytest.mark.parametrize(
    "declared,project,expected",
    [
        ([], "cogtrain", True),  # 미선언 = 공용
        ([], None, True),
        (["cogtrain"], "cogtrain", True),
        (["cogtrain"], "ncore", False),  # 차단 — 이것이 프로젝트 축의 핵심
        (["cogtrain", "ncore"], "ncore", True),
        (["cogtrain"], None, True),  # 프로젝트 미지정 수집 = 전부
    ],
)
def test_selects(declared, project, expected):
    assert selects(declared, project) is expected


def test_resolve_accepts_id_and_alias(tmp_path):
    projects, findings = load_projects(write(tmp_path))

    assert findings == []
    assert projects.resolve("cogtrain") == "cogtrain"
    assert projects.resolve("cog") == "cogtrain"
    assert projects.resolve("인지훈련") == "cogtrain"
    assert projects.resolve("COG") == "cogtrain"  # 대소문자 무시


def test_unknown_project_resolves_to_none(tmp_path):
    """미등록은 오타다. 조용히 통과시키면 빈 결과가 나오고 이유를 알 수 없다."""
    projects, _ = load_projects(write(tmp_path))
    assert projects.resolve("cogtrian") is None


def test_resolve_all_splits_known_and_unknown(tmp_path):
    projects, _ = load_projects(write(tmp_path))

    resolved, unknown = projects.resolve_all(["cog", "없는프로젝트", "ncore", "cogtrain"])

    assert resolved == ["cogtrain", "ncore"]  # 중복 제거, 선언 순서 유지
    assert unknown == ["없는프로젝트"]


def test_archived_project_is_flagged(tmp_path):
    projects, _ = load_projects(write(tmp_path))

    assert projects.is_archived("legacy")
    assert projects.active_ids() == ["cogtrain", "ncore"]
    assert projects.name("cogtrain") == "인지훈련 개인화"


def test_missing_file_is_empty_registry_not_an_error(tmp_path):
    """프로젝트가 하나뿐인 리포지토리는 이 파일을 신경 쓰지 않아도 된다."""
    projects, findings = load_projects(tmp_path)

    assert findings == []
    assert projects.entries == {}
    assert projects.unassigned_level == "notice"
    assert selects([], None) is True


def test_config_level_can_be_promoted(tmp_path):
    projects, findings = load_projects(write(tmp_path, REGISTRY.replace("unassigned: notice", "unassigned: error")))

    assert findings == []
    assert projects.unassigned_level == "error"


def test_bad_config_level_is_error_and_falls_back(tmp_path):
    projects, findings = load_projects(write(tmp_path, REGISTRY.replace("unassigned: notice", "unassigned: 치명적")))

    assert [f.rule for f in findings] == ["projects.malformed"]
    assert projects.unassigned_level == "notice"


def test_bad_status_is_error_and_defaults_to_active(tmp_path):
    projects, findings = load_projects(write(tmp_path, "legacy:\n  status: 종료\n"))

    assert [f.rule for f in findings] == ["projects.malformed"]
    assert projects.is_archived("legacy") is False


def test_duplicate_alias_across_projects_is_error(tmp_path):
    text = "cogtrain:\n  aliases: [cog]\nncore:\n  aliases: [cog]\n"
    projects, findings = load_projects(write(tmp_path, text))

    assert [f.rule for f in findings] == ["projects.malformed"]
    assert projects.resolve("cog") == "cogtrain"  # 먼저 선언된 쪽을 유지


def test_entry_without_fields_still_registers(tmp_path):
    projects, findings = load_projects(write(tmp_path, "cogtrain:\nncore:\n"))

    assert findings == []
    assert projects.resolve("ncore") == "ncore"
    assert projects.name("ncore") == "ncore"


def test_broken_yaml_is_error(tmp_path):
    projects, findings = load_projects(write(tmp_path, "cogtrain:\n  aliases: [cog\n"))

    assert [f.rule for f in findings] == ["projects.malformed"]
    assert projects.entries == {}
