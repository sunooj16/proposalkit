"""ppsk init — 빈 디렉터리에 리포지토리 골격을 만든다."""

from pathlib import Path

from ..scaffold import scaffold


def add_parser(subparsers):
    parser = subparsers.add_parser("init", help="리포지토리 골격 생성")
    parser.add_argument("path", nargs="?", default=".", help="대상 디렉터리 (기본: 현재 디렉터리)")
    parser.add_argument("-q", "--quiet", action="store_true", help="생성된 파일 목록을 출력하지 않는다")
    return parser


def run(args):
    root = Path(args.path)
    root.mkdir(parents=True, exist_ok=True)

    written, skipped = scaffold(root)

    if not args.quiet:
        for rel in written:
            print(f"  + {rel.as_posix()}")
    if skipped:
        print(f"이미 있어 건너뜀: {len(skipped)}개")
    print(f"골격 생성 완료 — {root}. 규약은 docs/rules.md 를 볼 것.")
    return 0
