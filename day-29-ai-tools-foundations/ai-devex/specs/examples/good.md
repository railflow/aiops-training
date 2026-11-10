---
id: SPEC-0042
title: Retry flaky network calls in the webhook sender
owner: platform-team
status: approved
risk: low
---

## Problem

The webhook sender gives up after one failure. About 3% of deliveries fail on transient 502s and are lost; on-call replays them by hand.

## Acceptance criteria

- [ ] AC-1: A 502 or a timeout is retried up to 3 times with exponential backoff starting at 200 ms.
- [ ] AC-2: A 4xx other than 429 is never retried.
- [ ] AC-3: After the final failure the delivery is written to the dead-letter table with the last error.

## Non-goals

- Changing the payload format.
- Ordering guarantees between deliveries.

## Constraints

- Public function signatures in `sender.py` do not change.
- Do not touch `deploy/` or `.forgejo/`.

## Test plan

- AC-1: `pytest tests/test_sender.py::test_retries_transient_errors`
- AC-2: `pytest tests/test_sender.py::test_no_retry_on_400`
- AC-3: `pytest tests/test_sender.py::test_dead_letter_after_retries`

## Rollback

Revert the commit; no migration is involved.
