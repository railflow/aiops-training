"""A small inventory library. The tests cover only part of it, which is the point of the exercise."""


def add_item(stock: dict, sku: str, qty: int) -> dict:
    if qty <= 0:
        raise ValueError("qty must be positive")
    stock[sku] = stock.get(sku, 0) + qty
    return stock


def remove_item(stock: dict, sku: str, qty: int) -> dict:
    have = stock.get(sku, 0)
    if qty > have:
        raise ValueError("not enough stock")
    stock[sku] = have - qty
    if stock[sku] == 0:
        del stock[sku]
    return stock


def low_stock(stock: dict, threshold: int = 5) -> list:
    return sorted(sku for sku, qty in stock.items() if qty < threshold)


def total_value(stock: dict, prices: dict) -> float:
    total = 0.0
    for sku, qty in stock.items():
        if sku not in prices:
            raise KeyError(f"no price for {sku}")
        total += qty * prices[sku]
    return round(total, 2)


def restock_plan(stock: dict, target: int) -> dict:
    plan = {}
    for sku, qty in sorted(stock.items()):
        if qty < target:
            plan[sku] = target - qty
    return plan
