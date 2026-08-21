"""cmd_new — 제안서 스캐폴드와 angle 템플릿 상속."""

from datetime import date

from ppsk.angle import load_angle
from ppsk.commands.new import angle_types, build_angle, create, dirname
from ppsk.scaffold import scaffold

TODAY = date(2026, 8, 21)


def repo(tmp_path):
    scaffold(tmp_path)
    return tmp_path


def test_dirname_is_year_month_prefixed():
    assert dirname("tips-rnd", TODAY) == "2026-08-tips-rnd"


def test_creates_four_files_and_no_generated_ones(tmp_path):
    target, files, error = create(repo(tmp_path), "tips-rnd", "rnd", today=TODAY)
    assert error == ""
    assert files == ["angle.md", "brief.md", "deviations.md", "draft.md"]
    assert target == tmp_path / "proposals" / "2026-08-tips-rnd"
    # final.md / report.md 는 build·check 만이 만든다. 빈 파일이 놓이면 통과한 산출물처럼 보인다.
    assert not (target / "final.md").exists()
    assert not (target / "report.md").exists()


def test_angle_inherits_template_body(tmp_path):
    target, _, _ = create(repo(tmp_path), "tips-rnd", "rnd", project="cogtrain", today=TODAY)
    angle, error = load_angle(target / "angle.md")
    assert error == ""
    assert (angle.proposal_type, angle.project, angle.extends) == ("rnd", "cogtrain", "templates/angles/rnd.md")
    # 템플릿의 강조 태그가 그대로 내려온다.
    assert ("기술난제", "강") in angle.emphasis


def test_project_omitted_leaves_a_commented_slot(tmp_path):
    target, _, _ = create(repo(tmp_path), "ir-2026", "ir", today=TODAY)
    text = (target / "angle.md").read_text(encoding="utf-8")
    assert "# project:" in text
    angle, _ = load_angle(target / "angle.md")
    assert angle.project is None


def test_unknown_type_lists_available(tmp_path):
    target, files, error = create(repo(tmp_path), "x", "없는유형", today=TODAY)
    assert target is None and files == []
    assert "ir" in error and "rnd" in error
    assert not (tmp_path / "proposals" / "2026-08-x").exists()


def test_angle_types_reads_the_repository_not_the_package(tmp_path):
    root = repo(tmp_path)
    (root / "templates" / "angles" / "govtech.md").write_text("---\nproposal_type: govtech\n---\n\n## 강조\n", "utf-8")
    assert "govtech" in angle_types(root)
    target, _, error = create(root, "g", "govtech", today=TODAY)
    assert error == "" and (target / "angle.md").exists()


def test_existing_directory_is_never_overwritten(tmp_path):
    root = repo(tmp_path)
    target, _, _ = create(root, "tips-rnd", "rnd", today=TODAY)
    (target / "draft.md").write_text("작업 중인 초안\n", encoding="utf-8")

    again, files, error = create(root, "tips-rnd", "rnd", today=TODAY)
    assert again is None and files == []
    assert "이미 있다" in error
    assert (target / "draft.md").read_text(encoding="utf-8") == "작업 중인 초안\n"


def test_slug_cannot_escape_the_proposals_directory(tmp_path):
    for bad in ("../evil", "a/b", ".hidden", ""):
        target, _, error = create(repo(tmp_path) if bad == "../evil" else tmp_path, bad, "rnd", today=TODAY)
        assert target is None and "slug" in error


def test_build_angle_reports_broken_template():
    text, error = build_angle("frontmatter 가 없다\n", "rnd")
    assert text is None and "frontmatter" in error
