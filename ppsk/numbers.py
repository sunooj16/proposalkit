"""주장성 수치 탐지 — 기획 6장 분류표의 코드화.

정규식은 가설로 출발했고, T-G1 임포트 코퍼스(과거 제안서 2건)로 한 차례
조정했다. 앞으로도 조정할 때마다 `tests/test_numbers.py`에 **실제 문장**을
케이스로 추가한다. 그 테스트가 곧 숫자 클래스 정의의 실체다.
"""

import re

EXEMPT_MARKER = re.compile(r"\{\{![^}]*\}\}")  # 면제 마커 — 스캔 전 제거, 건수만 센다
FACT_REF = re.compile(r"\{\{[a-z0-9_]+\}\}")  # fact 참조 — 스캔 전 제거

# 제외가 우선한다. 주장이 아닌 수치를 먼저 소거한 뒤 대상 패턴을 찾는다.
EXCLUDE = [
    re.compile(p, flags)
    for p, flags in [
        (r"\d{4}-\d{2}-\d{2}", 0),  # 날짜
        (r"\d{4}\s*년\s*\d{1,2}\s*월(\s*\d{1,2}\s*일)?", 0),
        (r"\d{2,4}\.\d{1,2}\.(\d{1,2}\.?)?", 0),  # 26.09.30. 형태 일정
        (r"제?\s*\d+\s*(장|절|항)", 0),  # 순번·구조
        # `조` 는 `제 3조`(순번) 와 `27조`(금액) 가 충돌한다. 순번은 `제` 를 요구한다.
        (r"제\s*\d+\s*조", 0),
        (r"(표|그림|그래프)\s*\d+", 0),
        (r"^\s*\d+\.\s", re.MULTILINE),  # 목록 번호
        (r"\[\d+(,\s*\d+)*\]", 0),  # 참고문헌 각주 번호 [12], [11, 12]
        (r"\d+\s*(개월|주|일차|차년도|년차|주차|분|초|시간)", 0),  # 기간
        (r"\d+\s*(세|대)\b", 0),  # 연령
        (r"TRL\s*\d+", 0),  # 단계·등급
        (r"\d+\s*단계", 0),
        (r"\d+\s*(가지|축|부)", 0),  # 목록 개수·구성
        (r"\d+\s*차\b", 0),  # 1차, 2차 시도
    ]
]

# 수 하나 — 자리구분 쉼표, 소수점, 만/억/조 배수까지. 쉼표로 시작하지 않는다.
_NUM = r"\d[\d,]*(?:\.\d+)?\s*(?:만|억|조)?"
# 범위 표현은 하나로 묶는다. `25만~30만 원` 을 뒤쪽만 잡으면 앞의 값이 검증을 빠져나간다.
_RANGE = rf"{_NUM}(?:\s*[~∼〜–—-]\s*{_NUM})?"
# 근사 표현도 대상이다. 접두어를 따로 두면 같은 수치가 두 번 잡힌다.
_ABOUT = r"(?:약|최대|최소|평균|연간|연|총)?\s*"

CLAIM = [
    re.compile(p)
    for p in [
        rf"{_ABOUT}{_RANGE}\s*(?:원|달러|USD|유로|엔)",  # 금액
        rf"\$\s*{_RANGE}\s*[KMB]?",
        rf"{_ABOUT}{_RANGE}\s*(?:명|건|곳|회|종|개사|개\s*기관|개\s*국|개|기관|세션|례|편)",  # 규모·실적
        rf"{_ABOUT}{_RANGE}\s*(?:%|%p|배|퍼센트)",  # 비율·배수
        r"\d{2}-\d{4}-\d{7}",  # 등록번호
        rf"{_ABOUT}\d[\d,]*(?:\.\d+)?\s*(?:억|조)",  # 단위 없는 억·조는 금액이다 (긴 매치가 우선하므로 `27조 원` 은 위에서 잡힌다)
        rf"{_RANGE}\s*(?:원대|명대|건대)",  # 범위 표현
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
            matched = match.group(0).strip()
            if not matched or not any(ch.isdigit() for ch in matched):
                continue
            start = match.start() + (len(match.group(0)) - len(match.group(0).lstrip()))
            hits.append((start, start + len(matched), matched))

    # 겹치는 매치는 긴 쪽만 남긴다. `약 3,400억 원` 이 `3,400억 원` 과 함께 잡히면
    # 같은 수치가 두 건으로 세어지고 리포트가 부풀려진다.
    result = []
    last_end = -1
    for start, end, matched in sorted(hits, key=lambda hit: (hit[0], -hit[1])):
        if start < last_end:
            continue
        last_end = end
        result.append((scanned.count("\n", 0, start) + 1, matched))
    return result
