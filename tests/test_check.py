"""check.py — Finding 수집·정렬·요약, 종료코드, 검증 규칙."""

import textwrap
from datetime import date

from ppsk.check import counts, exit_code, run_checks, sort_findings, summary
from ppsk.model import Finding

TODAY = date(2026, 8, 21)


def f(level, rule="x.y", message="m", location=None):
    return Finding(level=level, rule=rule, message=message, location=location)


def rules(findings):
    return [x.rule for x in findings]


# ── 수집·정렬·요약 (T-11) ────────────────────────────────────────────────


def test_sort_puts_errors_first_then_rule_then_location():
    findings = sort_findings(
        [
            f("notice", "facts.count_threshold"),
            f("error", "block.malformed", location="core/b.md"),
            f("warn", "tag.unregistered"),
            f("error", "block.malformed", location="core/a.md"),
            f("report", "exempt.usage"),
        ]
    )
    assert [(x.level, x.location) for x in findings] == [
        ("error", "core/a.md"),
        ("error", "core/b.md"),
        ("warn", None),
        ("notice", None),
        ("report", None),
    ]


def test_sort_is_stable_across_input_order():
    findings = [f("warn", "b.r"), f("error", "a.r"), f("notice", "c.r")]
    assert rules(sort_findings(findings)) == rules(sort_findings(findings[::-1]))


def test_unknown_level_goes_last_not_silently_promoted():
    findings = sort_findings([f("wat"), f("report", "exempt.usage")])
    assert [x.level for x in findings] == ["report", "wat"]
    assert exit_code(findings) == 0


def test_exit_code_and_summary():
    assert exit_code([]) == 0
    assert summary([]) == "이상 없음"
    assert exit_code([f("warn"), f("notice")]) == 0
    assert summary([f("warn"), f("notice")]) == "warn 1, notice 1"
    assert exit_code([f("warn"), f("error")]) == 1
    assert counts([f("error"), f("error")])["error"] == 2


# ── 최소 리포지토리 ───────────────────────────────────────────────────────

BLOCK = textwrap.dedent(
    """\
    ---
    id: core-claim
    layer: thesis
    status: active
    editable: strict
    summary: 한 줄 요약
    {extra}---

    본문.
    """
)


def repo(root, facts="", tags="", projects=None, block=BLOCK.format(extra=""), draft=None, angle=None):
    (root / "core" / "thesis").mkdir(parents=True)
    (root / "facts.yaml").write_text(facts, encoding="utf-8")
    (root / "tags.yaml").write_text(tags, encoding="utf-8")
    if projects is not None:
        (root / "projects.yaml").write_text(projects, encoding="utf-8")
    if block is not None:
        (root / "core" / "thesis" / "b.md").write_text(block, encoding="utf-8")

    proposal = root / "proposals" / "2026-08-tips-rnd"
    if draft is not None or angle is not None:
        proposal.mkdir(parents=True)
    if draft is not None:
        (proposal / "draft.md").write_text(draft, encoding="utf-8")
    if angle is not None:
        (proposal / "angle.md").write_text(angle, encoding="utf-8")
    return proposal


def test_run_checks_on_clean_repo_is_silent(tmp_path):
    repo(tmp_path)
    assert run_checks(tmp_path, today=TODAY) == []


def test_run_checks_gathers_from_every_loader(tmp_path):
    """깨진 파일 하나에서 멈추지 않고 전부 모은다."""
    repo(
        tmp_path,
        facts="a: [1, 2]\n",  # 매핑이 아님 → facts.malformed
        tags="- 하나\n",  # 최상위가 목록 → tags.malformed
        projects="- 하나\n",  # → projects.malformed
        block="본문만 있고 frontmatter 가 없다\n",  # → block.malformed
    )
    findings = run_checks(tmp_path, today=TODAY)
    assert rules(findings) == ["block.malformed", "facts.malformed", "projects.malformed", "tags.malformed"]
    assert exit_code(findings) == 1


def test_run_checks_evaluates_derived_facts(tmp_path):
    repo(
        tmp_path,
        facts=textwrap.dedent(
            """\
            n:
              value: "67명"
              num: 67

            ratio:
              expr: "n / missing_input"
            """
        ),
    )
    assert rules(run_checks(tmp_path, today=TODAY)) == ["derived.unknown_input"]


