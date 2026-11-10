#!/usr/bin/env python3
"""Generate a SYNTHETIC labelled dataset of failing CI test runs: flaky (infrastructure/timing noise) vs real (a defect in the change).
Seeded, so everyone gets the same file. It is made up: real data has different mess. Label noise is injected on purpose (about 8%) so scores are not 1.0.
  python3 decision/make_dataset.py --n 300 --seed 7 > decision/dataset.jsonl"""
import argparse
import json
import random

FLAKY_ERRORS = ["TimeoutError: waited 30s for element #checkout-button", "ConnectionResetError: [Errno 104] Connection reset by peer",
                "socket.timeout: timed out", "AssertionError: expected 3 rows, got 2 (ordering differs)", "Port 8080 already in use",
                "Error: ECONNREFUSED 127.0.0.1:5432", "Stale element reference: element is not attached to the page", "OOMKilled: container exceeded memory limit"]
REAL_ERRORS = ["AssertionError: expected 42, got 41", "TypeError: unsupported operand type(s) for +: 'int' and 'str'", "KeyError: 'customer_id'",
               "AssertionError: status 500 != 200", "NullPointerException at OrderService.total(OrderService.java:88)", "ZeroDivisionError: division by zero",
               "AssertionError: expected 'EUR', got 'USD'", "ImportError: cannot import name 'price_with_tax'"]
NEUTRAL_ERRORS = ["AssertionError: values differ", "Test failed", "Process exited with code 1"]


def make(n, seed):
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        flaky = rnd.random() < 0.4
        pool = FLAKY_ERRORS if flaky else REAL_ERRORS
        roll = rnd.random()
        error = rnd.choice(NEUTRAL_ERRORS) if roll < 0.2 else rnd.choice(pool if roll < 0.9 else (REAL_ERRORS if flaky else FLAKY_ERRORS))
        if flaky:
            passes_last20 = rnd.randint(8, 19)
            retry_passed = rnd.random() < 0.8
            touches = rnd.random() < 0.15
        else:
            passes_last20 = rnd.choice([0, 0, 0, 1, 2, 18, 19, 20])
            retry_passed = rnd.random() < 0.1
            touches = rnd.random() < 0.8
        label = "flaky" if flaky else "real"
        if rnd.random() < 0.08:
            label = "real" if label == "flaky" else "flaky"
        rows.append({"id": f"f{i:04d}", "test": f"tests/test_{rnd.choice(['checkout', 'orders', 'billing', 'login', 'search'])}.py::test_{rnd.randint(1, 40)}",
                     "error": error, "passes_last_20_on_main": passes_last20, "retry_passed": retry_passed,
                     "change_touches_code_under_test": touches, "label": label})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    for r in make(a.n, a.seed):
        print(json.dumps(r))


if __name__ == "__main__":
    main()
