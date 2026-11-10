#!/usr/bin/env python3
"""From incident to reviewed PR: alert -> context -> triage -> fix agent -> measure -> PR -> a DIFFERENT reviewer model -> human gate.

Every stage has an OFFLINE implementation (canned or rule-based, clearly labelled) so you can run the whole thing on a laptop with no keys, and a REAL hook
you switch on with environment variables. Real hooks that were not run by the author are marked NOT RUN in the page and in the README.

  python3 pipeline.py                      offline end-to-end (mock fix agent, mock reviewer); stops at the human gate
  python3 pipeline.py --approve-as dana    also records the human decision (for the agreement metric)
  FIX_MODEL=<slug-a> REVIEW_MODEL=<slug-b> OPENROUTER_API_KEY=... python3 pipeline.py --real-models   fix and review through the gateway

In production the same stage functions are Temporal activities (or k8s Jobs) and the Run record below becomes ClickHouse rows; see the course page."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import llm  # noqa: E402

MEASURE = os.path.join(HERE, "..", "..", "..", "capstone", "measure", "measure.py")
ALLOWED_PATHS = {"pricing.py"}


class BudgetExceeded(Exception):
    pass


class Budget:
    def __init__(self, max_usd=0.50, max_calls=6, max_seconds=600):
        self.max_usd, self.max_calls, self.max_seconds = max_usd, max_calls, max_seconds
        self.usd, self.calls, self.t0 = 0.0, 0, time.time()

    def charge(self, usd=0.0):
        self.calls += 1
        self.usd += usd or 0.0
        if self.usd > self.max_usd or self.calls > self.max_calls or time.time() - self.t0 > self.max_seconds:
            raise BudgetExceeded(f"budget exceeded: ${self.usd:.4f}/{self.max_usd}, {self.calls}/{self.max_calls} calls, {time.time()-self.t0:.0f}/{self.max_seconds}s")


class Run:
    """Append-only record of what happened. One JSON object per line: the same shape you would insert into ClickHouse."""

    def __init__(self, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        self.path = os.path.join(out_dir, "run.jsonl")
        open(self.path, "w").close()
        self.t0 = time.time()
        self.events = []

    def log(self, stage, **kw):
        ev = {"t": round(time.time() - self.t0, 3), "stage": stage, **kw}
        self.events.append(ev)
        open(self.path, "a").write(json.dumps(ev) + "\n")
        print(f"[{ev['t']:7.2f}s] {stage:10} " + " ".join(f"{k}={v}" for k, v in kw.items() if k != "detail"))
        return ev


def triage(alert, context):
    """Offline decision: is this a code defect we should try to fix? Same output contract as decision/classify.py: label, probability, reasons."""
    p, reasons = 0.3, []
    if context.get("same_error_before_deploy", 1) == 0:
        p += 0.35
        reasons.append("error never seen before the last deploy")
    if context.get("deploys_last_24h"):
        p += 0.2
        reasons.append("a deploy landed shortly before the first error")
    if context.get("count_last_hour", 0) >= 10:
        p += 0.1
        reasons.append("error is frequent, not a one-off")
    return {"label": "code_defect" if p >= 0.5 else "not_code", "probability": round(min(p, 0.99), 2), "reasons": reasons}


def parse_python_block(text):
    m = re.search(r"```(?:python)?\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).rstrip() + "\n"


MOCK_FIX = '''def apply_discount(cents: int, pct: int) -> int:
    """Price in integer cents after a percentage discount, rounded down to a whole cent."""
    return cents * (100 - pct) // 100


def total(items: list[int], pct: int = 0) -> int:
    return apply_discount(sum(items), pct)
'''


def fix_agent(workdir, alert, context, budget, real_model=None):
    path = os.path.join(workdir, "pricing.py")
    before = open(path).read()
    if real_model:
        prompt = (f"Alert: {alert['description']}\nContext: {json.dumps(context)}\n\nFile pricing.py:\n```python\n{before}```\n"
                  "Reply with the complete corrected pricing.py in one ```python block. Change only what is needed. Do not edit tests.")
        r = llm.chat(real_model, [{"role": "user", "content": prompt}], max_tokens=800)
        budget.charge(r["usage"].get("cost"))
        after, cost = parse_python_block(r["text"]), r["usage"].get("cost")
    else:
        budget.charge(0.0)
        after, cost = MOCK_FIX, 0.0
    open(path, "w").write(after)
    return {"before": before, "after": after, "cost": cost}


def changed_files(orig, new):
    changed = []
    for root, _, files in os.walk(new):
        for f in files:
            if "__pycache__" in root or f.endswith(".pyc") or ".pytest_cache" in root or f in (".coverage", "coverage.xml") or "reports" in root.split(os.sep):
                continue
            rel = os.path.relpath(os.path.join(root, f), new)
            o = os.path.join(orig, rel)
            if not os.path.exists(o) or open(o, "rb").read() != open(os.path.join(root, f), "rb").read():
                changed.append(rel)
    return sorted(changed)


def measure(workdir):
    """Uses the course's real measure.py (what `build.sh measure` runs). Falls back to plain pytest if pytest-cov is missing."""
    r = subprocess.run([sys.executable, MEASURE, "--dir", workdir, "--run-id", "i2pr", "--iteration", "0"], capture_output=True, text=True)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"build_ok": 0, "tests_failed": None, "line_coverage_pct": None, "error": (r.stderr or r.stdout)[-300:]}