# ── 프로젝트 규칙 (T-12) ─────────────────────────────────────────────────

REGISTRY = "cogtrain:\n  name: 인지훈련\nad_samd:\n  name: AD SaMD\n"


def test_project_unregistered_on_block_and_fact(tmp_path):
    repo(
        tmp_path,
        projects=REGISTRY,
        block=BLOCK.format(extra="projects: [cogtrian]\n"),  # 오타
        facts="n:\n  value: \"67명\"\n  num: 67\n  projects: [nope]\n",
    )
    findings = run_checks(tmp_path, today=TODAY)
    assert rules(findings) == ["project.unregistered", "project.unregistered"]
    assert [x.location for x in findings] == ["core/thesis/b.md", "facts.yaml:n"]


def test_project_unassigned_is_notice_and_silent_without_registry(tmp_path):
    proposal_repo = tmp_path / "with"
    proposal_repo.mkdir()
    repo(proposal_repo, projects=REGISTRY)
    findings = run_checks(proposal_repo, today=TODAY)
    assert rules(findings) == ["project.unassigned"]
    assert findings[0].level == "notice"
    assert exit_code(findings) == 0

    # 등록부가 비면 전부 공용이 정상이다 — 알리지 않는다.
    bare = tmp_path / "bare"
    bare.mkdir()
    repo(bare)
    assert run_checks(bare, today=TODAY) == []


def test_project_unassigned_level_promotable(tmp_path):
    repo(tmp_path, projects="_config:\n  unassigned: error\n" + REGISTRY)
    findings = run_checks(tmp_path, today=TODAY)
    assert rules(findings) == ["project.unassigned"]
    assert exit_code(findings) == 1


def test_project_unregistered_in_angle(tmp_path):
    repo(tmp_path, projects=REGISTRY, angle="---\nproject: nope\n---\n")
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    assert "project.unregistered" in rules(findings)
    assert findings[0].location == "2026-08-tips-rnd/angle.md"


def test_angle_alias_resolves(tmp_path):
    repo(tmp_path, projects="cogtrain:\n  name: 인지훈련\n  aliases: [cog]\n", angle="---\nproject: cog\n---\n")
    proposal = tmp_path / "proposals" / "2026-08-tips-rnd"
    assert rules(run_checks(tmp_path, proposal, today=TODAY)) == ["project.unassigned"]


def test_angle_malformed(tmp_path):
    repo(tmp_path, projects=REGISTRY, angle="frontmatter 가 없다\n")
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    assert "angle.malformed" in rules(findings)


def test_project_mismatch_blocks_other_projects_fact(tmp_path):
    repo(
        tmp_path,
        projects=REGISTRY,
        facts='mine:\n  value: "67명"\n  num: 67\n  projects: [cogtrain]\n',
        angle="---\nproject: ad_samd\n---\n",
        draft="참여자 {{mine}} 이 완료했다.\n",
    )
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    assert "project.mismatch" in rules(findings)
    assert exit_code(findings) == 1


def test_common_fact_passes_any_project(tmp_path):
    """소속 미선언 fact 는 공용이다 — 어느 제안서에서도 통과한다."""
    repo(
        tmp_path,
        projects=REGISTRY,
        facts='shared:\n  value: "67명"\n  num: 67\n',
        angle="---\nproject: ad_samd\n---\n",
        draft="참여자 {{shared}} 이 완료했다.\n",
    )
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    assert "project.mismatch" not in rules(findings)


# ── 초안 규칙 (T-12) ─────────────────────────────────────────────────────


def test_fact_unregistered_from_raw_number_and_unknown_ref(tmp_path):
    repo(tmp_path, draft="시장은 3,200억 원 규모이고 {{nope}} 를 참조한다.\n")
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    assert rules(findings) == ["fact.unregistered", "fact.unregistered"]
    assert exit_code(findings) == 1


