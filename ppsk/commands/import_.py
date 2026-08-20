"""ppsk import — 원본 문서를 블록 후보로 잘라 격리 구역에 놓는다.

**분해하지 않는다.** 문단 단위로 자르고 후보를 뽑을 뿐, 계층 판정과 병합은
에이전트와 사람이 한다 (기획 9장). `import/` 는 승인 전 격리 구역이며,
여기서 `core/`·`evidence/` 로 옮기는 것은 사람이 한다.
"""

import re
from pathlib import Path

from ..blocks import normalize_newlines
from ..numbers import find_claims
from ..projects import load_projects

# 헤딩이 있으면 헤딩 기준, 없으면 빈 줄 기준. devplan §7 미확정 항목 — T-G1 결과로 조정한다.
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$", re.MULTILINE)

# h2 까지만 자른다. T-G1 에서 h1~h6 전부로 잘라보니 하위 절이 전부 빠져나간
# 부모 헤딩이 본문 두 줄짜리 껍데기 블록이 되고, 제안서 1건이 38개로 갈라졌다.
# h3 이하는 부모 본문에 그대로 남긴다 (devplan §7 확정).
SPLIT_DEPTH = 2

MIN_CHARS = 40  # 이보다 짧은 조각은 블록 후보로 세우지 않는다


def slugify(text, fallback="block"):
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", str(text)).strip("-").lower()
    return slug[:60] or fallback


def split_sections(text, depth=SPLIT_DEPTH):
    """`[(제목|None, 본문)]`. h1~h`depth` 헤딩 기준으로 자르고, 헤딩이 없으면 빈 줄 기준."""
    text = normalize_newlines(text)
    matches = [m for m in HEADING.finditer(text) if len(m.group(1)) <= depth]

    if not matches:
        chunks = [c.strip() for c in re.split(r"\n\s*\n", text)]
        return [(None, c) for c in chunks if len(c) >= MIN_CHARS]

    sections = []
    preamble = text[: matches[0].start()].strip()
    if len(preamble) >= MIN_CHARS:
        sections.append((None, preamble))

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        if body or match.group(2):
            sections.append((match.group(2), body))
    return sections


def block_text(block_id, title, body, source, line_no, projects=()):
    """후보 블록 파일 내용.

    `layer: TODO` 는 의도된 것이다. 사람이 계층을 정하지 않은 채 core/ 로 옮기면
    허용값이 아니므로 `ppsk check` 이 곧바로 error 를 낸다.
    """
    heading = f"## {title}\n\n" if title else ""
    return (
        "---\n"
        f"id: {block_id}\n"
        "layer: TODO                    # identity | thesis | evidence | strategy — 사람이 정한다\n"
        "status: draft\n"
        "editable: free\n"
        "facts_used: []\n"
        "tags: []\n"
        + (
            f"projects: [{', '.join(projects)}]\n"
            if projects
            else "projects: []                   # 비면 전 프로젝트 공용. 이 사업 전용이면 채울 것\n"
        )
        + f"summary: {title or '(요약을 채울 것)'}\n"
        f"import_source: {source}#L{line_no}    # 승인 시 지울 것\n"
        "---\n"
        f"{heading}{body}\n"
    )


def collect_facts(sections):
    """블록 후보별 주장성 수치. `[(블록 id, 줄 번호, 매치)]`."""
    found = []
    for block_id, _, body in sections:
        found += [(block_id, line_no, matched) for line_no, matched in find_claims(body)]
    return found


def facts_yaml(candidates, source, projects=()):
    lines = [
        "# ppsk import 자동 추출 — 승인 전 후보다.",
        "# id 와 value 를 사람이 확정해 facts.yaml 로 옮긴다. 주장이 아닌 수치는 지운다.",
        f"# 원본: {source}",
        "",
    ]
    if projects:
        # 파일 단위 기본 소속. 항목마다 반복하지 않는다 (기획 6장).
        lines[3:3] = [f"_project: {projects[0]}"]
    for index, (block_id, line_no, matched) in enumerate(candidates, start=1):
        lines += [
            f"candidate_{index:02d}:",
            f'  value: "{matched}"',
            f'  source: "{source} — {block_id} L{line_no}"',
            "  # verified: YYYY-MM-DD",
            "  # stability: volatile      # fixed | volatile",
            "  # recheck_days: 90",
            "",
        ]
    return "\n".join(lines)


