"""블록 파일 파싱 — frontmatter + 본문 해시.

판정은 하지 않는다. 형식 위반만 Finding으로 모아 돌려주고, 신선도·잠금 같은
의미 판정은 check.py가 한다.
"""

import hashlib
import re
from datetime import date
from pathlib import Path

import yaml

from .model import Block, Finding

# 블록이 사는 디렉터리. docs/·archive/·proposals/·templates/·import/ 는 대상이 아니다.
BLOCK_DIRS = ("core", "evidence", "strategy")

# 같은 디렉터리에 있지만 블록이 아닌 파일들.
SKIP_NAMES = {"CHANGELOG.md", "README.md", "INDEX.md"}

REQUIRED = ("id", "layer", "status", "editable", "summary")
OPTIONAL = ("last_verified", "facts_used", "tags", "projects")

ENUMS = {
    "layer": ("identity", "thesis", "evidence", "strategy"),
    "status": ("draft", "active"),
    "editable": ("strict", "free"),
}

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*\r?\n?(.*)\Z", re.DOTALL)


class FrontmatterError(ValueError):
    """`---` 구분자 쌍이 없거나 YAML이 깨진 경우."""


def normalize_newlines(text):
    """해시 계산 전 필수. 빼먹으면 core.lock이 OS마다 다르게 나온다 (devplan §7)."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def sha(body):
    """본문만 해시한다. frontmatter를 포함하면 last_verified 갱신만으로 잠금이 깨진다."""
    return hashlib.sha256(normalize_newlines(body).strip().encode("utf-8")).hexdigest()


def parse_frontmatter(text):
    """`(meta, body)` 반환. 구분자가 없으면 FrontmatterError."""
    match = _FRONTMATTER.match(normalize_newlines(text))
    if match is None:
        raise FrontmatterError("frontmatter 없음 — 파일이 `---` 줄로 시작하고 `---` 로 닫혀야 한다")

    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"frontmatter YAML 파싱 실패: {exc}") from exc

    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise FrontmatterError("frontmatter는 키:값 매핑이어야 한다")

    return meta, match.group(2)


def block_paths(root):
    """스캔 대상 파일 경로. 경로 사전순 — 출력이 재현 가능해야 한다."""
    root = Path(root)
    found = []
    for name in BLOCK_DIRS:
        found += [p for p in (root / name).rglob("*.md") if p.name not in SKIP_NAMES]
    return sorted(found)


def load_block(path, root):
    """`(Block | None, list[Finding])`. 필수 필드가 깨지면 블록은 None."""
    rel = Path(path).relative_to(root)
    findings = []

    def bad(message):
        findings.append(Finding(level="error", rule="block.malformed", message=message, location=str(rel)))

    try:
        meta, body = parse_frontmatter(Path(path).read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        bad(str(exc))
        return None, findings

    for key in REQUIRED:
        if meta.get(key) in (None, ""):
            bad(f"필수 필드 누락: {key}")

    for key, allowed in ENUMS.items():
        value = meta.get(key)
        if value is not None and value not in allowed:
            bad(f"{key}: {value!r} — 허용값은 {' | '.join(allowed)}")

    for key in sorted(set(meta) - set(REQUIRED) - set(OPTIONAL)):
        findings.append(
            Finding(level="warn", rule="block.unknown_field", message=f"알 수 없는 필드: {key}", location=str(rel))
        )

    last_verified = meta.get("last_verified")
    if last_verified is not None and not isinstance(last_verified, date):
        bad(f"last_verified: {last_verified!r} — YYYY-MM-DD 형식이어야 한다")
        last_verified = None

    lists = {}
    for key in ("facts_used", "tags", "projects"):
        value = meta.get(key) or []
        if isinstance(value, str):
            value = [value]  # `projects: cogtrain` 한 줄 표기도 받는다
        if not isinstance(value, list):
            bad(f"{key}: 목록이어야 한다")
            value = []
        lists[key] = [str(item).strip() for item in value]

    if any(f.level == "error" for f in findings):
        return None, findings

    block = Block(
        path=rel,
        id=str(meta["id"]),
        layer=meta["layer"],
        status=meta["status"],
        editable=meta["editable"],
        summary=str(meta["summary"]),
        body=body,
        sha=sha(body),
        last_verified=last_verified,
        facts_used=lists["facts_used"],
        tags=lists["tags"],
        projects=lists["projects"],  # 빈 목록 = 공용. 미등록 id 판정은 check 이 한다
    )
    return block, findings


def load_blocks(root):
    """`(list[Block], list[Finding])`. 깨진 파일은 건너뛰고 나머지는 계속 읽는다."""
    root = Path(root)
    blocks, findings = [], []
    for path in block_paths(root):
        block, found = load_block(path, root)
        findings += found
        if block is not None:
            blocks.append(block)
    return blocks, findings
