"""cmd_collect — 프로젝트 하드 필터 → 태그 가중치 정렬 + generated_from 갱신."""

import textwrap

from ppsk.angle import Angle, load_angle, update_generated_from
from ppsk.blocks import load_blocks
from ppsk.commands.collect import render, select, weights_of
from ppsk.projects import load_projects
from ppsk.tags import load_tags

TAGS = "기술난제:\n  aliases: [난제]\n시장규모: {}\n가격: {}\n"
REGISTRY = "cogtrain:\n  name: 인지훈련\nad_samd:\n  name: AD SaMD\n"

ANGLE = textwrap.dedent(
    """\
    ---
    proposal_type: rnd
    ---

    ## 강조
    - tag:기술난제 (강)
    - tag:시장규모 (배경)

    ## 고정 포함

    ## 제외
    """
)


def block(path, tags=(), projects=(), layer="thesis", body="본문.", status="active"):
    front = [f"id: {path.split('/')[-1]}", f"layer: {layer}", f"status: {status}", "editable: strict", "summary: 요약"]
    if tags:
        front.append(f"tags: [{', '.join(tags)}]")
    if projects:
        front.append(f"projects: [{', '.join(projects)}]")
    return path, "---\n" + "\n".join(front) + "\n---\n\n" + body + "\n"


def repo(tmp_path, *blocks, angle=ANGLE, tags=TAGS, projects=REGISTRY):
    (tmp_path / "tags.yaml").write_text(tags, encoding="utf-8")
    (tmp_path / "projects.yaml").write_text(projects, encoding="utf-8")
    for path, text in blocks:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    proposal = tmp_path / "proposals" / "2026-08-tips-rnd"
    proposal.mkdir(parents=True)
    (proposal / "angle.md").write_text(angle, encoding="utf-8")
    return proposal


def run_select(tmp_path, proposal, project=None):
    blocks, _ = load_blocks(tmp_path)
    tags, _ = load_tags(tmp_path)
    angle, _ = load_angle(proposal / "angle.md")
    return [(score, b.path.as_posix()) for score, _pinned, b in select(blocks, angle, tags, project)]


def test_weights_take_the_stronger_duplicate():
    tags, _ = load_tags("nowhere")  # tags.yaml 부재 = 빈 어휘
    weights = weights_of(Angle(emphasis=[("기술난제", "배경"), ("기술난제", "강")]), tags)
    assert weights == {"기술난제": 3}


def test_scores_sum_matching_tags_and_sort_descending(tmp_path):
    proposal = repo(
        tmp_path,
        block("core/thesis/both.md", tags=["기술난제", "시장규모"]),  # 3 + 1
        block("core/thesis/strong.md", tags=["난제"]),  # alias → 3
        block("core/thesis/weak.md", tags=["시장규모"]),  # 1
        block("strategy/active/none.md", tags=["가격"], layer="strategy"),  # 0 — 안 뽑힌다
    )
    assert run_select(tmp_path, proposal) == [
        (4, "core/thesis/both.md"),
        (3, "core/thesis/strong.md"),
        (1, "core/thesis/weak.md"),
    ]


def test_ties_break_on_path_for_reproducibility(tmp_path):
    proposal = repo(
        tmp_path,
        block("core/thesis/b.md", tags=["기술난제"]),
        block("core/thesis/a.md", tags=["기술난제"]),
        block("evidence/market/c.md", tags=["기술난제"], layer="evidence"),
    )
    first = run_select(tmp_path, proposal)
    assert first == [(3, "core/thesis/a.md"), (3, "core/thesis/b.md"), (3, "evidence/market/c.md")]
    assert run_select(tmp_path, proposal) == first


def test_project_filter_runs_before_sorting(tmp_path):
    """점수가 아무리 높아도 남의 사업 블록은 후보에 없다."""
    proposal = repo(
        tmp_path,
        block("core/thesis/theirs.md", tags=["기술난제", "시장규모"], projects=["cogtrain"]),
        block("core/thesis/mine.md", tags=["시장규모"], projects=["ad_samd"]),
        block("core/identity/common.md", tags=["기술난제"], layer="identity"),
    )
    assert run_select(tmp_path, proposal, project="ad_samd") == [
        (3, "core/identity/common.md"),  # 소속 미선언 = 공용
        (1, "core/thesis/mine.md"),
    ]


