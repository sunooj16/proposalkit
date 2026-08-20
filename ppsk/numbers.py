"""주장성 수치 탐지 — 기획 6장 분류표의 코드화.

**이 정규식들은 가설이다.** 1단계 임포트 결과로 조정하고, 조정할 때마다
`tests/test_numbers.py`에 실제 문장을 케이스로 추가한다 (T-10). 그 테스트가
곧 숫자 클래스 정의의 실체가 된다.
"""

import re

EXEMPT_MARKER = re.compile(r"\{\{![^}]*\}\}")  # 면제 마커 — 스캔 전 제거, 건수만 센다
FACT_REF = re.compile(r"\{\{[a-z0-9_]+\}\}")  # fact 참조 — 스캔 전 제거

# 제외가 우선한다. 주장이 아닌 수치를 먼저 소거한 뒤 대상 패턴을 찾는다.
EXCLUDE = [
    re.compile(p, flags)
    for p, flags in [
        (r"\d{4}-\d{2}-\d{2}", 0),  # 날짜
        (r"제?\s*\d+\s*(장|절|항|조)", 0),  # 순번·구조
        (r"(표|그림|그래프)\s*\d+", 0),
        (r"^\s*\d+\.\s", re.MULTILINE),  # 목록 번호
        (r"\d+\s*(개월|주|일차|차년도|년차)", 0),  # 기간·연차
        (r"TRL\s*\d+", 0),  # 단계·등급
        (r"\d+\s*단계", 0),
        (r"\d+\s*가지", 0),  # 목록 개수
    ]
]

CLAIM = [
    re.compile(p)
    for p in [
        r"[\d,]+(\.\d+)?\s*(억|조|만)?\s*원",  # 금액
        r"\$[\d,]+(\.\d+)?\s*[KMB]?",
        r"[\d,]+\s*(명|건|개\s*기관|개사|곳|회|세션)",  # 규모·실적
        r"\d+(\.\d+)?\s*(%|%p|배)",  # 비율·배수
        r"\d{2}-\d{4}-\d{7}",  # 등록번호
        r"약\s*[\d,]+(\.\d+)?",  # 근사 표현도 대상
        r"[\d,]+\s*(원대|명대|건대)",  # 범위 표현
    ]
]


def _blank_out(pattern, text):
    """길이를 유지한 채 지운다. 줄 번호와 열 위치가 어긋나지 않게."""
    return pattern.sub(lambda m: " " * len(m.group(0)), text)


def strip_noise(text):
    """`(스캔 대상 텍스트, 면제 마커 건수)`. 면제·fact 참조는 검사 대상이 아니다."""
    exempt_count = len(EXEMPT_MARKER.findall(text))
    text = _blank_out(EXEMPT_MARKER, text)
    text = _blank_out(FACT_REF, text)
    return text, exempt_count


def find_claims(text):
    """`[(줄 번호, 매치된 문자열)]`. 줄 번호는 1부터."""
    scanned, _ = strip_noise(text)
    for pattern in EXCLUDE:
        scanned = _blank_out(pattern, scanned)

    hits = []
    for pattern in CLAIM:
        for match in pattern.finditer(scanned):
            line_no = scanned.count("\n", 0, match.start()) + 1
            hits.append((line_no, match.start(), match.group(0).strip()))

    # 같은 위치를 두 패턴이 잡을 수 있다. 위치 기준으로 정렬·중복 제거.
    seen, result = set(), []
    for line_no, start, matched in sorted(hits):
        if start in seen:
            continue
        seen.add(start)
        result.append((line_no, matched))
    return result