def reviewer(diff_text, files, m, real_model=None, author_model=None, budget=None):
    if real_model:
        if real_model == author_model or real_model.split("/")[0] == (author_model or "").split("/")[0]:
            raise ValueError("reviewer must be a different model, and preferably from a different vendor, than the author")
        r = llm.chat(real_model, [{"role": "user", "content": "You are a skeptical code reviewer. Reply on the first line with exactly APPROVE or REQUEST_CHANGES, "
                                   "then at most five bullet points.\n\nDiff:\n" + diff_text[:6000] + f"\n\nMeasured: {json.dumps(m)}"}], max_tokens=400)
        if budget:
            budget.charge(r["usage"].get("cost"))
        first = r["text"].strip().splitlines()[0].strip().upper() if r["text"].strip() else ""
        return {"decision": "approve" if first.startswith("APPROVE") else "request_changes", "comments": r["text"], "cost": r["usage"].get("cost")}
    problems = []
    if set(files) - ALLOWED_PATHS:
        problems.append(f"touches files outside the allowed set: {sorted(set(files) - ALLOWED_PATHS)}")
    if m.get("tests_failed"):
        problems.append("tests still fail")
    if (m.get("line_coverage_pct") or 0) < 80:
        problems.append("coverage below 80%")
    return {"decision": "request_changes" if problems else "approve", "comments": "; ".join(problems) or "diff is small, tests pass, coverage ok (mock rule-based reviewer)", "cost": 0.0}


