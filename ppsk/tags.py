"""통제 어휘 로더 + alias 정규화.

어휘가 없으면 전부 미등록이다 — 그 자체는 오류가 아니다. 어휘는 임포트
결과에서 귀납되므로(기획 7장) 초기에는 비어 있는 것이 정상이다.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .model import Finding

TAGS_FILE = "tags.yaml"
CONFIG_KEY = "_config"
DEFAULT_UNREGISTERED = "warn"  # 어휘 안정화 후 tags.yaml 한 줄로 error 승격 (T-24)


def _key(tag):
    """대소문자·공백 차이는 같은 태그로 본다. `기술 난제` == `기술난제`, `KPI` == `kpi`."""
    return re.sub(r"\s+", "", str(tag)).casefold()


@dataclass
class Tags:
    """정규형 어휘 + alias 역인덱스. `normalize`가 미등록 태그를 세어둔다."""

    canonical: dict = field(default_factory=dict)  # 정규형 -> [alias...]
    unregistered_level: str = DEFAULT_UNREGISTERED
    unregistered: Counter = field(default_factory=Counter)  # 원문 -> 등장 횟수
    _index: dict = field(default_factory=dict)  # _key(alias|정규형) -> 정규형

    def normalize(self, tag):
        """정규형 반환. 어휘에 없으면 원문 그대로 돌려주고 미등록 카운트를 올린다."""
        tag = str(tag).strip()
        found = self._index.get(_key(tag))
        if found is None:
            self.unregistered[tag] += 1
            return tag
        return found

    def normalize_all(self, tags):
        """정규형 목록. 선언 순서를 유지하고 중복은 제거한다.

        `[문제정의, 고객문제]` 처럼 정규형과 그 alias 를 같이 달면 정규화 후 같은
        태그가 두 번 남는다. 중복 태그는 어떤 호출부에서도 의미가 없다.
        """
        seen, result = set(), []
        for tag in tags:
            normalized = self.normalize(tag)
            if normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    def unregistered_findings(self):
        """등장 횟수 내림차순. 두세 번 이상 나온 태그가 어휘 승격 후보다 (기획 7장)."""
        return [
            Finding(
                level=self.unregistered_level,
                rule="tag.unregistered",
                message=f"미등록 태그: {tag} ({count}회)",
            )
            for tag, count in sorted(self.unregistered.items(), key=lambda kv: (-kv[1], kv[0]))
        ]


def load_tags(root):
    """`(Tags, list[Finding])`. `tags.yaml` 부재는 빈 어휘 — 오류가 아니다."""
    path = Path(root) / TAGS_FILE
    findings = []

    def bad(message):
        findings.append(Finding(level="error", rule="tags.malformed", message=message, location=TAGS_FILE))

    if not path.exists():
        return Tags(), findings

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        bad(f"YAML 파싱 실패: {exc}")
        return Tags(), findings

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        bad("최상위는 키:값 매핑이어야 한다")
        return Tags(), findings

    config = raw.get(CONFIG_KEY) or {}
    level = config.get("unregistered", DEFAULT_UNREGISTERED) if isinstance(config, dict) else DEFAULT_UNREGISTERED
    if level not in ("warn", "error"):
        bad(f"_config.unregistered: {level!r} — warn | error")
        level = DEFAULT_UNREGISTERED

    tags = Tags(unregistered_level=level)
    for name, entry in raw.items():
        if name == CONFIG_KEY:
            continue
        name = str(name).strip()
        aliases = (entry or {}).get("aliases") or [] if isinstance(entry, dict) else []
        if not isinstance(aliases, list):
            bad(f"{name}.aliases: 목록이어야 한다")
            aliases = []
        aliases = [str(a).strip() for a in aliases]
        tags.canonical[name] = aliases

        for term in [name] + aliases:
            owner = tags._index.get(_key(term))
            if owner is not None and owner != name:
                # 한 표기가 두 정규형을 가리키면 매칭이 조용히 어긋난다.
                bad(f"중복 표기 {term!r} — {owner} 와 {name} 양쪽에 있다")
                continue
            tags._index[_key(term)] = name

    return tags, findings