def test_registered_fact_and_exempt_marker_pass(tmp_path):
    repo(
        tmp_path,
        facts='pilot_n:\n  value: "67명"\n  num: 67\n',
        draft="참여자 {{pilot_n}} 이 {{!12개월}} 동안 참여했다.\n",
    )
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    assert rules(findings) == ["exempt.usage"]
    assert findings[0].level == "report"
    assert findings[0].location == "2026-08-tips-rnd/draft.md:L1"


def test_fact_stale_when_recheck_period_passed(tmp_path):
    repo(
        tmp_path,
        facts=textwrap.dedent(
            """\
            old:
              value: "3,200억 원"
              num: 320000000000
              verified: 2025-09-01
              stability: volatile
              recheck_days: 180

            forever:
              value: "10-2024-0012345"
              verified: 2020-01-01
              stability: fixed
              recheck_days: 30
            """
        ),
        draft="시장은 {{old}} 이고 특허는 {{forever}} 다. {{old}} 를 다시 쓴다.\n",
    )
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    # fixed 는 영구 통과, 같은 fact 를 두 번 써도 신고는 한 번.
    assert rules(findings) == ["fact.stale"]
    assert "old" in findings[0].message


def test_derived_fact_stale_follows_its_inputs(tmp_path):
    repo(
        tmp_path,
        facts=textwrap.dedent(
            """\
            total:
              value: "160회"
              num: 160
              verified: 2025-09-01
              stability: volatile
              recheck_days: 90

            n:
              value: "67명"
              num: 67
              verified: 2026-08-01
              stability: volatile
              recheck_days: 90

            per_user:
              expr: "total / n"
              format: "1인당 {v:.1f}회"
            """
        ),
        draft="사용자당 {{per_user}} 를 수행했다.\n",
    )
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    assert rules(findings) == ["fact.stale"]
    assert "파생" in findings[0].message


def test_draft_without_proposal_arg_is_not_checked(tmp_path):
    """초안 검사는 제안서를 지목했을 때만 돈다 — 전역 검사가 남의 초안을 끌고 오지 않게."""
    repo(tmp_path, draft="시장은 3,200억 원 규모다.\n")
    assert run_checks(tmp_path, today=TODAY) == []


# ── 블록·앵글 규칙 (T-13) ────────────────────────────────────────────────

TAGS = "기술난제:\n  aliases: [난제]\n시장규모: {}\n"


def test_tag_unregistered_counted_once_per_tag(tmp_path):
    """정규화는 한 번만 돈다 — 두 번 돌면 건수가 부풀려진다."""
    repo(tmp_path, tags=TAGS, block=BLOCK.format(extra="tags: [난제, 미등록태그]\n"))
    findings = run_checks(tmp_path, today=TODAY)
    assert rules(findings) == ["tag.unregistered"]
    assert findings[0].level == "warn"
    assert "미등록태그 (1회)" in findings[0].message


def test_tag_unregistered_promotable_to_error(tmp_path):
    repo(tmp_path, tags="_config:\n  unregistered: error\n" + TAGS, block=BLOCK.format(extra="tags: [없는태그]\n"))
    assert exit_code(run_checks(tmp_path, today=TODAY)) == 1


def test_block_stale_uses_layer_period(tmp_path):
    repo(tmp_path, block=BLOCK.format(extra="last_verified: 2026-01-01\n"))  # thesis 180일
    findings = run_checks(tmp_path, today=TODAY)
    assert rules(findings) == ["block.stale"]
    assert findings[0].level == "warn"

    # 확인일이 없으면 기한도 없다.
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    repo(fresh)
    assert run_checks(fresh, today=TODAY) == []


def test_identity_layer_never_stale(tmp_path):
    block = BLOCK.format(extra="last_verified: 2020-01-01\n").replace("layer: thesis", "layer: identity")
    repo(tmp_path, block=block)
    assert run_checks(tmp_path, today=TODAY) == []


def angle_with(generated_from="", extra=""):
    return f"---\n{generated_from}---\n\n## 강조\n{extra}"


def test_generated_from_mismatch_on_hash_and_missing_block(tmp_path):
    repo(
        tmp_path,
        angle=angle_with("generated_from:\n  - core/thesis/b.md@deadbee\n  - core/thesis/gone.md@1234567\n"),
        draft="본문.\n",
    )
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    assert rules(findings) == ["generated_from.mismatch", "generated_from.mismatch"]
    assert exit_code(findings) == 0  # 경고다. 다시 수집하면 된다


