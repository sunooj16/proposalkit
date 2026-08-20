"""blocks.py — frontmatter 파싱, 필수 필드 판정, 본문 해시."""

import textwrap
from datetime import date

import pytest

from ppsk.blocks import FrontmatterError, load_block, load_blocks, parse_frontmatter, sha

GOOD = textwrap.dedent(
    """\
    ---
    id: thesis-core-claim
    layer: thesis
    status: active
    editable: free
    last_verified: 2026-07-10
    facts_used: [patent_personalization, pilot_n_2025]
    tags: [기술난제, 개인화]
    summary: 우리는 훈련 소재를 개인화한다
    ---
    기존 개인화는 난이도 조절에 머물러 있다.
    """
)


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def rules(findings):
    return sorted(f.rule for f in findings)


def test_parse_frontmatter_splits_meta_and_body():
    meta, body = parse_frontmatter(GOOD)
    assert meta["id"] == "thesis-core-claim"
    assert meta["last_verified"] == date(2026, 7, 10)
    assert body.startswith("기존 개인화는")
    assert "---" not in body


@pytest.mark.parametrize(
    "text",
    [
        "구분자가 아예 없는 본문\n",
        "---\nid: x\n본문만 있고 닫는 구분자가 없다\n",
        "본문 먼저\n---\nid: x\n---\n",  # 파일 첫 줄이 `---` 여야 한다
    ],
)
def test_parse_frontmatter_requires_both_delimiters(text):
    with pytest.raises(FrontmatterError):
        parse_frontmatter(text)


def test_sha_is_crlf_insensitive():
    """이 정규화를 빼면 core.lock이 체크아웃 환경마다 달라져 잠금이 무의미해진다."""
    assert sha("한 줄\r\n다음 줄\r\n") == sha("한 줄\n다음 줄\n")


def test_sha_ignores_surrounding_blank_lines_but_not_content():
    assert sha("\n본문\n\n") == sha("본문")
    assert sha("본문") != sha("본 문")


def test_load_block_reads_all_fields(tmp_path):
    path = write(tmp_path, "core/thesis/claim.md", GOOD)
    block, findings = load_block(path, tmp_path)

    assert findings == []
    assert block.id == "thesis-core-claim"
    assert block.path.as_posix() == "core/thesis/claim.md"
    assert block.layer == "thesis"
    assert block.last_verified == date(2026, 7, 10)
    assert block.facts_used == ["patent_personalization", "pilot_n_2025"]
    assert block.tags == ["기술난제", "개인화"]
    assert block.sha == sha(block.body)


def test_missing_required_field_is_error(tmp_path):
    text = GOOD.replace("summary: 우리는 훈련 소재를 개인화한다\n", "")
    path = write(tmp_path, "core/thesis/claim.md", text)
    block, findings = load_block(path, tmp_path)

    assert block is None
    assert rules(findings) == ["block.malformed"]
    assert "summary" in findings[0].message


def test_bad_enum_value_is_error(tmp_path):
    path = write(tmp_path, "core/thesis/claim.md", GOOD.replace("layer: thesis", "layer: 주장"))
    block, findings = load_block(path, tmp_path)

    assert block is None
    assert [f.level for f in findings] == ["error"]


def test_unknown_field_is_warn_and_block_still_loads(tmp_path):
    path = write(tmp_path, "core/thesis/claim.md", GOOD.replace("layer: thesis", "layer: thesis\nangles: [rnd]"))
    block, findings = load_block(path, tmp_path)

    assert block is not None  # 경고지 거부가 아니다
    assert rules(findings) == ["block.unknown_field"]
    assert findings[0].level == "warn"


def test_optional_fields_default_to_empty(tmp_path):
    text = textwrap.dedent(
        """\
        ---
        id: minimal
        layer: identity
        status: draft
        editable: strict
        summary: 최소 블록
        ---
        본문
        """
    )
    block, findings = load_block(write(tmp_path, "core/minimal.md", text), tmp_path)

    assert findings == []
    assert block.last_verified is None
    assert block.facts_used == [] and block.tags == []


def test_load_blocks_scans_only_block_dirs_and_skips_changelog(tmp_path):
    write(tmp_path, "core/thesis/claim.md", GOOD)
    write(tmp_path, "evidence/pilot.md", GOOD.replace("id: thesis-core-claim", "id: pilot"))
    write(tmp_path, "strategy/tone.md", GOOD.replace("id: thesis-core-claim", "id: tone"))
    write(tmp_path, "core/CHANGELOG.md", "# 변경 이력\n프론트매터 없음\n")
    write(tmp_path, "docs/plan.md", "# 기획\n프론트매터 없음\n")
    write(tmp_path, "import/old/candidate.md", "프론트매터 없음\n")

    blocks, findings = load_blocks(tmp_path)

    assert findings == []
    assert [b.id for b in blocks] == ["thesis-core-claim", "pilot", "tone"]


def test_load_blocks_continues_past_broken_file(tmp_path):
    write(tmp_path, "core/aaa-broken.md", "프론트매터 없음\n")
    write(tmp_path, "core/bbb-good.md", GOOD)

    blocks, findings = load_blocks(tmp_path)

    assert [b.id for b in blocks] == ["thesis-core-claim"]
    assert rules(findings) == ["block.malformed"]


def test_load_blocks_is_sorted_by_path(tmp_path):
    for name in ("core/z.md", "core/a.md", "evidence/m.md"):
        write(tmp_path, name, GOOD.replace("id: thesis-core-claim", f"id: {name}"))

    blocks, _ = load_blocks(tmp_path)

    assert [b.path.as_posix() for b in blocks] == ["core/a.md", "core/z.md", "evidence/m.md"]


def test_projects_field_is_parsed(tmp_path):
    path = write(tmp_path, "core/thesis/claim.md", GOOD.replace("tags: [기술난제, 개인화]", "tags: []\nprojects: [cogtrain, ncore]"))
    block, findings = load_block(path, tmp_path)

    assert findings == []
    assert block.projects == ["cogtrain", "ncore"]


def test_projects_accepts_single_string(tmp_path):
    path = write(tmp_path, "core/thesis/claim.md", GOOD.replace("tags: [기술난제, 개인화]", "projects: cogtrain"))
    block, findings = load_block(path, tmp_path)

    assert findings == []
    assert block.projects == ["cogtrain"]


def test_missing_projects_means_shared(tmp_path):
    """선언이 없으면 전 프로젝트 공용이다 — 회사 소개·팀이 그런 블록이다."""
    block, findings = load_block(write(tmp_path, "core/identity/company.md", GOOD), tmp_path)

    assert findings == []
    assert block.projects == []


def test_unregistered_project_is_not_judged_here(tmp_path):
    """미등록 판정은 blocks 가 아니라 check 이 한다. 여기서는 원문을 그대로 싣는다."""
    path = write(tmp_path, "core/thesis/claim.md", GOOD.replace("tags: [기술난제, 개인화]", "projects: [오타난프로젝트]"))
    block, findings = load_block(path, tmp_path)

    assert findings == []
    assert block.projects == ["오타난프로젝트"]
