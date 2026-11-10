#!/usr/bin/env python3
"""Score a decision backend on the labelled dataset and show what thresholds buy you.

  python3 decision/make_dataset.py > decision/dataset.jsonl
  python3 decision/evaluate.py --backend heuristic --hi 0.75 --lo 0.35

Policy: p >= hi -> auto-act as FLAKY (retry/quarantine); p <= lo -> treat as REAL (block, page the author); between -> a human decides.
Metrics: precision/recall of the auto-flaky bucket (a wrong auto-flaky hides a real bug, so precision matters most), share sent to humans, and a sweep."""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import classify  # noqa: E402


def decide(p, hi, lo):
    return "auto_flaky" if p >= hi else ("auto_real" if p <= lo else "human")


def prf(rows, pred_flaky):
    tp = sum(1 for r, p in zip(rows, pred_flaky) if p and r["label"] == "flaky")
    fp = sum(1 for r, p in zip(rows, pred_flaky) if p and r["label"] != "flaky")
    fn = sum(1 for r, p in zip(rows, pred_flaky) if not p and r["label"] == "flaky")
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return precision, recall, tp, fp, fn


def evaluate(rows, probs, hi, lo):
    decisions = [decide(p, hi, lo) for p in probs]
    n = len(rows)
    auto_flaky = [d == "auto_flaky" for d in decisions]
    precision, recall, tp, fp, fn = prf(rows, auto_flaky)
    auto_real_wrong = sum(1 for r, d in zip(rows, decisions) if d == "auto_real" and r["label"] == "flaky")
    return {"n": n, "human_share": decisions.count("human") / n, "auto_flaky": sum(auto_flaky), "precision": precision, "recall": recall,
            "fp_hidden_real_bugs": fp, "auto_real_but_was_flaky": auto_real_wrong}


def sweep(rows, probs):
    out = []
    for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        p, r, *_ = prf(rows, [x >= t for x in probs])
        out.append((t, p, r))
    return out


def fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=os.path.join(HERE, "dataset.jsonl"))
    ap.add_argument("--backend", default="heuristic", choices=sorted(classify.BACKENDS))
    ap.add_argument("--hi", type=float, default=0.75)
    ap.add_argument("--lo", type=float, default=0.35)
    a = ap.parse_args(argv)
    rows = [json.loads(line) for line in open(a.data)]
    probs = [classify.BACKENDS[a.backend](r)["probability"] for r in rows]
    m = evaluate(rows, probs, a.hi, a.lo)
    print(f"backend={a.backend}  n={m['n']}  hi={a.hi} lo={a.lo}")
    print(f"auto-flaky: {m['auto_flaky']}  precision={fmt(m['precision'])}  recall={fmt(m['recall'])}  real bugs wrongly auto-flaked={m['fp_hidden_real_bugs']}")
    print(f"sent to a human: {m['human_share']*100:.0f}%   flaky tests wrongly treated as real: {m['auto_real_but_was_flaky']}")
    print("\nsingle-threshold sweep (no review band):  threshold  precision  recall")
    for t, p, r in sweep(rows, probs):
        print(f"                                           {t:.1f}        {fmt(p)}       {fmt(r)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
