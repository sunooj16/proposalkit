"""ppsk collect — 이번 제안서에 쓸 블록만 골라 출력한다.

**필터가 정렬보다 먼저 돈다.** 프로젝트는 순위가 아니라 차단이다 — 다른 사업의
블록은 점수가 아무리 높아도 후보에 들어오지 않는다. 순서를 바꾸면 남의 실적이
상위에 올라오고, 사람이 그것을 지우는 작업이 생긴다 (기획 2장 축 3).

파생 텍스트를 저장하지 않으므로 앵글별 결과는 매번 다시 뽑는다. 대신 무엇을
뽑았는지는 `angle.md` 의 `generated_from` 에 경로·해시로 남는다.
"""

from pathlib import Path

from ..angle import ANGLE_FILE, SHA_LEN, load_angle, matches_path, update_generated_from
from ..blocks import BLOCK_DIRS, load_blocks
from ..projects import load_projects, selects
from ..tags import load_tags

PROPOSALS_DIR = "proposals"


def weights_of(angle, tags):
    """`{정규형 태그: 가중치}`. 같은 태그를 두 번 적었으면 큰 쪽을 쓴다."""
    weights = {}
    for tag, grade in angle.emphasis:
        normalized = tags.normalize(tag)
        weights[normalized] = max(weights.get(normalized, 0), angle.weight(grade))
    return weights


def select(blocks, angle, tags, project):
    """`[(점수, 고정 포함 여부, block)]` — 출력 순서 그대로.

    고정 포함은 점수와 무관하게 선두, 제외는 점수와 무관하게 배제. 점수 0인
    블록은 뽑지 않는다 — "전부 읽고 알아서 골라라"는 collect 가 아니다.
    동점은 경로 사전순이다. 같은 앵글로 두 번 돌리면 같은 목록이 나와야 한다.
    """
    weights = weights_of(angle, tags)
    chosen = []

    for block in blocks:
        path = block.path.as_posix()
        if not selects(block.projects, project):
            continue  # 하드 필터. 정렬보다 먼저.
        if any(matches_path(path, entry) for entry in angle.exclude):
            continue

        pinned = any(matches_path(path, entry) for entry in angle.include)
        score = sum(weights.get(tag, 0) for tag in tags.normalize_all(block.tags))
        if pinned or score > 0:
            chosen.append((score, pinned, block))

    return sorted(chosen, key=lambda item: (not item[1], -item[0], item[2].path.as_posix()))


def render(selected, slug):
    """에이전트가 읽을 텍스트. 블록마다 출처를 한 줄로 밝힌다 — 초안에서 무엇을
    인용했는지 나중에 되짚을 수 있어야 한다."""
    lines = [f"<!-- ppsk collect — {slug}. 이 블록들만 근거로 쓴다 -->", ""]
    for score, pinned, block in selected:
        note = "고정 포함" if pinned else f"점수 {score}"
        lines += [
            f"<!-- {block.path.as_posix()} · {block.layer} · {block.editable} · {note}"
            + (" · draft" if block.status == "draft" else "")
            + " -->",
            "",
            block.body.strip(),
            "",
        ]
    return "\n".join(lines)


def add_parser(subparsers):
    parser = subparsers.add_parser("collect", help="앵글에 맞는 블록 선별 출력")
    parser.add_argument("slug", help="제안서 폴더 이름 (proposals/ 아래)")
    parser.add_argument("--root", default=".", help="리포지토리 루트 (기본: 현재 디렉터리)")
    return parser


def run(args):
    root = Path(args.root)
    proposal = root / PROPOSALS_DIR / args.slug
    if not proposal.is_dir():
        available = ", ".join(sorted(p.name for p in (root / PROPOSALS_DIR).glob("*") if p.is_dir())) or "(없다)"
        print(f"없는 제안서: {args.slug} — 있는 것: {available}")
        return 1

    angle, error = load_angle(proposal / ANGLE_FILE)
    if angle is None:
        print(f"{proposal.as_posix()}/{ANGLE_FILE} — {error}")
        return 1

    if not any((root / name).is_dir() for name in BLOCK_DIRS):
        print(f"블록 디렉터리가 없다: {root} — `ppsk init` 을 먼저 돌릴 것")
        return 1

    blocks, _ = load_blocks(root)
    tags, _ = load_tags(root)
    projects, _ = load_projects(root)

    project = None
    if angle.project:
        project = projects.resolve(angle.project)
        if project is None:
            # 오타 하나가 조용한 빈 결과가 된다. 정렬까지 가기 전에 멈춘다.
            known = ", ".join(projects.entries) or "(등록부가 비어 있다)"
            print(f"미등록 프로젝트: {angle.project} ({ANGLE_FILE}) — 등록된 것: {known}")
            return 1

    selected = select(blocks, angle, tags, project)
    if not selected:
        print(
            f"고른 블록이 없다 — 강조 태그가 어떤 블록과도 맞지 않거나 프로젝트 필터가 전부 걸렀다"
            f" (후보 {len(blocks)}건, 프로젝트 {project or '지정 없음'})"
        )
        return 1

    print(render(selected, args.slug))

    entries = [(block.path.as_posix(), block.sha[:SHA_LEN]) for _score, _pinned, block in selected]
    angle_path = proposal / ANGLE_FILE
    angle_path.write_text(
        update_generated_from(angle_path.read_text(encoding="utf-8"), entries), encoding="utf-8", newline="\n"
    )
    return 0