def test_pinned_goes_first_regardless_of_score(tmp_path):
    angle = ANGLE.replace("## 고정 포함\n", "## 고정 포함\n- core/identity/team\n")
    proposal = repo(
        tmp_path,
        block("core/thesis/top.md", tags=["기술난제", "시장규모"]),
        block("core/identity/team.md", layer="identity"),  # 태그 없음 = 점수 0
        angle=angle,
    )
    assert run_select(tmp_path, proposal) == [(0, "core/identity/team.md"), (4, "core/thesis/top.md")]


def test_exclude_wins_over_score(tmp_path):
    angle = ANGLE.replace("## 제외\n", "## 제외\n- strategy/active\n")
    proposal = repo(
        tmp_path,
        block("core/thesis/keep.md", tags=["시장규모"]),
        block("strategy/active/pricing.md", tags=["기술난제"], layer="strategy"),
        angle=angle,
    )
    assert run_select(tmp_path, proposal) == [(1, "core/thesis/keep.md")]


def test_render_marks_origin_and_draft(tmp_path):
    proposal = repo(tmp_path, block("core/thesis/a.md", tags=["기술난제"], status="draft", body="핵심 주장."))
    blocks, _ = load_blocks(tmp_path)
    tags, _ = load_tags(tmp_path)
    angle, _ = load_angle(proposal / "angle.md")
    text = render(select(blocks, angle, tags, None), "2026-08-tips-rnd")
    assert "<!-- core/thesis/a.md · thesis · strict · 점수 3 · draft -->" in text
    assert "핵심 주장." in text


def test_projects_registry_loads(tmp_path):
    (tmp_path / "projects.yaml").write_text(REGISTRY, encoding="utf-8")
    projects, _ = load_projects(tmp_path)
    assert projects.resolve("ad_samd") == "ad_samd"


# ── generated_from 갱신 ──────────────────────────────────────────────────


def load_angle_text(text, tmp_path):
    path = tmp_path / "roundtrip.md"
    path.write_text(text, encoding="utf-8")
    return load_angle(path)


def test_update_generated_from_preserves_everything_else(tmp_path):
    text = textwrap.dedent(
        """\
        ---
        proposal_type: rnd
        project: cogtrain          # 손으로 적은 주석
        extends: templates/angles/rnd.md
        generated_from:
          - core/thesis/old.md@1111111
        ---

        ## 강조
        - tag:기술난제 (강)
        """
    )
    updated = update_generated_from(text, [("core/thesis/new.md", "abcdef0"), ("core/identity/team.md", "9999999")])
    assert "# 손으로 적은 주석" in updated
    assert "## 강조" in updated and "- tag:기술난제 (강)" in updated
    assert "old.md" not in updated
    assert "  - core/thesis/new.md@abcdef0\n  - core/identity/team.md@9999999\n" in updated

    angle, error = load_angle_text(updated, tmp_path)
    assert error == ""
    assert angle.generated_from == [("core/thesis/new.md", "abcdef0"), ("core/identity/team.md", "9999999")]
    assert angle.project == "cogtrain"


def test_update_generated_from_appends_when_absent(tmp_path):
    text = "---\nproposal_type: rnd\n---\n\n## 강조\n"
    updated = update_generated_from(text, [("core/thesis/a.md", "abcdef0")])
    angle, _ = load_angle_text(updated, tmp_path)
    assert angle.proposal_type == "rnd"
    assert angle.generated_from == [("core/thesis/a.md", "abcdef0")]


def test_update_generated_from_clears_to_empty_list(tmp_path):
    text = "---\ngenerated_from:\n  - core/thesis/a.md@abcdef0\nproposal_type: rnd\n---\n\n## 강조\n"
    updated = update_generated_from(text, [])
    angle, _ = load_angle_text(updated, tmp_path)
    assert angle.generated_from == []
    assert angle.proposal_type == "rnd"
