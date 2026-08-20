"""facts 로더와 파생 fact 평가.

앞부분은 `facts.yaml` 단일 파일과 `facts/` 디렉터리를 읽어 `Fact` 로 만들고,
뒷부분은 `expr` 를 가진 파생 fact 를 계산해 확인 상태를 상속시킨다.

판정은 하지 않는다. 재확인 기한이 지났는지, 초안이 쓴 수치가 등록됐는지는
check.py 가 본다.
"""

import ast
import operator
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from string import Formatter

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


# ── 파생 fact 평가 (T-09) ────────────────────────────────────────────────
#
# `eval()` 에 문자열을 넘기지 않는다. 파싱한 뒤 허용 노드만 걸러 직접 계산한다.
# facts.yaml 은 사람이 쓰는 파일이고 리포지토리는 에이전트가 쓰기 권한을 갖는다.

ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.USub,
)

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

# 파생 fact 는 이 값들을 입력에서 상속한다. 직접 선언하면 두 소유자가 생긴다 (기획 8장).
FORBIDDEN_ON_DERIVED = ("verified", "stability", "recheck_days", "source")

DEFAULT_FORMAT = "{v:g}"


@dataclass
class Derived:
    """파생 fact 평가 결과. 값과 상속된 확인 상태."""

    id: str
    value: str
    inputs: list  # 입력 fact id, 등장 순서
    verified: date | None = None  # 입력들 중 가장 오래된 확인일
    recheck_due: date | None = None  # 입력별 기한 중 가장 이른 것. fixed 입력은 제외
    source: str = ""


def _parse_expr(fact, findings):
    """`ast.Expression | None`. 허용 노드만 통과한다."""

    def bad(message, rule="derived.invalid_expr"):
        findings.append(Finding(level="error", rule=rule, message=f"{fact.id}: {message}", location=FACTS_FILE))

    try:
        tree = ast.parse(fact.expr, mode="eval")
    except SyntaxError as exc:
        bad(f"expr 파싱 실패 — {exc.msg}")
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            bad(f"expr 에 허용되지 않은 문법: {type(node).__name__}")
            return None
        if isinstance(node, ast.Constant) and (isinstance(node.value, bool) or not isinstance(node.value, (int, float))):
            bad(f"expr 의 상수는 숫자여야 한다: {node.value!r}")
            return None
    return tree


def _compute(node, values):
    if isinstance(node, ast.Expression):
        return _compute(node.body, values)
    if isinstance(node, ast.BinOp):
        return OPERATORS[type(node.op)](_compute(node.left, values), _compute(node.right, values))
    if isinstance(node, ast.UnaryOp):
        return -_compute(node.operand, values)
    if isinstance(node, ast.Name):
        return values[node.id]
    return node.value  # Constant


def _apply_format(fact, value, findings):
    """`str | None`. `{v}` 슬롯 하나에만 값을 넣는다."""

    def bad(message):
        findings.append(
            Finding(level="error", rule="derived.invalid_format", message=f"{fact.id}: {message}", location=FACTS_FILE)
        )

    template = fact.format or DEFAULT_FORMAT
    fields = [name for _, name, _, _ in Formatter().parse(template) if name is not None]

    if len(fields) > 1:
        bad(f"format 의 슬롯은 하나여야 한다 — {len(fields)}개 발견")
        return None
    if any(name != "v" for name in fields):
        bad(f"format 의 슬롯은 {{v}} 여야 한다: {template!r}")
        return None

    try:
        return template.format(v=value)
    except (ValueError, KeyError, IndexError) as exc:
        bad(f"format 적용 실패 — {exc}")
        return None


def _inherit(fact, inputs):
    """입력들로부터 확인 상태를 상속한다."""
    verified_dates = [f.verified for f in inputs if f.verified is not None]
    verified = min(verified_dates) if verified_dates else None

    # stability: fixed 는 기한 계산에서 빠진다. 특허번호·설립일은 영구 통과다.
    dues = [
        f.verified + timedelta(days=f.recheck_days)
        for f in inputs
        if f.stability != "fixed" and f.verified is not None and f.recheck_days is not None
    ]

    sources = [f.source for f in inputs if f.source]
    source = " · ".join(sources)
    return verified, (min(dues) if dues else None), (f"{source} · 계산: {fact.expr}" if source else f"계산: {fact.expr}")


def eval_derived(fact, facts):
    """`(Derived | None, list[Finding])`. 깊이 1 고정 — 파생이 파생을 참조하지 못한다."""
    findings = []

    def bad(message, rule):
        findings.append(Finding(level="error", rule=rule, message=f"{fact.id}: {message}", location=FACTS_FILE))

    for field_name in FORBIDDEN_ON_DERIVED:
        if getattr(fact, field_name) is not None:
            bad(f"파생 fact 는 {field_name} 를 선언할 수 없다 — 입력에서 상속한다", "derived.forbidden_field")

    tree = _parse_expr(fact, findings)
    if tree is None or findings:
        return None, findings

    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in names:
            names.append(node.id)

    inputs = []
    for name in names:
        source_fact = facts.get(name)
        if source_fact is None:
            bad(f"등록되지 않은 fact 를 참조한다: {name}", "derived.unknown_input")
        elif source_fact.derived:
            bad(f"파생 fact 를 참조한다: {name} — 파생은 깊이 1 까지다", "derived.nested")
        elif source_fact.num is None:
            bad(f"입력 {name} 에 num 이 없다 — 값에서 숫자를 추출하지 않는다", "derived.missing_num")
        else:
            inputs.append(source_fact)

    if findings:
        return None, findings

    try:
        value = _compute(tree, {f.id: f.num for f in inputs})
    except ZeroDivisionError:
        bad("0 으로 나눈다", "derived.invalid_expr")
        return None, findings

    formatted = _apply_format(fact, value, findings)
    if formatted is None:
        return None, findings

    verified, recheck_due, source = _inherit(fact, inputs)
    return (
        Derived(
            id=fact.id,
            value=formatted,
            inputs=[f.id for f in inputs],
            verified=verified,
            recheck_due=recheck_due,
            source=source,
        ),
        findings,
    )


def eval_all_derived(facts):
    """`(dict[id, Derived], list[Finding])`. 캐시 없음 — build 마다 다시 센다."""
    results, findings = {}, []
    for fact in facts.values():
        if not fact.derived:
            continue
        derived, found = eval_derived(fact, facts)
        findings += found
        if derived is not None:
            results[fact.id] = derived
    return results, findings
