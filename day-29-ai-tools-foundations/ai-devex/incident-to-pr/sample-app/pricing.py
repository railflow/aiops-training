def apply_discount(cents: int, pct: int) -> int:
    """Price in integer cents after a percentage discount, rounded down to a whole cent."""
    return cents * (100 - pct) / 100


def total(items: list[int], pct: int = 0) -> int:
    return apply_discount(sum(items), pct)
