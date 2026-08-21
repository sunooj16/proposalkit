"""angle.py — angle.md 로더."""

import textwrap

from ppsk.angle import Angle, load_angle

FULL = textwrap.dedent(
    """\
    ---
    proposal_type: rnd
    project: cogtrain
    extends: templates/angles/rnd.md
    generated_from:
      - core/thesis/existing-limitation.md@8c1e04b
      - core/identity/team.md@1d90f77
    ---

    ## 강조
    - tag:기술난제 (강)
    - 성능목표
    - tag:시장규모 (배경)

    ## 고정 포함
    - core/thesis/core-claim        # 태그와 무관하게 반드시 포함

    ## 제외
    - strategy/pricing
    - strategy/gtm
    """
)


def write(tmp_path, text, name="angle.md"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_parses_every_section(tmp_path):
    angle, error = load_angle(write(tmp_path, FULL))
    assert error == ""
    assert (angle.project, angle.proposal_type, angle.extends) == ("cogtrain", "rnd", "templates/angles/rnd.md")
    assert angle.generated_from == [
        ("core/thesis/existing-limitation.md", "8c1e04b"),
        ("core/identity/team.md", "1d90f77"),
    ]
    assert angle.emphasis == [("기술난제", "강"), ("성능목표", "강"), ("시장규모", "배경")]
    assert angle.include == ["core/thesis/core-claim"]  # 줄 끝 주석은 잘린다
    assert angle.exclude == ["strategy/pricing", "strategy/gtm"]


def test_weights():
    angle = Angle()
    assert (angle.weight("강"), angle.weight("배경")) == (3, 1)
    assert angle.weight("모름") == 3  # 등급이 이상하면 강조로 본다 — 굳이 적었다면 올리려는 것이다


def test_template_with_empty_sections(tmp_path):
    """`ppsk new` 가 깔아주는 템플릿 상태. 빈 절은 빈 목록이지 오류가 아니다."""
    angle, error = load_angle(write(tmp_path, "---\nproposal_type: rnd\n---\n\n## 강조\n\n## 고정 포함\n\n## 제외\n"))
    assert error == ""
    assert (angle.emphasis, angle.include, angle.exclude, angle.project) == ([], [], [], None)


def test_generated_from_without_hash(tmp_path):
    """`ppsk collect` 이전에 손으로 적은 목록. 해시 대조는 못 하지만 사용 블록은 안다."""
    angle, _ = load_angle(write(tmp_path, "---\ngenerated_from: core/thesis/x.md\n---\n"))
    assert angle.generated_from == [("core/thesis/x.md", "")]


def test_malformed_returns_reason_not_exception(tmp_path):
    angle, error = load_angle(write(tmp_path, "frontmatter 가 없다\n"))
    assert angle is None
    assert "frontmatter" in error
