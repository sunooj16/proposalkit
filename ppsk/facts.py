"""facts 로더 — `facts.yaml` 단일 파일과 `facts/` 디렉터리 양쪽.

파생 fact 평가는 여기 없다 (T-09). 이 모듈은 읽고, 형식을 확인하고, 파일 단위
기본 소속을 상속시키는 데까지만 한다.
"""

from datetime import date
from pathlib import Path

import yaml

from .model import Fact, Finding

FACTS_FILE = "facts.yaml"
FACTS_DIR = "facts"

PROJECT_KEY = "_project"  # 파일 단위 기본 소속. 항목마다 반복하지 않는다 (기획 6장)

# 이 수를 넘으면 분할을 검토하라는 알림 한 줄. 실패가 아니다 (기획 6장).
COUNT_THRESHOLD = 80

FIELDS = ("value", "num", "source", "verified", "stability", "recheck_days", "expr", "format", "projects")
STABILITIES = ("fixed", "volatile")


def fact_files(root):
    """읽을 파일 목록. `facts/` 가 있으면 그쪽이 이기고, 없으면 `facts.yaml`.

    둘 다 없으면 빈 목록 — 오류가 아니다. 아직 등록한 수치가 없을 뿐이다.
    """
    root = Path(root)
    directory = root / FACTS_DIR
    if directory.is_dir():
        return sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
    single = root / FACTS_FILE
    return [single] if single.is_file() else []


def _load_one(path, root, findings):
    """`{id: (entry, 파일 기본 소속)}`. 형식 위반은 findings 에 담고 건너뛴다."""
    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name

    def bad(message, rule="facts.malformed"):
        findings.append(Finding(level="error", rule=rule, message=message, location=rel))

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        bad(f"YAML 파싱 실패: {exc}")
        return {}

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        bad("최상위는 fact id 를 키로 하는 매핑이어야 한다")
        return {}

    file_project = raw.get(PROJECT_KEY)
    if file_project is not None and not isinstance(file_project, str):
        bad(f"{PROJECT_KEY}: 문자열 하나여야 한다")
        file_project = None

    entries = {}
    for fact_id, entry in raw.items():
        fact_id = str(fact_id).strip()
        if fact_id.startswith("_"):  # _project 등 예약 키
            continue
        if not isinstance(entry, dict):
            bad(f"{fact_id}: 키:값 매핑이어야 한다")
            continue
        entries[fact_id] = (entry, file_project, rel)
    return entries


def _build(fact_id, entry, file_project, location, findings):
    """`Fact | None`. 형식 위반이 있으면 None."""

    errors = []

    def bad(message):
        errors.append(Finding(level="error", rule="facts.malformed", message=message, location=location))

    for key in sorted(set(entry) - set(FIELDS)):
        findings.append(
            Finding(level="warn", rule="facts.unknown_field", message=f"{fact_id}: 알 수 없는 필드 {key}", location=location)
        )

    num = entry.get("num")
    if num is not None and (isinstance(num, bool) or not isinstance(num, (int, float))):
        bad(f"{fact_id}.num: 숫자여야 한다")
        num = None

    verified = entry.get("verified")
    if verified is not None and not isinstance(verified, date):
        bad(f"{fact_id}.verified: YYYY-MM-DD 형식이어야 한다")
        verified = None

    recheck_days = entry.get("recheck_days")
    if recheck_days is not None and (not isinstance(recheck_days, int) or isinstance(recheck_days, bool)):
        bad(f"{fact_id}.recheck_days: 정수여야 한다")
        recheck_days = None

    stability = entry.get("stability")
    if stability is not None and stability not in STABILITIES:
        bad(f"{fact_id}.stability: {stability!r} — {' | '.join(STABILITIES)}")
        stability = None

    projects = entry.get("projects")
    if projects is None:
        # 항목이 선언하지 않으면 파일 기본 소속을 상속한다. 그것도 없으면 공용.
        projects = [file_project] if file_project else []
    elif isinstance(projects, str):
        projects = [projects]
    elif not isinstance(projects, list):
        bad(f"{fact_id}.projects: 목록이어야 한다")
        projects = []

    findings += errors
    if errors:
        return None

    return Fact(
        id=fact_id,
        value=None if entry.get("value") is None else str(entry["value"]),
        num=num,
        source=entry.get("source"),
        verified=verified,
        stability=stability,
        recheck_days=recheck_days,
        expr=entry.get("expr"),
        format=entry.get("format"),
        projects=[str(p).strip() for p in projects],
    )


def load_facts(root):
    """`(dict[id, Fact], list[Finding])`. id 는 전역 유일이다."""
    root = Path(root)
    findings = []
    facts = {}
    seen_in = {}

    for path in fact_files(root):
        for fact_id, (entry, file_project, location) in _load_one(path, root, findings).items():
            if fact_id in facts:
                # 분할해도 id 는 전역 유일이어야 `{{fact_id}}` 참조가 흔들리지 않는다.
                findings.append(
                    Finding(
                        level="error",
                        rule="facts.duplicate_id",
                        message=f"id 중복: {fact_id} — {seen_in[fact_id]} 에도 있다",
                        location=location,
                    )
                )
                continue
            fact = _build(fact_id, entry, file_project, location, findings)
            if fact is not None:
                facts[fact_id] = fact
                seen_in[fact_id] = location

    if len(facts) > COUNT_THRESHOLD:
        findings.append(
            Finding(
                level="notice",
                rule="facts.count_threshold",
                message=f"fact {len(facts)}건 — {COUNT_THRESHOLD}건을 넘었다. facts/ 디렉터리로 분할을 검토할 것",
            )
        )

    return facts, findings
