"""프로젝트 등록부 + 소속 판정.

계층은 "무엇인가", 태그는 "얼마나 관련 있는가", 프로젝트는 "여기에 들어가도
되는가"다. 앞의 둘은 정렬이고 이것은 차단이다 (기획 2장 축 3).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .model import Finding

PROJECTS_FILE = "projects.yaml"
CONFIG_KEY = "_config"
DEFAULT_UNASSIGNED = "notice"  # 소속 미선언은 공용이다. 등급은 리포트 수준
LEVELS = ("notice", "warn", "error")
STATUSES = ("active", "archived")


def _key(name):
    return re.sub(r"\s+", "", str(name)).casefold()


def selects(declared, project):
    """이 항목이 해당 프로젝트에서 보이는가.

    `declared` 는 블록/fact 가 선언한 소속 목록, `project` 는 지금 수집 중인
    프로젝트 id (특정하지 않으면 None).
    """
    if not declared:  # 소속 미선언 = 공용
        return True
    if project is None:  # 프로젝트를 특정하지 않은 수집 = 전부
        return True
    return project in declared


@dataclass
class Projects:
    """등록된 프로젝트 목록. 미등록 id 는 오타이므로 조용히 넘기지 않는다."""

    entries: dict = field(default_factory=dict)  # id -> {"name": str, "status": str}
    unassigned_level: str = DEFAULT_UNASSIGNED
    _index: dict = field(default_factory=dict)  # _key(id|alias) -> id

    def resolve(self, name):
        """등록된 id 반환. 미등록이면 None — 판정은 호출부(check)가 한다."""
        return self._index.get(_key(name))

    def resolve_all(self, names):
        """`(정규 id 목록, 미등록 원문 목록)`."""
        resolved, unknown = [], []
        for name in names:
            found = self.resolve(name)
            if found is None:
                unknown.append(str(name).strip())
            elif found not in resolved:
                resolved.append(found)
        return resolved, unknown

    def is_archived(self, project_id):
        return self.entries.get(project_id, {}).get("status") == "archived"

    def active_ids(self):
        return [pid for pid in self.entries if not self.is_archived(pid)]

    def name(self, project_id):
        return self.entries.get(project_id, {}).get("name", project_id)


def load_projects(root):
    """`(Projects, list[Finding])`. `projects.yaml` 부재는 빈 등록부 — 오류가 아니다.

    등록부가 비면 모든 항목이 공용이므로 필터가 항상 통과한다. 프로젝트가 하나뿐인
    리포지토리는 이 파일을 신경 쓰지 않아도 된다.
    """
    path = Path(root) / PROJECTS_FILE
    findings = []

    def bad(message):
        findings.append(Finding(level="error", rule="projects.malformed", message=message, location=PROJECTS_FILE))

    if not path.exists():
        return Projects(), findings

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        bad(f"YAML 파싱 실패: {exc}")
        return Projects(), findings

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        bad("최상위는 키:값 매핑이어야 한다")
        return Projects(), findings

    config = raw.get(CONFIG_KEY) if isinstance(raw.get(CONFIG_KEY), dict) else {}
    level = config.get("unassigned", DEFAULT_UNASSIGNED)
    if level not in LEVELS:
        bad(f"_config.unassigned: {level!r} — {' | '.join(LEVELS)}")
        level = DEFAULT_UNASSIGNED

    projects = Projects(unassigned_level=level)
    for pid, entry in raw.items():
        if pid == CONFIG_KEY:
            continue
        pid = str(pid).strip()
        entry = entry if isinstance(entry, dict) else {}

        status = entry.get("status", "active")
        if status not in STATUSES:
            bad(f"{pid}.status: {status!r} — {' | '.join(STATUSES)}")
            status = "active"

        aliases = entry.get("aliases") or []
        if not isinstance(aliases, list):
            bad(f"{pid}.aliases: 목록이어야 한다")
            aliases = []

        projects.entries[pid] = {"name": str(entry.get("name", pid)), "status": status}

        for term in [pid] + [str(a).strip() for a in aliases]:
            owner = projects._index.get(_key(term))
            if owner is not None and owner != pid:
                # 한 표기가 두 프로젝트를 가리키면 필터가 조용히 어긋난다.
                bad(f"중복 표기 {term!r} — {owner} 와 {pid} 양쪽에 있다")
                continue
            projects._index[_key(term)] = pid

    return projects, findings
