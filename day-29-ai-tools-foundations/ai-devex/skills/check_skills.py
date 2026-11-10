#!/usr/bin/env python3
"""CI guard rails for a skills registry: every skill is a folder with SKILL.md. Reject what must never ship, warn about what rots.
  python3 skills/check_skills.py skills/examples                      lint every <dir>/SKILL.md under the path
  python3 skills/check_skills.py skills/examples --usage usage.jsonl --stale-days 90   also list skills nobody has used (prune candidates)
usage.jsonl: one {"skill": "name", "at": "2026-10-01T12:00:00Z"} per use, from your gateway or agent logs.
Pattern checks are a floor, not a guarantee: a human still reviews every new skill, and your secret scanner (Day 14) and OPA policies (Day 15) run as well."""
import argparse
import datetime as dt
import json
import os
import re
import sys

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SECRETS = [re.compile(p) for p in (r"sk-[A-Za-z0-9_-]{16,}", r"AKIA[0-9A-Z]{12,}", r"ghp_[A-Za-z0-9]{20,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----")]
RISKY = [(re.compile(r"curl[^\n|]*\|\s*(ba)?sh", re.I), "pipes a download into a shell"),
         (re.compile(r"ignore (all )?(previous|prior) instructions", re.I), "prompt-injection phrase"),
         (re.compile(r"do not (tell|inform) the user", re.I), "asks the agent to hide actions from the user"),
         (re.compile(r"chmod\s+777|rm\s+-rf\s+/(\s|$)", re.I), "dangerous command")]
MAX_BYTES = 20_000


def front(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def lint(path):
    text = open(path, encoding="utf-8").read()
    errs, warns = [], []
    fm = front(text)
    if fm is None:
        return ["no front matter"], warns, None
    name = fm.get("name", "")
    if not NAME.match(name):
        errs.append(f"name '{name}' must be lowercase-with-hyphens")
    if name and os.path.basename(os.path.dirname(path)) != name:
        errs.append(f"name '{name}' does not match its folder '{os.path.basename(os.path.dirname(path))}'")
    desc = fm.get("description", "")
    if len(desc) < 40:
        errs.append("description under 40 characters: the agent picks skills by description, so say what it does and WHEN to use it")
    elif "use when" not in desc.lower():
        warns.append("description has no 'Use when ...' trigger")
    for k in ("owner", "version"):
        if not fm.get(k):
            warns.append(f"no '{k}' in front matter (needed for curation and pruning)")
    if len(text.encode()) > MAX_BYTES:
        errs.append(f"SKILL.md is over {MAX_BYTES} bytes: split it, load detail on demand")
    for rx in SECRETS:
        if rx.search(text):
            errs.append("looks like it contains a secret")
            break
    for rx, why in RISKY:
        if rx.search(text):
            errs.append(why)
    return errs, warns, name


def stale(usage_path, names, days, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    last = {}
    for line in open(usage_path):
        r = json.loads(line)
        t = dt.datetime.fromisoformat(r["at"].replace("Z", "+00:00"))
        last[r["skill"]] = max(last.get(r["skill"], t), t)
    return sorted(n for n in names if n not in last or (now - last[n]).days > days)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--usage")
    ap.add_argument("--stale-days", type=int, default=90)
    a = ap.parse_args(argv)
    rc, names, seen = 0, [], {}
    for d, _, files in sorted(os.walk(a.root)):
        if "SKILL.md" in files:
            p = os.path.join(d, "SKILL.md")
            errs, warns, name = lint(p)
            if name:
                if name in seen:
                    errs.append(f"duplicate skill name (also {seen[name]})")
                seen[name] = p
                names.append(name)
            for e in errs:
                print(f"{p}: ERROR {e}")
            for w in warns:
                print(f"{p}: warn  {w}")
            if not errs:
                print(f"{p}: ok")
            rc |= bool(errs)
    if a.usage:
        for n in stale(a.usage, names, a.stale_days):
            print(f"prune candidate: {n} (unused for {a.stale_days}+ days)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
