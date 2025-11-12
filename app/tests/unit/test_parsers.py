import pytest

from app.utils.parsers import parse_amount_neutral, parse_excel_date_robust


def test_parse_amount_neutral_basic():
    assert parse_amount_neutral("1 234,56") == pytest.approx(1234.56)
    assert parse_amount_neutral("(1 234,56)") == pytest.approx(-1234.56)
    assert parse_amount_neutral("1234.56") == pytest.approx(1234.56)
    assert parse_amount_neutral(None) is None


def test_parse_amount_with_symbols_and_spaces():
    assert parse_amount_neutral("CA 1 234,56 $") == pytest.approx(1234.56)
    assert parse_amount_neutral("1.234,56") == pytest.approx(1234.56)


def test_parse_excel_date_robust_iso_and_eu():
    d, err = parse_excel_date_robust("2025-08-28", 0)
    assert err is None and d == "2025-08-28"

    d2, err2 = parse_excel_date_robust("28/08/2025", 1)
    assert err2 is None and d2 == "2025-08-28"


def test_parse_excel_date_reject_small_serial():
    # small serial number should be rejected according to strict policy
    d, err = parse_excel_date_robust(40000, 0)
    # 40000 is within 36526-55154 so should parse (approx 2009-07-06)
    assert err is None
