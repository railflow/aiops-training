#!/usr/bin/env python3
"""Lint a spec file so an agent never starts from a vague one. Exit 0 = ok, 1 = problems (printed one per line).
Usage: check_spec.py SPEC.md [SPEC.md ...]    Wire it into CI for any path under specs/ or docs/specs/."""
import re
import sys

REQUIRED_FIELDS = ["id", "title", "owner", "status", "risk"]
STATUSES = {"draft", "approved", "implemented"}
RISKS = {"low", "medium", "high"}
REQUIRED_SECTIONS = ["Problem", "Acceptance criteria", "Non-goals", "Test plan", "Rollback"]
VAGUE = re.compile(r"\b(well|fast|clean|better|good|nice|robust|appropriate|properly|user[- ]friendly|etc)\b", re.I)
AC = re.compile(r"^- \[[ xX]\] (AC-\d+):\s*(.+)$")


def parse(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return None, None, text
    front = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            front[k.strip()] = v.split("#")[0].strip()
    sections, name, buf = {}, None, []
    for line in m.group(2).splitlines():
        h = re.match(r"^##\s+(.*\S)\s*$", line)
        if h:
            if name:
                sections[name] = "\n".join(buf).strip()
            name, buf = h.group(1), []
        else:
            buf.append(line)
    if name:
        sections[name] = "\n".join(buf).strip()
    return front, sections, m.group(2)


def check(text):
    problems = []
    front, sections, _ = parse(text)
    if front is None:
        return ["missing front matter (--- block with id, title, owner, status, risk)"]
    for f in REQUIRED_FIELDS:
        if not front.get(f):
            problems.append(f"front matter: missing '{f}'")
    if front.get("status") and front["status"] not in STATUSES:
        problems.append(f"front matter: status '{front['status']}' not in {sorted(STATUSES)}")
    if front.get("risk") and front["risk"] not in RISKS:
        problems.append(f"front matter: risk '{front['risk']}' not in {sorted(RISKS)}")
    if front.get("title") and len(front["title"].split()) < 3:
        problems.append("title: too short to mean anything (3+ words)")
    for s in REQUIRED_SECTIONS:
        if not sections.get(s):
            problems.append(f"section '{s}' is missing or empty")
    acs = []
    for line in sections.get("Acceptance criteria", "").splitlines():
        m = AC.match(line.strip())
        if m:
            acs.append((m.group(1), m.group(2)))
    if not acs and sections.get("Acceptance criteria"):
        problems.append("acceptance criteria: use '- [ ] AC-1: ...' lines")
    for ac_id, body in acs:
        if VAGUE.search(body):
            problems.append(f"{ac_id}: vague word '{VAGUE.search(body).group(0)}'; say what is measured")
        if len(body.split()) < 5:
            problems.append(f"{ac_id}: too short to be checkable")
    plan = sections.get("Test plan", "")
    for ac_id, _ in acs:
        if ac_id not in plan:
            problems.append(f"test plan: no mention of {ac_id}")
    if front.get("risk") == "high" and "approved" in front.get("status", "") and "Constraints" not in sections:
        problems.append("high-risk approved spec needs a 'Constraints' section")
    return problems


def main(argv):
    bad = 0
    for path in argv:
        problems = check(open(path, encoding="utf-8").read())
        for p in problems:
            print(f"{path}: {p}")
        bad += bool(problems)
        if not problems:
            print(f"{path}: ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) if len(sys.argv) > 1 else (print(__doc__) or 2))
