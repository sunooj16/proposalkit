"""numbers.py — 주장성 수치 탐지.

여기 케이스가 곧 숫자 클래스 정의의 실체다. T-G1 코퍼스로 확장한다 (T-10).
"""

import pytest

from ppsk.numbers import find_claims, strip_noise


def matches(text):
    return [m for _, m in find_claims(text)]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("매출은 3,200억 원이다", "3,200억 원"),
        ("참여자 42명이 등록했다", "42명"),
        ("정확도가 12.5% 올랐다", "12.5%"),
        ("효율이 3배 개선됐다", "3배"),
        ("17개 기관과 협력했다", "17개 기관"),
        ("약 1,500 규모다", "약 1,500"),
    ],
)
def test_claim_is_detected(text, expected):
    assert matches(text) == [expected]


@pytest.mark.parametrize(
    "text",
    [
        "2026-08-01 기준이다",  # 날짜
        "제 3장을 참조한다",  # 순번·구조
        "표 2 에 정리했다",
        "1. 첫 번째 항목이다",  # 목록 번호
        "3개월간 진행한다",  # 기간
        "2차년도 계획이다",
        "TRL 6 수준이다",  # 단계·등급
        "4단계로 나눈다",
        "세 가지가 아니라 3가지다",  # 목록 개수
    ],
)
def test_non_claim_is_excluded(text):
    assert matches(text) == []


def test_exclusion_wins_over_claim():
    """제외를 먼저 소거한 뒤 대상을 찾는다 — 순서가 뒤바뀌면 기간·순번이 전부 걸린다."""
    assert matches("사업 기간 36개월, 총 3장 구성") == []


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