def test_block_draft_used_is_warn(tmp_path):
    repo(
        tmp_path,
        block=BLOCK.format(extra="").replace("status: active", "status: draft"),
        angle=angle_with("generated_from:\n  - core/thesis/b.md\n"),
        draft="본문.\n",
    )
    findings = run_checks(tmp_path, tmp_path / "proposals" / "2026-08-tips-rnd", today=TODAY)
    assert rules(findings) == ["block.draft_used"]


def test_strict_not_verbatim(tmp_path):
    angle = angle_with("generated_from:\n  - core/thesis/b.md\n")
    proposal = repo(tmp_path, angle=angle, draft="본문을 마음대로 고쳐 썼다.\n")
    findings = run_checks(tmp_path, proposal, today=TODAY)
    assert rules(findings) == ["strict.not_verbatim"]
    assert exit_code(findings) == 1


def test_strict_verbatim_survives_rewrapping(tmp_path):
    """공백만 정규화한다 — 줄바꿈 위치가 달라졌다고 실패하면 아무도 안 쓴다."""
    block = BLOCK.format(extra="").replace("본문.", "긴 문장 하나를\n두 줄로 나눠 썼다.")
    proposal = repo(
        tmp_path,
        block=block,
        angle=angle_with("generated_from:\n  - core/thesis/b.md\n"),
        draft="## 배경\n\n긴 문장 하나를 두 줄로   나눠 썼다.\n",
    )
    assert run_checks(tmp_path, proposal, today=TODAY) == []


def test_free_block_may_be_reworded(tmp_path):
    block = BLOCK.format(extra="").replace("editable: strict", "editable: free")
    proposal = repo(tmp_path, block=block, angle=angle_with("generated_from:\n  - core/thesis/b.md\n"), draft="고쳐 썼다.\n")
    assert run_checks(tmp_path, proposal, today=TODAY) == []


def test_block_project_mismatch(tmp_path):
    proposal = repo(
        tmp_path,
        projects=REGISTRY,
        block=BLOCK.format(extra="projects: [cogtrain]\n"),
        angle="---\nproject: ad_samd\ngenerated_from:\n  - core/thesis/b.md\n---\n\n## 강조\n",
        draft="본문.\n",
    )
    findings = run_checks(tmp_path, proposal, today=TODAY)
    assert "project.mismatch" in rules(findings)
    assert exit_code(findings) == 1


def test_angle_no_match_on_tag_include_and_exclude(tmp_path):
    proposal = repo(
        tmp_path,
        tags=TAGS,
        block=BLOCK.format(extra="tags: [기술난제]\n"),
        angle=(
            "---\nproposal_type: rnd\n---\n\n## 강조\n- tag:난제 (강)\n- tag:시장규모 (배경)\n\n"
            "## 고정 포함\n- core/thesis/b\n- core/thesis/없음\n\n## 제외\n- strategy/pricing\n"
        ),
        draft="본문.\n",
    )
    findings = run_checks(tmp_path, proposal, today=TODAY)
    # alias(난제)와 실재 경로(core/thesis/b)는 통과. 나머지 셋은 매칭 실패.
    assert rules(findings) == ["angle.no_match"] * 3
    assert sorted(x.message.split(": ")[-1] for x in findings) == ["core/thesis/없음", "strategy/pricing", "시장규모"]


def test_angle_matching_respects_project_filter(tmp_path):
    """다른 프로젝트 전용 블록의 태그는 매칭 대상이 아니다 — collect 이 거른 뒤 정렬하므로."""
    proposal = repo(
        tmp_path,
        tags=TAGS,
        projects=REGISTRY,
        block=BLOCK.format(extra="tags: [기술난제]\nprojects: [cogtrain]\n"),
        angle="---\nproject: ad_samd\n---\n\n## 강조\n- tag:기술난제 (강)\n",
    )
    assert "angle.no_match" in rules(run_checks(tmp_path, proposal, today=TODAY))
