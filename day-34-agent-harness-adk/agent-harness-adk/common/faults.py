"""Failure injection for the lab. CHAOS="repo-a:stuck+bad_test,repo-b:oom@1,repo-c:rate_limit:3".

Faults a worker understands (the mock model reads the first group; the process reads the rest):
  stuck, bad_test, bad_tool, malformed_json, malformed_args   how the mock model misbehaves
  rate_limit:N                                                the first N model calls answer HTTP 429
  oom@K, crash@K                                              the worker dies on attempt K (137 like an OOM kill, or 1)
  hang                                                        the first test run never returns (exercises step timeouts)
  die_at_test@K                                               the worker is killed (137) on its Kth test run, once (exercises resume)
"""
import os
import time
from pathlib import Path


class RateLimited(Exception):
    def __init__(self, retry_after: float = 0.0):
        super().__init__("429 Too Many Requests")
        self.retry_after = retry_after


def parse(chaos: str, repo: str) -> list[str]:
    for entry in filter(None, chaos.split(",")):
        name, _, spec = entry.partition(":")
        if name == repo:
            return spec.split("+")
    return []


MODEL_FAULTS = {"stuck", "bad_test", "bad_tool", "malformed_json", "malformed_args"}


def model_faults(faults: list[str]) -> frozenset:
    return frozenset(f for f in faults if f in MODEL_FAULTS)


class RateLimiter:
    """Raises RateLimited for the first N calls, like a gateway under load."""

    def __init__(self, faults: list[str]):
        self.left = next((int(f.split(":")[1]) for f in faults if f.startswith("rate_limit:")), 0)

    def check(self):
        if self.left > 0:
            self.left -= 1
            raise RateLimited(retry_after=0.01)


def die_if_planned(faults: list[str], attempt: int):
    for f in faults:
        if f == f"oom@{attempt}":
            os._exit(137)
        if f == f"crash@{attempt}":
            os._exit(1)


_tests_run = 0


def die_at_test(faults: list[str], state_dir: str, repo: str):
    """Kill the worker (like an OOM) on the Kth test run, once. A marker file stops it dying again after the restart."""
    global _tests_run
    _tests_run += 1
    for f in faults:
        if f.startswith("die_at_test@") and _tests_run == int(f.split("@")[1]):
            marker = Path(state_dir) / f"{repo}.died"
            if not marker.exists():
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.touch()
                os._exit(137)


def hang_if_planned(faults: list[str], seconds: float = 30.0):
    if "hang" in faults:
        faults.remove("hang")
        time.sleep(seconds)
