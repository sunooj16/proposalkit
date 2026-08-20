"""cmd_import — 문단 분할과 후보 추출. 분해가 아니라 스캐폴드다."""

import textwrap

from ppsk.blocks import parse_frontmatter
from ppsk.commands.import_ import build, slugify, split_sections

DOC = textwrap.dedent(
    """\
    # 2025 사업계획서

    본 사업은 인지훈련 개인화를 목표로 한다. 기존 접근은 난이도 조절에 머물러 있다.

    ## 기술적 난제

    훈련 소재 자체의 개인화는 데이터 희소성 때문에 어렵다. 우리는 이를 해결했다.

    ## 실증 결과

    2025년 파일럿에서 참여자 42명이 참여했고, 총 3,200억 원 규모 시장을 대상으로 한다.
    """
)


def blocks_by_id(doc=DOC, source="archive/2025.md"):
    blocks, facts, tags = build(doc, source)
    parsed = {}
    for name, text in blocks:
        meta, body = parse_frontmatter(text)
        parsed[meta["id"]] = (meta, body)
    return parsed, facts, tags


def test_splits_on_headings():
    parsed, _, _ = blocks_by_id()

    assert list(parsed) == ["2025-사업계획서", "기술적-난제", "실증-결과"]
    assert "데이터 희소성" in parsed["기술적-난제"][1]
    assert "데이터 희소성" not in parsed["실증-결과"][1]


def test_every_candidate_is_draft_with_undecided_layer():
    """계층 판정은 사람이 한다. layer: TODO 는 허용값이 아니므로 그냥 옮기면 check 가 막는다."""
    parsed, _, _ = blocks_by_id()

    for meta, _ in parsed.values():
        assert meta["status"] == "draft"
        assert meta["layer"] == "TODO"
        assert meta["facts_used"] == [] and meta["tags"] == []


def test_source_location_is_recorded():
    parsed, _, _ = blocks_by_id()
    assert parsed["기술적-난제"][0]["import_source"].startswith("archive/2025.md#L")


def test_fact_candidates_are_extracted_with_location():
    _, facts, _ = blocks_by_id()

    assert '"42명"' in facts
    assert '"3,200억 원"' in facts
    assert "실증-결과" in facts
    assert "2025년" not in facts  # 연도는 주장이 아니다


def test_tag_candidates_come_from_headings():
    _, _, tags = blocks_by_id()

    lines = [l for l in tags.splitlines() if l and not l.startswith("#")]
    assert lines == ["2025 사업계획서", "기술적 난제", "실증 결과"]


def test_falls_back_to_paragraphs_without_headings():
    doc = "첫 문단은 충분히 길게 쓴다. " * 3 + "\n\n" + "둘째 문단도 충분히 길다. " * 3 + "\n\n짧음\n"
    sections = split_sections(doc)

    assert [title for title, _ in sections] == [None, None]  # 너무 짧은 조각은 블록이 아니다


def test_duplicate_headings_get_unique_ids():
    doc = "## 개요\n" + "같은 제목이 두 번 나온다. " * 3 + "\n\n## 개요\n" + "두 번째다. " * 5 + "\n"
    parsed, _, _ = blocks_by_id(doc)

    assert list(parsed) == ["개요", "개요-2"]


def test_slugify_keeps_hangul_and_drops_punctuation():
    assert slugify("기술적 난제 (2025)!") == "기술적-난제-2025"
    assert slugify("!!!") == "block"
