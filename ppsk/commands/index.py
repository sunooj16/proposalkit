"""ppsk index — frontmatter summary 를 모아 INDEX.md 를 만든다.

에이전트는 인덱스를 먼저 읽고 필요한 파일만 연다. 별도 매니페스트를 유지하는
것보다 각 파일 frontmatter 에서 뽑아 쓰는 편이 동기화 문제가 없다 (기획 4장).
"""

from pathlib import Path

from ..blocks import BLOCK_DIRS, load_blocks
from ..tags import load_tags

INDEX_FILE = "INDEX.md"
HEADER = "<!-- 자동 생성 — ppsk index. 편집 금지 -->"

LAYER_ORDER = ("identity", "thesis", "evidence", "strategy")


def _cell(text):
    """표가 깨지지 않게 파이프와 줄바꿈만 막는다."""
    return " ".join(str(text).split()).replace("|", "\|")


def render(blocks, tags):
    """INDEX.md 내용. 블록 tags 는 여기서 정규형으로 치환한다."""
    lines = [HEADER, "", "# 블록 인덱스", ""]

    if not blocks:
        lines += ["아직 블록이 없다. `ppsk import` 로 과거 문서를 임포트하고 승인해 `core/`·`evidence/` 로 옮긴다.", ""]
        return "\n".join(lines)

    by_layer = {}
    for block in blocks:
        by_layer.setdefault(block.layer, []).append(block)

    # 알 수 없는 layer 는 뒤에 붙인다. 블록이 조용히 목록에서 사라지지 않게.
    ordered = [l for l in LAYER_ORDER if l in by_layer] + sorted(set(by_layer) - set(LAYER_ORDER))

    for layer in ordered:
        lines += [f"## {layer}", "", "| 경로 | 태그 | 요약 |", "|---|---|---|"]
        for block in by_layer[layer]:
            path = block.path.as_posix()
            label = f"`{path}`" + (" *(draft)*" if block.status == "draft" else "")
            normalized = ", ".join(tags.normalize_all(block.tags))
            lines.append(f"| {label} | {_cell(normalized)} | {_cell(block.summary)} |")
        lines.append("")

    lines += [f"블록 {len(blocks)}건 — " + ", ".join(f"{l} {len(by_layer[l])}" for l in ordered), ""]
    return "\n".join(lines)


def add_parser(subparsers):
    parser = subparsers.add_parser("index", help="INDEX.md 생성")
    parser.add_argument("path", nargs="?", default=".", help="리포지토리 루트 (기본: 현재 디렉터리)")
    return parser


def run(args):
    root = Path(args.path)
    if not any((root / name).is_dir() for name in BLOCK_DIRS):
        print(f"블록 디렉터리가 없다: {root} — `ppsk init` 을 먼저 돌릴 것")
        return 1

    blocks, findings = load_blocks(root)
    tags, tag_findings = load_tags(root)

    text = render(blocks, tags)
    (root / INDEX_FILE).write_text(text, encoding="utf-8", newline="\n")

    for finding in findings + tag_findings + tags.unregistered_findings():
        location = f" ({finding.location})" if finding.location else ""
        print(f"  {finding.level}: {finding.message}{location}")

    print(f"{root / INDEX_FILE} — 블록 {len(blocks)}건")
    # 인덱스 생성은 검증이 아니다. 판정과 종료코드는 ppsk check 이 소유한다.
    return 0
