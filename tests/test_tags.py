"""tags.py — 어휘 로더, alias 정규화, 미등록 카운트."""

import textwrap

from ppsk.tags import load_tags

VOCAB = textwrap.dedent(
    """\
    _config:
      unregistered: warn

    기술난제:
      aliases: [기술적난제, 난제, technical-challenge]
      note: 해결이 어려운 기술적 문제 자체

    성능목표:
      aliases: [성능지표, KPI, 목표성능]

    시장규모:
      aliases: [시장크기, TAM]
    """
)


def write(root, text, name="tags.yaml"):
    (root / name).write_text(text, encoding="utf-8", newline="\n")
    return root


def test_alias_maps_to_canonical(tmp_path):
    tags, findings = load_tags(write(tmp_path, VOCAB))

    assert findings == []
    assert tags.normalize("난제") == "기술난제"
    assert tags.normalize("기술적난제") == "기술난제"
    assert tags.normalize("TAM") == "시장규모"
    assert tags.unregistered == {}


def test_canonical_passes_through(tmp_path):
    tags, _ = load_tags(write(tmp_path, VOCAB))
    assert tags.normalize("기술난제") == "기술난제"


def test_matching_ignores_case_and_spacing(tmp_path):
    tags, _ = load_tags(write(tmp_path, VOCAB))

    assert tags.normalize("kpi") == "성능목표"
    assert tags.normalize("Technical-Challenge") == "기술난제"
    assert tags.normalize("기술 난제") == "기술난제"
    assert tags.unregistered == {}


def test_unregistered_returns_input_and_counts(tmp_path):
    tags, _ = load_tags(write(tmp_path, VOCAB))

    assert tags.normalize_all(["현장검증", "규제대응", "현장검증", "현장검증"]) == [
        "현장검증",
        "규제대응",
        "현장검증",
        "현장검증",
    ]
    assert tags.unregistered == {"현장검증": 3, "규제대응": 1}


def test_unregistered_findings_sorted_by_count(tmp_path):
    tags, _ = load_tags(write(tmp_path, VOCAB))
    tags.normalize_all(["규제대응", "현장검증", "현장검증", "현장검증"])

    findings = tags.unregistered_findings()

    assert [f.rule for f in findings] == ["tag.unregistered"] * 2
    assert [f.level for f in findings] == ["warn", "warn"]
    assert "현장검증 (3회)" in findings[0].message
    assert "규제대응 (1회)" in findings[1].message


def test_config_promotes_unregistered_to_error(tmp_path):
    """어휘 안정화 후 tags.yaml 한 줄로 승격 — 코드 수정 없이."""
    tags, findings = load_tags(write(tmp_path, VOCAB.replace("unregistered: warn", "unregistered: error")))
    tags.normalize("현장검증")

    assert findings == []
    assert [f.level for f in tags.unregistered_findings()] == ["error"]


def test_bad_config_value_is_error_and_falls_back_to_warn(tmp_path):
    tags, findings = load_tags(write(tmp_path, VOCAB.replace("unregistered: warn", "unregistered: 치명적")))

    assert [f.rule for f in findings] == ["tags.malformed"]
    assert tags.unregistered_level == "warn"


def test_missing_file_is_empty_vocabulary_not_an_error(tmp_path):
    """어휘는 임포트 결과에서 귀납된다 — 초기에 비어 있는 것이 정상이다."""
    tags, findings = load_tags(tmp_path)

    assert findings == []
    assert tags.canonical == {}
    assert tags.normalize("기술난제") == "기술난제"
    assert tags.unregistered == {"기술난제": 1}


def test_config_only_file_loads(tmp_path):
    tags, findings = load_tags(write(tmp_path, "_config:\n  unregistered: error\n"))

    assert findings == []
    assert tags.canonical == {} and tags.unregistered_level == "error"


def test_entry_without_aliases_still_registers_canonical(tmp_path):
    tags, findings = load_tags(write(tmp_path, "기술난제:\n  note: alias 없음\n"))

    assert findings == []
    assert tags.normalize("기술난제") == "기술난제" and tags.unregistered == {}


def test_duplicate_alias_across_canonicals_is_error(tmp_path):
    """한 표기가 두 정규형을 가리키면 매칭이 조용히 어긋난다."""
    text = "기술난제:\n  aliases: [난제]\n성능목표:\n  aliases: [난제]\n"
    tags, findings = load_tags(write(tmp_path, text))

    assert [f.rule for f in findings] == ["tags.malformed"]
    assert tags.normalize("난제") == "기술난제"  # 먼저 선언된 쪽을 유지


def test_broken_yaml_is_error(tmp_path):
    tags, findings = load_tags(write(tmp_path, "기술난제:\n  aliases: [난제\n"))

    assert [f.rule for f in findings] == ["tags.malformed"]
    assert tags.canonical == {}
