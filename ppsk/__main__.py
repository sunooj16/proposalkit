"""ppsk CLI 진입점.

각 커맨드는 ``ppsk/commands/<name>.py`` 에 살고, 다음 두 가지를 노출한다.

    add_parser(subparsers) -> parser  # argparse 하위 파서 등록 후 반환
    run(args) -> int                  # 종료코드 반환

여기서는 등록과 디스패치만 한다. 판정 로직은 커맨드 모듈 밖(check.py 등)에 둔다.
"""

import argparse
import importlib
import sys

from . import __version__

# 등록 순서 = --help 표시 순서. 구현되는 대로 추가한다 (docs/process.md 참조).
COMMANDS = [
    "init",
    "import_",
    "index",
    "new",
    "collect",
    "check",
    "verify",
    "build",
    "core_update",
    "review",
]


def _load(name):
    """구현된 커맨드 모듈만 반환. 미구현이면 None."""
    try:
        return importlib.import_module(f".commands.{name}", __package__)
    except ModuleNotFoundError:
        return None


def build_parser():
    parser = argparse.ArgumentParser(prog="ppsk", description="제안서 블록 도구")
    parser.add_argument("--version", action="version", version=f"ppsk {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    for name in COMMANDS:
        module = _load(name)
        if module is None:
            continue
        # 모듈명(import_)과 커맨드명(import)이 다를 수 있으므로 run을 파서에 붙여둔다.
        module.add_parser(subparsers).set_defaults(run=module.run)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
