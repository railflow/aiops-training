import pricing


def test_discount_is_whole_cents():
    assert pricing.apply_discount(1999, 15) == 1699
    assert isinstance(pricing.apply_discount(1999, 15), int)


def test_no_discount():
    assert pricing.apply_discount(500, 0) == 500


def test_total_with_coupon():
    assert pricing.total([1999, 1], 50) == 1000
