"""ppsk new — 제안서 폴더를 만든다.

`angle.md` 는 `templates/angles/<type>.md` 를 **여기서 한 번** 펼친다. 상속을
검사 때마다 다시 해석하면 템플릿을 고쳤을 때 이미 확정한 앵글이 조용히 바뀐다
(기획 7장의 "파생 텍스트를 저장하지 않는다"는 core 블록 이야기이지, 사람이
확정하는 angle.md 이야기가 아니다). `extends:` 는 출처 표시로 남긴다.
"""

from datetime import date
from pathlib import Path

from ..angle import ANGLE_FILE
from ..blocks import FrontmatterError, parse_frontmatter
from ..projects import load_projects

PROPOSALS_DIR = "proposals"
ANGLE_TEMPLATES = "templates/angles"

BRIEF = """\
# 공고 요구사항

<!-- 공고문에서 평가항목·제출양식·분량 제한을 여기에 옮겨 적는다. 원문 붙여넣기도 좋다. -->
"""

DRAFT = """\
<!-- 초안. 주장성 수치는 {{fact_id}} 로 쓰고 facts.yaml 에 등록한다.
     fact 가 아닌 수치는 {{!12개월}} 로 면제한다 (면제는 리포트에 건수로 남는다).
     `ppsk collect <slug>` 로 뽑은 블록만 근거로 쓴다. -->
"""

DEVIATIONS = """\
<!-- 자동 기록 — ppsk check 이 core 잠금 이탈 시도를 여기에 append 한다. 편집 금지 -->
"""


def dirname(slug, today):
    """`2026-08-tips-rnd` — 연월 접두. 폴더 목록이 시간순으로 정렬된다."""
    return f"{today:%Y-%m}-{slug}"


def angle_types(root):
    """리포지토리에 있는 앵글 템플릿 이름. 패키지가 아니라 **리포지토리** 것을 쓴다 —
    템플릿은 스캐폴드 이후 사람이 고쳐 쓰는 파일이다."""
    return sorted(p.stem for p in (Path(root) / ANGLE_TEMPLATES).glob("*.md"))


def build_angle(template_text, proposal_type, project=None):
    """`(angle.md 내용, 오류 사유)`. 템플릿 본문은 그대로 두고 frontmatter 만 다시 쓴다.

    `yaml.dump` 로 통째로 다시 쓰면 템플릿의 주석과 절 순서가 날아간다.
    """
    try:
        _, body = parse_frontmatter(template_text)
    except FrontmatterError as exc:
        return None, str(exc)

    meta = [f"proposal_type: {proposal_type}"]
    if project:
        meta.append(f"project: {project}")
    else:
        meta.append("# project: <id>            # 이 제안서가 속한 프로젝트. 생략하면 회사 단위(IR 등)")
    meta.append(f"extends: {ANGLE_TEMPLATES}/{proposal_type}.md")

    return "---\n" + "\n".join(meta) + "\n---\n" + body, ""


def create(root, slug, proposal_type, project=None, today=None):
    """`(경로, 생성된 파일 목록, 오류 사유)`. 오류면 아무것도 쓰지 않는다."""
    root = Path(root)
    today = today or date.today()

    # 사용자 입력이 그대로 경로가 된다. 상위 디렉터리로 새 나가지 않게 막는다.
    if not slug or slug != Path(slug).name or slug.startswith("."):
        return None, [], f"쓸 수 없는 slug: {slug!r} — 경로 구분자 없이 한 조각이어야 한다"

    template = root / ANGLE_TEMPLATES / f"{proposal_type}.md"
    if not template.exists():
        available = ", ".join(angle_types(root)) or "(templates/angles/ 가 비었다)"
        return None, [], f"없는 제안 유형: {proposal_type} — 쓸 수 있는 것: {available}"

    angle_text, error = build_angle(template.read_text(encoding="utf-8"), proposal_type, project)
    if error:
        return None, [], f"{template} — {error}"

    target = root / PROPOSALS_DIR / dirname(slug, today)
    if target.exists():
        return None, [], f"이미 있다: {target} — 덮어쓰지 않는다"

    # final.md / report.md 는 만들지 않는다. 빈 파일이 놓여 있으면 검증을 통과한
    # 산출물처럼 보인다 — 그 둘은 build·check 만이 만든다 (기획 4장).
    files = {"brief.md": BRIEF, ANGLE_FILE: angle_text, "draft.md": DRAFT, "deviations.md": DEVIATIONS}

    target.mkdir(parents=True)
    for name, text in files.items():
        (target / name).write_text(text, encoding="utf-8", newline="\n")
    return target, sorted(files), ""


def add_parser(subparsers):
    parser = subparsers.add_parser("new", help="제안서 폴더 생성")
    parser.add_argument("slug", help="제안서 이름 — 폴더는 `YYYY-MM-<slug>`")
    parser.add_argument("--type", required=True, dest="proposal_type", help="앵글 템플릿 이름 (templates/angles/)")
    parser.add_argument("--project", help="이 제안서가 속한 프로젝트 id. 생략하면 회사 단위")
    parser.add_argument("--root", default=".", help="리포지토리 루트 (기본: 현재 디렉터리)")
    return parser


def run(args):
    root = Path(args.root)

    project = None
    if args.project:
        projects, _ = load_projects(root)
        project = projects.resolve(args.project)
        if project is None:
            # 오타를 그대로 찍으면 angle.md 에 박히고 collect 결과가 조용히 빈다 (T-30 과 같은 이유).
            known = ", ".join(projects.entries) or "(등록부가 비어 있다)"
            print(f"미등록 프로젝트: {args.project} — projects.yaml 에 등록된 것: {known}")
            return 1

    target, files, error = create(root, args.slug, args.proposal_type, project)
    if error:
        print(error)
        return 1

    for name in files:
        print(f"  + {(target / name).as_posix()}")
    print(f"{target.as_posix()} — 다음: brief.md 에 공고문을 옮기고 angle.md 의 강조를 확정할 것")
    print(f"그다음 `ppsk collect {target.name}` 로 근거 블록을 뽑는다.")
    return 0
