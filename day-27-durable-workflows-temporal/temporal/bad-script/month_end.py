#!/usr/bin/env python3
"""A month-end batch the way it is usually written. DO NOT COPY THIS PATTERN.

Five steps, a hand-rolled retry loop, and a state file so "it can resume". Each choice below is a bug you will meet in real life:
  * the state file is written AFTER a step finishes, so a crash in the middle of a step redoes the whole step
  * step 4 has side effects (emails) with no idempotency key, so a redo sends duplicates
  * retry is a bare loop: no jitter, no cap, every error is retried (even "your data is invalid"), and the sleeps block the process
  * progress lives in a local file next to the process: a new pod or a new laptop has none of it
  * nothing tells you where it is, apart from print statements

Timings are scaled down with STEP_SECONDS so you can watch it fail. Run:  python3 month_end.py BATCH-2026-11
"""
import json
import os
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
STATE = HERE / "state.json"
OUTBOX = HERE / "outbox.log"
STEP_SECONDS = float(os.environ.get("STEP_SECONDS", "3"))
CUSTOMERS = 8


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"done": []}


def save_state(state):
    STATE.write_text(json.dumps(state))


def verify_records(batch):
    print("  step 1: verifying records")
    time.sleep(STEP_SECONDS)


def generate_pdfs(batch):
    print(f"  step 2: generating PDFs ({CUSTOMERS} x {STEP_SECONDS}s)")
    for i in range(CUSTOMERS):
        time.sleep(STEP_SECONDS)
        print(f"    pdf {i + 1}/{CUSTOMERS}")


def check_irs(batch):
    print("  step 3: calling the IRS API")
    if random.random() < float(os.environ.get("IRS_FAIL_RATE", "0.5")):
        raise ConnectionError("IRS API timed out")
    time.sleep(STEP_SECONDS)


def email_customers(batch):
    print("  step 4: emailing customers")
    for i in range(CUSTOMERS):
        time.sleep(STEP_SECONDS / 2)
        with OUTBOX.open("a") as f:  # stand-in for a real mail API: every line is a customer who got an email
            f.write(f"{batch} customer-{i + 1}\n")
        print(f"    sent to customer-{i + 1}")


def archive(batch):
    print("  step 5: archiving")
    time.sleep(STEP_SECONDS)


STEPS = [verify_records, generate_pdfs, check_irs, email_customers, archive]


def with_retry(fn, batch, attempts=5):
    for attempt in range(attempts):
        try:
            return fn(batch)
        except Exception as e:  # retries everything, including bugs
            wait = 2 ** attempt  # no jitter, no cap, and nobody else is told
            print(f"  {fn.__name__} failed ({e}); sleeping {wait}s then retrying")
            time.sleep(wait)
    raise RuntimeError(f"{fn.__name__} failed after {attempts} attempts")


def main(batch):
    state = load_state()
    for step in STEPS:
        if step.__name__ in state["done"]:
            print(f"skipping {step.__name__} (already done)")
            continue
        print(f"running {step.__name__}")
        with_retry(step, batch)
        state["done"].append(step.__name__)
        save_state(state)
    print("batch complete")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: month_end.py BATCH_ID")
    main(sys.argv[1])
