"""템플릿 트리를 대상 디렉터리에 펼친다.

`ppsk/templates/` 아래 파일 트리가 그대로 골격이다. 디렉터리 목록을 코드에
따로 두지 않는다 — 두 곳에 적으면 반드시 어긋난다. 빈 디렉터리는 `.gitkeep`
으로 표현한다.
"""

import shutil
from importlib import resources
from pathlib import Path


def template_root():
    return Path(str(resources.files("ppsk") / "templates"))


def template_files():
    """`(원본 경로, 대상 상대경로)` 목록. 경로 사전순."""
    root = template_root()
    return sorted(((p, p.relative_to(root)) for p in root.rglob("*") if p.is_file()), key=lambda pair: pair[1])


def scaffold(root, on_write=None):
    """골격 생성. `(생성된 상대경로, 건너뛴 상대경로)` 반환."""
    root = Path(root)
    written, skipped = [], []

    for source, rel in template_files():
        target = root / rel
        if target.exists():
            skipped.append(rel)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        written.append(rel)
        if on_write is not None:
            on_write(rel)

    return written, skipped
