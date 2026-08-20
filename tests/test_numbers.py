"""numbers.py — 주장성 수치 탐지.

여기 케이스가 곧 숫자 클래스 정의의 실체다. `CORPUS` 는 T-G1 에서 임포트한
과거 제안서 2건(TIPS 투자제안서, MVP 공동개발 사업계획서)의 실제 문장이다.
정규식을 고칠 때는 문장을 여기에 먼저 추가한다.
"""

import pytest

from ppsk.numbers import find_claims, strip_noise


def matches(text):
    return [m for _, m in find_claims(text)]


# (실제 문장, 잡혀야 하는 수치)
CORPUS = [
    ("국내 아토피피부염 진단 환자는 2024년 기준 연간 약 100만 명 규모이며", ["약 100만 명"]),
    ("세계적으로는 약 1.3억 명에 달합니다", ["약 1.3억 명"]),
    ("2018년 약 823억 원에서 2022년 1,765억 원으로", ["약 823억 원", "1,765억 원"]),
    ("5년 사이 약 114% 증가했습니다", ["약 114%"]),
    ("2025년 약 132억 달러에서 2035년 약 344억 달러로 성장", ["약 132억 달러", "약 344억 달러"]),
    ("연평균 성장률은 약 10.1%로 제시되어 있습니다", ["약 10.1%"]),
    ("2025년 기준 국내 치매관리비용은 약 27조에 육박하며", ["약 27조"]),
    ("제주지역 치매관리비용만 약 3,400억 원에 달하는 것으로 추산됨", ["약 3,400억 원"]),
    ("제주도의 65세 이상 고령인구 비율은 2025년 19.4%로", ["19.4%"]),
    ("MCI에서 치매로의 연간 전환율은 약 5~10%로 보고되고", ["약 5~10%"]),
    ("검사당 평균 25만~30만 원", ["평균 25만~30만 원"]),
    ("200개 기관 확보 시 연간 총거래액 약 9.6억 원", ["200개 기관", "약 9.6억 원"]),
    ("사용자당 12주 프로그램 이용료 24만 원을 가정할 경우", ["24만 원"]),
    ("치료제 실제 반응률을 약 52~60% 수준으로 제시합니다", ["약 52~60%"]),
    ("아토피피부염 환자와 정상 대조군 67명의 임상 샘플을 수집하고", ["67명"]),
    ("약 1,000종 gene expression 기반 분석", ["약 1,000종"]),
    ("키트당 약 30만 원의 반복 검사 매출을 유도하며", ["약 30만 원"]),
    ("3차 병원 1곳과 임상데이터 확보 협업 진행", ["1곳"]),
    ("biologics/JAK inhibitor 환자 중심 연 2~3회 반복검사", ["연 2~3회"]),
    ("2029년 100만 달러 목표", ["100만 달러"]),
    ("병원당 연 3,000만~5,000만 원 수준의 SaaS/CDSS 계약", ["연 3,000만~5,000만 원"]),
]


@pytest.mark.parametrize("text,expected", CORPUS, ids=[t[:20] for t, _ in CORPUS])
def test_corpus(text, expected):
    assert matches(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "2026-08-01 기준이다",  # 날짜
        "2026년 4월 23일 세브란스병원에 제출했으며",
        "26.09.30. 까지 기술이전 완료",
        "제 3장을 참조한다",  # 순번·구조
        "제 12조에 따른다",
        "표 2 에 정리했다",
        "1. 첫 번째 항목이다",  # 목록 번호
        "3개월간 진행한다",  # 기간
        "2차년도 계획이다",
        "12주 인지기능 케어 프로그램",
        "5분 부착, 무통증",
        "TRL 6 수준이다",  # 단계·등급
        "4단계로 나눈다",
        "세 가지가 아니라 3가지다",  # 목록 개수
        "65세 이상 고령자",  # 연령
        "1차, 2차 치료 시도 끝에",  # 시도 순번
        "긍정적 가능성을 보여주고 있어[4], 맞춤형 콘텐츠",  # 참고문헌 각주
        "전이 효과(transfer effect)를 보이고[11, 12]",
    ],
)
def test_non_claim_is_excluded(text):
    assert matches(text) == []


def test_exclusion_wins_over_claim():
    """제외를 먼저 소거한 뒤 대상을 찾는다 — 순서가 뒤바뀌면 기간·순번이 전부 걸린다."""
    assert matches("사업 기간 36개월, 총 3장 구성") == []


def test_approximation_is_not_double_counted():
    """`약 3,400억 원` 을 `약 3,400` 과 `3,400억 원` 두 건으로 세면 리포트가 부풀려진다."""
    assert matches("치매관리비용만 약 3,400억 원") == ["약 3,400억 원"]


def test_range_keeps_both_ends():
    """뒤쪽만 잡으면 앞의 값이 검증을 빠져나간다."""
    assert matches("검사당 25만~30만 원") == ["25만~30만 원"]


def test_comma_alone_is_not_a_number():
    assert matches("항목, 건별로 정리한다") == []


def test_fact_reference_and_exempt_marker_are_not_claims():
    text = "참여자 {{pilot_n_2025}} 이며 {{!17개 기관}} 과 협력했다"
    assert matches(text) == []


def test_strip_noise_counts_exempt_markers_and_keeps_offsets():
    text = "{{!17개 기관}} 과 42명"
    scanned, exempt = strip_noise(text)

    assert exempt == 1
    assert len(scanned) == len(text)  # 줄 번호·열 위치가 어긋나면 리포트가 엉뚱한 곳을 가리킨다


def test_line_numbers_are_one_based():
    text = "첫 줄\n둘째 줄\n참여자 42명\n"
    assert find_claims(text) == [(3, "42명")]


def test_multiple_claims_in_order():
    text = "42명이 3,200억 원 규모의 사업에서 12.5% 개선했다"
    assert matches(text) == ["42명", "3,200억 원", "12.5%"]
