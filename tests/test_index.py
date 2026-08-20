"""cmd_index — 인덱스 내용의 문자열 포맷이 아니라 무엇이 담기는지를 본다."""

import textwrap

from ppsk.commands.index import render
from ppsk.blocks import load_blocks
from ppsk.projects import load_projects
from ppsk.tags import load_tags

BLOCK = textwrap.dedent(
    """\
    ---
    id: {id}
    layer: {layer}
    status: {status}
    editable: free
    tags: [{tags}]
    projects: [{projects}]
    summary: {summary}
    ---
    본문이다.
    """
)


REGISTRY = "cogtrain:\n  name: 인지훈련 개인화\nncore:\n  name: N-Core 플랫폼\n"


def build(tmp_path, blocks, vocabulary=None, project=None, registry=None):
    for rel, fields in blocks.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BLOCK.format(**fields), encoding="utf-8", newline="\n")
    if vocabulary is not None:
        (tmp_path / "tags.yaml").write_text(vocabulary, encoding="utf-8", newline="\n")
    if registry is not None:
        (tmp_path / "projects.yaml").write_text(registry, encoding="utf-8", newline="\n")
    loaded, _ = load_blocks(tmp_path)
    tags, _ = load_tags(tmp_path)
    projects, _ = load_projects(tmp_path)
    return render(loaded, tags, project, projects)


def fields(**kwargs):
    base = dict(id="x", layer="thesis", status="active", tags="", projects="", summary="요약")
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
    assert len(row.split(" | ")) == 4  # 경로 | 프로젝트 | 태그 | 요약


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


def test_project_filter_keeps_shared_blocks(tmp_path):
    """공용 블록은 어느 프로젝트 인덱스에도 실린다 — 회사 소개가 그런 블록이다."""
    text = build(
        tmp_path,
        {
            "core/identity/company.md": fields(id="company", layer="identity"),
            "evidence/cog.md": fields(id="cog", layer="evidence", projects="cogtrain"),
            "evidence/ncore.md": fields(id="ncore", layer="evidence", projects="ncore"),
        },
        project="cogtrain",
        registry=REGISTRY,
    )

    assert "core/identity/company.md" in text
    assert "evidence/cog.md" in text
    assert "evidence/ncore.md" not in text  # 차단 — 다른 사업의 근거가 새면 안 된다


def test_without_project_everything_is_listed(tmp_path):
    text = build(
        tmp_path,
        {
            "evidence/cog.md": fields(id="cog", layer="evidence", projects="cogtrain"),
            "evidence/ncore.md": fields(id="ncore", layer="evidence", projects="ncore"),
        },
        registry=REGISTRY,
    )

    assert "evidence/cog.md" in text and "evidence/ncore.md" in text


def test_project_column_shows_owner_or_shared(tmp_path):
    text = build(
        tmp_path,
        {
            "core/identity/company.md": fields(id="company", layer="identity"),
            "evidence/cog.md": fields(id="cog", layer="evidence", projects="cogtrain"),
        },
        registry=REGISTRY,
    )

    rows = {l.split("|")[1].strip(): l.split("|")[2].strip() for l in text.splitlines() if l.startswith("| `")}
    assert rows["`core/identity/company.md`"] == "공용"
    assert rows["`evidence/cog.md`"] == "cogtrain"
