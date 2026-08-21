"""`angle.md` 로더 — 이번 제안서의 강조점.

앵글은 블록 경로 목록이 아니라 **의도**다. 사람이 판단할 것은 "이번 공고는
기술적 난제를 앞세워야 한다"이지 "core/thesis/existing-limitation 을 1순위로"가
아니다 (기획 7장). 그래서 본문은 태그 가중치로 쓰고, 경로는 고정 포함·제외라는
예외에만 쓴다.

판정은 하지 않는다 — 매칭 실패(`angle.no_match`)나 해시 불일치는 check.py 가
소유한다. tags.py·projects.py 와 같은 구조다.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from .blocks import FrontmatterError, normalize_newlines, parse_frontmatter, split_frontmatter

ANGLE_FILE = "angle.md"

# 절 제목. 템플릿(`ppsk/templates/templates/angles/`)과 한 벌이다.
EMPHASIS = "강조"
INCLUDE = "고정 포함"
EXCLUDE = "제외"

# 태그 가중치 (devplan §4). 등급을 안 달면 강이다 — 굳이 적었다면 강조하려는 것이다.
WEIGHTS = {"강": 3, "배경": 1}
DEFAULT_GRADE = "강"

_HEADING = re.compile(r"^#{1,6}\s*(.+?)\s*$")
_ITEM = re.compile(r"^\s*[-*]\s+(.*)$")
_GRADE = re.compile(r"\(\s*(.+?)\s*\)\s*$")
# `generated_from:` 한 키와 그 아래 들여쓴 줄들. frontmatter 원문에만 적용한다.
_GENERATED_FROM = re.compile(r"^generated_from:.*(?:\n[ \t]+\S.*)*\n?", re.MULTILINE)

SHA_LEN = 7  # 사람이 눈으로 대조하는 길이. 전체 해시는 core.lock 이 든다


@dataclass
class Angle:
    """`angle.md` 한 건. 값만 담는다."""

    project: str | None = None  # 원문 — 등록부 대조는 check 이 한다
    proposal_type: str | None = None
    extends: str | None = None
    generated_from: list = field(default_factory=list)  # [(경로, sha 접두)]
    emphasis: list = field(default_factory=list)  # [(태그 원문, 등급)]
    include: list = field(default_factory=list)  # 고정 포함 경로
    exclude: list = field(default_factory=list)  # 제외 경로

    def weight(self, grade):
        return WEIGHTS.get(grade, WEIGHTS[DEFAULT_GRADE])


def _strip_comment(line):
    """줄 끝 `# 주석` 제거. 경로·태그에 `#` 이 들어갈 일은 없다."""
    return line.split("#", 1)[0].strip()


def _sections(body):
    """`{절 제목: [항목...]}`. 항목은 `- ` 로 시작하는 줄만."""
    result, current = {}, None
    for line in body.splitlines():
        heading = _HEADING.match(line) if line.startswith("#") else None
        if heading:
            current = heading.group(1)
            result.setdefault(current, [])
            continue
        item = _ITEM.match(line)
        if item is not None and current is not None:
            text = _strip_comment(item.group(1))
            if text:
                result[current].append(text)
    return result


def _emphasis(items):
    """`- tag:기술난제 (강)` → `("기술난제", "강")`."""
    parsed = []
    for item in items:
        grade = DEFAULT_GRADE
        match = _GRADE.search(item)
        if match is not None:
            grade = match.group(1)
            item = item[: match.start()].strip()
        # `tag:` 접두는 있어도 없어도 받는다. 어차피 이 절은 태그만 적는 곳이다.
        parsed.append((item.removeprefix("tag:").strip(), grade))
    return [(tag, grade) for tag, grade in parsed if tag]


def _generated_from(raw):
    """`["core/thesis/x.md@8c1e04b"]` → `[("core/thesis/x.md", "8c1e04b")]`.

    `@` 가 없으면 해시 없이 경로만 — `ppsk collect` 이전 수동 편집분이다.
    """
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []

    entries = []
    for item in raw:
        text = str(item).strip()
        if not text:
            continue
        path, _, digest = text.rpartition("@")
        entries.append((path, digest) if path else (digest, ""))
    return entries


def load_angle(path):
    """`(Angle | None, str)`. 두 번째는 실패 사유 — 판정은 호출부가 한다."""
    try:
        meta, body = parse_frontmatter(Path(path).read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        return None, str(exc)
    except OSError as exc:
        return None, f"읽을 수 없다: {exc}"

    def text(key):
        value = meta.get(key)
        return str(value).strip() if value not in (None, "") else None

    sections = _sections(body)
    return (
        Angle(
            project=text("project"),
            proposal_type=text("proposal_type"),
            extends=text("extends"),
            generated_from=_generated_from(meta.get("generated_from")),
            emphasis=_emphasis(sections.get(EMPHASIS, [])),
            include=sections.get(INCLUDE, []),
            exclude=sections.get(EXCLUDE, []),
        ),
        "",
    )


def matches_path(path, entry):
    """`core/thesis/core-claim` 이 파일(`.md` 생략)과 디렉터리 접두를 모두 받는다.

    사람이 `angle.md` 에 손으로 쓰는 칸이라 확장자를 붙이는지가 일정하지 않다.
    """
    entry = entry.strip().strip("/")
    return path == entry or path == f"{entry}.md" or path.startswith(f"{entry}/")


def update_generated_from(text, entries):
    """`generated_from` 한 키만 갈아끼운 `angle.md` 내용.

    나머지 줄·주석·본문은 그대로 둔다. `yaml.dump` 로 다시 쓰면 사람이 적은
    `## 강조` 절과 주석이 날아간다 (devplan §4 의 verify 와 같은 이유).
    """
    raw, body = split_frontmatter(normalize_newlines(text))

    if entries:
        block = "generated_from:\n" + "".join(f"  - {path}@{digest}\n" for path, digest in entries)
    else:
        block = "generated_from: []\n"

    if _GENERATED_FROM.search(raw):
        raw = _GENERATED_FROM.sub(lambda _: block, raw, count=1)
    else:
        raw = raw.rstrip("\n") + "\n" + block

    return "---\n" + raw.strip("\n") + "\n---\n" + body
