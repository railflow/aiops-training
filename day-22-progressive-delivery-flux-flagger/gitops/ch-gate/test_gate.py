import gate


def test_not_enough_data_passes_with_a_note():
    code, msg = gate.decide(5, 5, 5, 20)
    assert code == 200 and "not enough data" in msg


def test_error_rate_above_threshold_fails():
    code, msg = gate.decide(100, 10, 5, 20)
    assert code == 500 and "10.0%" in msg


def test_error_rate_at_or_below_threshold_passes():
    assert gate.decide(100, 5, 5, 20)[0] == 200


def test_query_excludes_primary_pods():
    sql = gate.build_query("shop-frontend", 3)
    assert "NOT LIKE '%-primary-%'" in sql
    assert "INTERVAL 3 MINUTE" in sql


def test_service_name_is_validated():
    import pytest
    with pytest.raises(ValueError):
        gate.build_query("shop'; DROP TABLE x; --", 3)