def forgejo_create_pr(base_url, token, repo, head, base, title, body):
    """POST /api/v1/repos/{owner}/{repo}/pulls. The branch must already be pushed. Not run against a real Forgejo by the author; see tests (fake server)."""
    req = urllib.request.Request(f"{base_url.rstrip('/')}/api/v1/repos/{repo}/pulls", method="POST",
                                 data=json.dumps({"head": head, "base": base, "title": title, "body": body}).encode(),
                                 headers={"Authorization": "token " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def run_pipeline(out_dir, *, real_models=False, approve_as=None, budget=None):
    budget = budget or Budget()
    run = Run(out_dir)
    alert = json.load(open(os.path.join(HERE, "fixtures", "alert.json")))
    context = json.load(open(os.path.join(HERE, "fixtures", "context.json")))
    run.log("alert", id=alert["id"], name=alert["name"])
    run.log("context", source="fixtures/context.json (real: read-only ClickHouse query)", errors_last_hour=context["count_last_hour"])
    tr = triage(alert, context)
    run.log("triage", label=tr["label"], probability=tr["probability"])
    if tr["probability"] < 0.5:
        run.log("stopped", reason="not a code defect; route to a human or another playbook")
        return run
    work = tempfile.mkdtemp(prefix="i2pr-")
    orig = os.path.join(HERE, "sample-app")
    shutil.copytree(orig, os.path.join(work, "app"), ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".coverage", "reports", "coverage.xml"))
    app = os.path.join(work, "app")
    before = measure(app)
    run.log("baseline", tests_failed=before.get("tests_failed"), coverage=before.get("line_coverage_pct"))
    fix_model, review_model = os.environ.get("FIX_MODEL"), os.environ.get("REVIEW_MODEL")
    if real_models and not (fix_model and review_model):
        raise SystemExit("--real-models needs FIX_MODEL and REVIEW_MODEL (two different models)")
    try:
        fx = fix_agent(app, alert, context, budget, fix_model if real_models else None)
    except BudgetExceeded as e:
        run.log("stopped", reason=str(e))
        return run
    files = changed_files(orig, app)
    run.log("fix", files=",".join(files), cost=fx["cost"])
    if set(files) - ALLOWED_PATHS:
        run.log("stopped", reason=f"guardrail: agent changed files outside {sorted(ALLOWED_PATHS)}: {files}")
        return run
    after = measure(app)
    first_pass = int(after.get("build_ok") == 1 and after.get("tests_failed") == 0)
    run.log("measure", tests_failed=after.get("tests_failed"), coverage=after.get("line_coverage_pct"), first_pass_ci=first_pass)
    diff_text = subprocess.run(["diff", "-u", "-L", "a/pricing.py", "-L", "b/pricing.py", os.path.join(orig, "pricing.py"), os.path.join(app, "pricing.py")], capture_output=True, text=True).stdout
    pr = {"title": f"Fix: {alert['name']}", "head": f"ai/fix-{alert['id']}", "base": "main",
          "body": f"Alert {alert['id']}: {alert['description']}\n\nTriage: {tr['label']} ({tr['probability']}).\nTests failed before/after: {before.get('tests_failed')}/{after.get('tests_failed')}.\nCoverage: {before.get('line_coverage_pct')} -> {after.get('line_coverage_pct')}.\n\nThis PR was drafted by an AI agent. A human must review and merge.",
          "diff": diff_text}
    if os.environ.get("FORGEJO_URL") and os.environ.get("FORGEJO_TOKEN") and os.environ.get("FORGEJO_REPO"):
        res = forgejo_create_pr(os.environ["FORGEJO_URL"], os.environ["FORGEJO_TOKEN"], os.environ["FORGEJO_REPO"], pr["head"], pr["base"], pr["title"], pr["body"])
        run.log("pr", url=res.get("html_url"))
    else:
        json.dump(pr, open(os.path.join(out_dir, "pr.json"), "w"), indent=2)
        run.log("pr", written_to=os.path.join(out_dir, "pr.json"), note="no FORGEJO_* env: wrote the PR instead of opening it")
    time_to_pr = run.events[-1]["t"]
    rv = reviewer(diff_text, files, after, review_model if real_models else None, fix_model, budget)
    run.log("review", decision=rv["decision"], reviewer=review_model if real_models else "mock:rule-based", comments=rv["comments"][:120].replace("\n", " "))
    run.log("human-gate", status="awaiting-human" if not approve_as else "decided", by=approve_as or "-")
    human = "approve" if approve_as else None
    metrics = {"time_to_pr_s": time_to_pr, "cost_usd": round(budget.usd, 6), "calls": budget.calls, "first_pass_ci": first_pass,
               "reviewer_decision": rv["decision"], "human_decision": human, "reviewer_human_agree": (rv["decision"] == human) if human else None}
    run.log("metrics", **metrics)
    json.dump(metrics, open(os.path.join(out_dir, "metrics.json"), "w"), indent=2)
    shutil.rmtree(work, ignore_errors=True)
    return run


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--real-models", action="store_true")
    ap.add_argument("--approve-as")
    ap.add_argument("--max-usd", type=float, default=0.50)
    a = ap.parse_args(argv)
    run_pipeline(a.out, real_models=a.real_models, approve_as=a.approve_as, budget=Budget(max_usd=a.max_usd))
    return 0


if __name__ == "__main__":
    sys.exit(main())
