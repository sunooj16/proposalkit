"""scaffold.py — 골격 생성. 템플릿 문구가 아니라 구조와 재실행 안전성을 본다."""

from ppsk.blocks import load_blocks
from ppsk.scaffold import scaffold
from ppsk.tags import load_tags


def test_creates_expected_skeleton(tmp_path):
    written, skipped = scaffold(tmp_path)

    assert skipped == []
    for rel in ("CLAUDE.md", "AGENTS.md", "facts.yaml", "tags.yaml", "docs/rules.md", "core/CHANGELOG.md"):
        assert (tmp_path / rel).is_file(), rel
    for rel in ("core/identity", "core/thesis", "evidence/market", "strategy/active", "proposals", "import"):
        assert (tmp_path / rel).is_dir(), rel
    assert {p.name for p in (tmp_path / "templates/angles").iterdir()} == {"rnd.md", "ir.md", "commercialization.md"}
    assert len(written) == len({rel for rel in written})


def test_pointer_files_point_at_rules(tmp_path):
    """두 파일을 따로 관리하면 반드시 어긋나므로 규약 원본은 docs/rules.md 하나다."""
    scaffold(tmp_path)

    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude == (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "docs/rules.md" in claude
    assert len(claude.splitlines()) == 1


def test_generated_repo_loads_clean(tmp_path):
    """갓 만든 리포지토리에서 ppsk 로더가 오류 없이 돈다 — 블록 0개, 어휘 비어 있음."""
    scaffold(tmp_path)

    blocks, block_findings = load_blocks(tmp_path)
    tags, tag_findings = load_tags(tmp_path)

    assert blocks == [] and block_findings == []
    assert tag_findings == [] and tags.canonical == {}
    assert tags.unregistered_level == "warn"


def test_rerun_skips_everything_and_keeps_edits(tmp_path):
    scaffold(tmp_path)
    (tmp_path / "tags.yaml").write_text("기술난제:\n  aliases: [난제]\n", encoding="utf-8")

    written, skipped = scaffold(tmp_path)

    assert written == []
    assert skipped
    tags, _ = load_tags(tmp_path)
    assert tags.normalize("난제") == "기술난제"  # 사람이 채운 내용이 살아 있다


def test_missing_files_are_restored_without_touching_others(tmp_path):
    scaffold(tmp_path)
    (tmp_path / "docs/rules.md").unlink()
    (tmp_path / "facts.yaml").write_text("# 내가 쓴 것\n", encoding="utf-8")

    written, _ = scaffold(tmp_path)

    assert [rel.as_posix() for rel in written] == ["docs/rules.md"]
    assert (tmp_path / "facts.yaml").read_text(encoding="utf-8") == "# 내가 쓴 것\n"