def tags_txt(sections, source):
    """헤딩을 태그 후보로 내놓는다. 어휘는 설계가 아니라 임포트 결과에서 귀납한다."""
    lines = [
        "# ppsk import 태그 후보 — 원본 헤딩에서 뽑았다.",
        "# 정규형으로 확정한 것만 tags.yaml 로 옮기고, 변형은 aliases 로 흡수한다.",
        f"# 원본: {source}",
        "",
    ]
    lines += [title for _, title, _ in sections if title]
    return "\n".join(lines) + "\n"


def build(text, source, projects=()):
    """`(블록 목록, facts.candidates.yaml 내용, tags.candidates.txt 내용)`."""
    raw = split_sections(text)

    sections, used = [], {}
    for title, body in raw:
        base = slugify(title) if title else "para"
        used[base] = used.get(base, 0) + 1
        block_id = base if used[base] == 1 else f"{base}-{used[base]}"
        sections.append((block_id, title, body))

    line_of = {}
    normalized = normalize_newlines(text)
    for block_id, title, body in sections:
        anchor = body.split("\n", 1)[0] if body else (title or "")
        position = normalized.find(anchor) if anchor else -1
        line_of[block_id] = normalized.count("\n", 0, position) + 1 if position >= 0 else 1

    blocks = [
        (f"{block_id}.md", block_text(block_id, title, body, source, line_of[block_id], projects))
        for block_id, title, body in sections
    ]
    return blocks, facts_yaml(collect_facts(sections), source, projects), tags_txt(sections, source)


def add_parser(subparsers):
    parser = subparsers.add_parser("import", help="원본 문서를 블록 후보로 임포트")
    parser.add_argument("file", help="임포트할 원본 문서 (텍스트/마크다운)")
    parser.add_argument("--name", help="import/<name>/ 이름 (기본: 원본 파일명)")
    parser.add_argument("--project", help="후보 블록·fact 에 찍을 프로젝트 id (생략하면 공용)")
    parser.add_argument("--force", action="store_true", help="이미 있는 import 디렉터리를 덮어쓴다")
    return parser


def run(args):
    source = Path(args.file)
    if not source.is_file():
        print(f"원본을 찾을 수 없다: {source}")
        return 1

    projects = ()
    if args.project:
        registry, findings = load_projects(".")
        resolved = registry.resolve(args.project)
        if resolved is None:
            # 오타를 그대로 찍으면 승인 뒤 check 에서야 드러난다. 여기서 막는 편이 싸다.
            known = ", ".join(registry.entries) or "(등록부가 비어 있다)"
            print(f"미등록 프로젝트: {args.project} — projects.yaml 에 등록된 것: {known}")
            return 1
        for finding in findings:
            print(f"  {finding.level}: {finding.message}")
        projects = (resolved,)

    out = Path("import") / slugify(args.name or source.stem, fallback="import")
    if out.exists() and any(out.iterdir()) and not args.force:
        print(f"이미 있다: {out} — 덮어쓰려면 --force")
        return 1

    blocks, facts, tags = build(source.read_text(encoding="utf-8"), source.as_posix(), projects)

    out.mkdir(parents=True, exist_ok=True)
    for name, text in blocks:
        (out / name).write_text(text, encoding="utf-8", newline="\n")
    (out / "facts.candidates.yaml").write_text(facts, encoding="utf-8", newline="\n")
    (out / "tags.candidates.txt").write_text(tags, encoding="utf-8", newline="\n")

    print(f"{out} — 블록 후보 {len(blocks)}건")
    print("전부 status: draft, layer: TODO 다. 계층 판정과 병합은 사람이 승인한 뒤에 한다.")
    if not projects:
        print("프로젝트 미지정 — 후보가 전 프로젝트 공용으로 들어갔다. 사업 전용이면 --project 로 다시 돌릴 것.")
    return 0
