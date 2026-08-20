"""핵심 자료구조 — 타입 선언만. 판정 로직은 check.py, 로딩은 blocks/facts.py에 둔다."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

Layer = Literal["identity", "thesis", "evidence", "strategy"]
Status = Literal["draft", "active"]
Editable = Literal["strict", "free"]
Stability = Literal["fixed", "volatile"]
Level = Literal["error", "warn", "notice", "report"]


@dataclass
class Block:
    """`core/`·`evidence/`·`strategy/` 하위 마크다운 블록 하나."""

    path: Path  # 리포지토리 루트 기준 상대경로
    id: str
    layer: Layer
    status: Status
    editable: Editable
    summary: str
    body: str
    sha: str  # sha256(정규화된 body). core.lock·generated_from 공용
    last_verified: date | None = None
    facts_used: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)  # 정규형으로 치환된 상태


@dataclass
class Fact:
    """`facts.yaml` / `facts/*.yaml` 항목 하나. `expr`가 있으면 파생 fact."""

    id: str
    value: str | None = None
    num: float | None = None
    source: str | None = None
    verified: date | None = None
    stability: Stability | None = None
    recheck_days: int | None = None
    expr: str | None = None  # 파생 fact
    format: str | None = None

    @property
    def derived(self) -> bool:
        return self.expr is not None


@dataclass
class Finding:
    """검증 결과 1건. `level`이 종료코드를 결정한다 — error 1건이라도 있으면 exit 1."""

    level: Level
    rule: str  # "fact.unregistered" 등 안정적인 식별자. 테스트는 문구가 아니라 이 값으로 단언한다
    message: str
    location: str | None = None  # "draft.md:L34"
