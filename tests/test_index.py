"""cmd_index — 인덱스 내용의 문자열 포맷이 아니라 무엇이 담기는지를 본다."""

import textwrap

from ppsk.commands.index import render
from ppsk.blocks import load_blocks
from ppsk.tags import load_tags

BLOCK = textwrap.dedent(
    """\
    ---
    id: {id}
    layer: {layer}
    status: {status}
    editable: free
    tags: [{tags}]
    summary: {summary}
    ---
    본문이다.
    """
)


def build(tmp_path, blocks, vocabulary=None):
    for rel, fields in blocks.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BLOCK.format(**fields), encoding="utf-8", newline="\n")
    if vocabulary is not None:
        (tmp_path / "tags.yaml").write_text(vocabulary, encoding="utf-8", newline="\n")
    loaded, _ = load_blocks(tmp_path)
    tags, _ = load_tags(tmp_path)
    return render(loaded, tags)


def fields(**kwargs):
    base = dict(id="x", layer="thesis", status="active", tags="", summary="요약")
    base.update(kwargs)
    return base


def test_lists_path_layer_tags_and_summary(tmp_path):
    text = build(
        tmp_path,
        {"core/thesis/claim.md": fields(id="claim", tags="기술난제", summary="우리 주장")},
    )

    assert "core/thesis/claim.md" in text
    assert "## thesis" in text
    assert "기술난제" in text
    assert "우리 주장" in text


def test_tags_are_normalized_to_canonical(tmp_path):
    """블록은 `난제` 로 태깅돼 있어도 인덱스에는 정규형이 실린다."""
    text = build(
        tmp_path,
        {"core/thesis/claim.md": fields(id="claim", tags="난제")},
        vocabulary="기술난제:\n  aliases: [난제]\n",
    )

    assert "기술난제" in text
    assert "| 난제 |" not in text


def test_layers_are_grouped_in_fixed_order(tmp_path):
    text = build(
        tmp_path,
        {
            "strategy/gtm.md": fields(id="gtm", layer="strategy"),
            "core/identity/team.md": fields(id="team", layer="identity"),
            "evidence/pilot.md": fields(id="pilot", layer="evidence"),
        },
    )

    assert [l for l in text.splitlines() if l.startswith("## ")] == [
        "## identity",
        "## evidence",
        "## strategy",
    ]


def test_draft_blocks_are_marked(tmp_path):
    text = build(
        tmp_path,
        {
            "evidence/a.md": fields(id="a", layer="evidence", status="draft"),
            "evidence/b.md": fields(id="b", layer="evidence"),
        },
    )

    lines = [l for l in text.splitlines() if l.startswith("| `evidence")]
    assert "*(draft)*" in lines[0]
    assert "*(draft)*" not in lines[1]


def test_pipe_in_summary_does_not_break_table(tmp_path):
    text = build(tmp_path, {"evidence/a.md": fields(id="a", layer="evidence", summary="A | B")})

    row = [l for l in text.splitlines() if l.startswith("| `evidence")][0]
    assert r"A \| B" in row
    assert len(row.split(" | ")) == 3  # 경로 | 태그 | 요약


def test_marked_generated_and_stable_across_runs(tmp_path):
    blocks = {"core/thesis/claim.md": fields(id="claim", tags="기술난제")}
    first = build(tmp_path, blocks)
    second = build(tmp_path, blocks)

    assert first.splitlines()[0].startswith("<!-- 자동 생성")
    assert first == second


def test_empty_repository_gives_usable_index(tmp_path):
    (tmp_path / "core").mkdir()
    text = build(tmp_path, {})

    assert "ppsk import" in text
