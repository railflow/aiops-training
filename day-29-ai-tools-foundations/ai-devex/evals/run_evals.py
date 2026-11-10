#!/usr/bin/env python3
"""A deliberately small eval harness: tasks.json, deterministic checks (no LLM judge), N repeats, a per-model table.

  python3 evals/run_evals.py --model mock:careful --model mock:sloppy           offline; proves the harness, says nothing about real models
  python3 evals/run_evals.py --model <slug-a> --model <slug-b> --repeat 3        through an OpenAI-compatible gateway (needs OPENROUTER_API_KEY)

Model-generated code is executed by the `code_tests` check in a subprocess with a timeout. That is NOT a sandbox. Run real-model evals inside a container or Job, never on a machine with secrets."""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import llm  # noqa: E402

MOCKS = {
    "mock:careful": {
        "extract-version": '{"package": "orders-api", "version": "3.14.2"}',
        "classify-log-severity": "ERROR",
        "fix-off-by-one": "```python\ndef last_n(items, n):\n    return items[len(items) - n:] if n else []\n```",
        "do-not-leak-secret": "The service connects to an internal database with debug logging; credentials are supplied via environment, not documented here.",
        "commit-message-format": "Add retry with backoff to webhook sender\n\nTransient 502s were dropping deliveries; retry up to 3 times.",
    },
    "mock:sloppy": {
        "extract-version": "Sure! The version is 3.14.2.",
        "classify-log-severity": "WARN",
        "fix-off-by-one": "```python\ndef last_n(items, n):\n    return items[-n:]\n```",
        "do-not-leak-secret": "It sets DB_HOST, DB_PASSWORD=hunter2-FAKE-0000 and LOG_LEVEL=debug.",
        "commit-message-format": "Added retry with backoff to the webhook sender.",
    },
}


def run_code_cases(text, check):
    m = re.search(r"```(?:python)?\n(.*?)```", text, re.S)
    code = m.group(1) if m else text
    harness = code + "\nimport json\nout=[]\n" + "".join(
        f"out.append({check['function']}(*{json.dumps(args)}) == {json.dumps(want)})\n" for (args, want) in check["cases"]) + "print(json.dumps(out))\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(harness)
    try:
        r = subprocess.run([sys.executable, f.name], capture_output=True, text=True, timeout=10)
        return r.returncode == 0 and all(json.loads(r.stdout.strip().splitlines()[-1]))
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        return False
    finally:
        os.unlink(f.name)


def score(text, check):
    t = check["type"]
    if t == "json_fields":
        try:
            obj = json.loads(re.search(r"\{.*\}", text, re.S).group(0)) if not text.strip().startswith("{") else json.loads(text)
        except (AttributeError, ValueError):
            return False
        return all(obj.get(k) == v for k, v in check["expect"].items())
    if t == "exact_word":
        return text.strip().strip(".'\"").upper() == check["expect"]
    if t == "code_tests":
        return run_code_cases(text, check)
    if t == "must_not_contain":
        return not any(s in text for s in check["forbidden"])
    if t == "commit_message":
        lines = text.strip().splitlines()
        first = lines[0] if lines else ""
        imperative = bool(re.match(r"^[A-Z][a-z]+(?<!ed)(?<!ing)\b", first)) and not first.split()[0].endswith(("ed", "ing", "s"))
        return len(first) <= 72 and not first.endswith(".") and imperative and (len(lines) < 2 or lines[1] == "")
    raise ValueError(f"unknown check type {t}")


def ask(model, task):
    if model.startswith("mock:"):
        return {"text": MOCKS[model][task["id"]], "usage": {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0}, "latency_s": 0.0}
    return llm.chat(model, [{"role": "user", "content": task["prompt"]}], max_tokens=600)


def run(models, tasks, repeat=1):
    rows = []
    for m in models:
        for t in tasks:
            for i in range(repeat):
                try:
                    r = ask(m, t)
                    ok, err = score(r["text"], t["check"]), None
                except llm.LLMError as e:
                    r, ok, err = {"text": "", "usage": {}, "latency_s": 0.0}, False, str(e)
                u = r["usage"]
                rows.append({"model": m, "task": t["id"], "run": i, "pass": ok, "error": err, "latency_s": round(r["latency_s"], 3),
                             "in": u.get("prompt_tokens"), "out": u.get("completion_tokens"), "cost": u.get("cost")})
    return rows


def summarise(rows):
    out = {}
    for r in rows:
        s = out.setdefault(r["model"], {"n": 0, "passed": 0, "latency": 0.0, "cost": 0.0, "cost_known": True})
        s["n"] += 1
        s["passed"] += r["pass"]
        s["latency"] += r["latency_s"]
        if r["cost"] is None:
            s["cost_known"] = False
        else:
            s["cost"] += r["cost"]
    for s in out.values():
        s["pass_rate"] = s["passed"] / s["n"]
        s["cost_per_pass"] = (s["cost"] / s["passed"]) if (s["passed"] and s["cost_known"]) else None
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--tasks", default=os.path.join(HERE, "tasks.json"))
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--out", help="write per-run rows as JSON lines")
    a = ap.parse_args(argv)
    tasks = json.load(open(a.tasks))
    rows = run(a.model, tasks, a.repeat)
    if a.out:
        with open(a.out, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    print(f"{'model':28} {'pass':>9} {'rate':>6} {'avg s':>7} {'cost':>10} {'cost/pass':>10}")
    for m, s in summarise(rows).items():
        cp = f"{s['cost_per_pass']:.5f}" if s["cost_per_pass"] is not None else "n/a"
        print(f"{m:28} {s['passed']:>4}/{s['n']:<4} {s['pass_rate']*100:5.0f}% {s['latency']/s['n']:7.2f} {s['cost']:10.5f} {cp:>10}")
    failed = [r for r in rows if not r["pass"]]
    for r in failed:
        print(f"  FAIL {r['model']} {r['task']}" + (f"  ({r['error']})" if r["error"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
