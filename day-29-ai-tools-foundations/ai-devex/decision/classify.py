#!/usr/bin/env python3
"""Flaky-test triage as a DECISION, not a chat: input a failure record, output {label, probability, reasons}.
Two backends with the same output shape:
  heuristic   offline rules (a stand-in with the right interface; it is not a model)
  jev         the Jev decision model through OpenRouter's alpha Decisions API (needs OPENROUTER_API_KEY; not run by the author, see README)
The point of the exercise is the surrounding contract (probability, thresholds, a human-review band, metrics), which is the same for any decision model."""
import json
import os
import sys
import urllib.error
import urllib.request

FLAKY_WORDS = ["timeout", "timed out", "connection reset", "econnrefused", "already in use", "stale element", "oomkilled", "ordering"]

JEV_MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.13")  # id as shown on OpenRouter's docs on 2026-11-05; ids change, so it is overridable
JEV_URL = os.environ.get("JEV_URL", "https://openrouter.ai/api/alpha/decisions")

QUESTIONS = {
    "flaky": {"type": "noul", "instructions": "Is this failure caused by timing, networking, ordering, shared resources or infrastructure rather than a defect in the code under test?"},
    "history": {"type": "noul", "instructions": "Does the test's pass history on the main branch suggest it passes most of the time without changes?"},
    "retry": {"type": "noul", "instructions": "Did the test pass when it was simply retried?"},
    "touches": {"type": "noul", "instructions": "Does the change touch the code that this test exercises?"},
}


def classify_heuristic(rec):
    score, reasons = 0.5, []
    err = rec["error"].lower()
    if any(w in err for w in FLAKY_WORDS):
        score += 0.25
        reasons.append("error text looks like timing/network/infrastructure")
    elif err.startswith(("assertionerror: values differ", "test failed", "process exited")):
        reasons.append("error text is uninformative")
    else:
        score -= 0.2
        reasons.append("error text looks like a logic failure")
    p = rec["passes_last_20_on_main"]
    if 6 <= p <= 19:
        score += 0.15
        reasons.append(f"passes {p}/20 on main: intermittent")
    elif p <= 2:
        score -= 0.15
        reasons.append(f"passes only {p}/20 on main: consistently broken")
    if rec["retry_passed"]:
        score += 0.15
        reasons.append("passed on retry")
    if rec["change_touches_code_under_test"]:
        score -= 0.25
        reasons.append("change touches the code under test")
    return _out(max(0.01, min(0.99, score)), reasons)


def _out(p, reasons):
    return {"label": "flaky" if p >= 0.5 else "real", "probability": round(p, 3), "reasons": reasons}


def combine_jev_answers(answers):
    """Turn Jev's per-question probabilities into one flaky probability and readable reasons. The weights are ours, a starting point to tune on labelled data."""
    g = lambda k: answers[k]["noul"]  # noqa: E731
    p = 0.55 * g("flaky") + 0.2 * g("history") + 0.15 * g("retry") + 0.1 * (1 - g("touches"))
    reasons = [f"{k}: {answers[k]['noul']:.2f} - {QUESTIONS[k]['instructions']}" for k in QUESTIONS]
    return _out(max(0.0, min(1.0, p)), reasons)


def classify_jev(rec, url=None):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    state = {k: rec[k] for k in ("test", "error", "passes_last_20_on_main", "retry_passed", "change_touches_code_under_test")}
    body = json.dumps({"model": JEV_MODEL, "state": state, "questions": QUESTIONS}).encode()
    req = urllib.request.Request(url or JEV_URL, data=body, method="POST", headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Decisions API HTTP {e.code}: {e.read()[:200].decode(errors='replace')}") from None
    out = combine_jev_answers(data["answers"])
    out["cost"] = (data.get("usage") or {}).get("cost")
    return out


BACKENDS = {"heuristic": classify_heuristic, "jev": classify_jev}


def main():
    rec = json.loads(sys.stdin.readline())
    print(json.dumps(BACKENDS[sys.argv[1] if len(sys.argv) > 1 else "heuristic"](rec), indent=2))


if __name__ == "__main__":
    main()
