#!/usr/bin/env python3
"""Work out who is on call this week from schedule.json and (optionally) write it into the Keep workflows.

Usage:
  python3 rotate.py                    show primary and secondary for today
  python3 rotate.py --date 2026-11-10  show them for another date
  python3 rotate.py --apply            rewrite the consts in keep/workflows/20-* and 30-*, then print the commands to load them

Rotation rule: weeks since `start`, modulo the number of people. Primary is people[n], secondary is people[n+1].
Overrides replace both for their date range. This is a stand-in for a real on-call tool (PagerDuty, Grafana OnCall, ...).
"""
import argparse
import datetime as dt
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOWS = HERE.parent / "keep" / "workflows"


def who(schedule, day):
    for o in schedule.get("overrides", []):
        if dt.date.fromisoformat(o["from"]) <= day <= dt.date.fromisoformat(o["to"]):
            return o["primary"], o["secondary"], o.get("reason", "override")
    start = dt.date.fromisoformat(schedule["start"])
    people = schedule["people"]
    n = ((day - start).days // 7) % len(people)
    return people[n]["email"], people[(n + 1) % len(people)]["email"], "rotation"


def set_const(path, key, value):
    text = path.read_text()
    new = re.sub(rf'({key}: )"[^"]*"', rf'\g<1>"{value}"', text)
    if new != text:
        path.write_text(new)
        return True
    return False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", default=dt.date.today().isoformat())
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    schedule = json.loads((HERE / "schedule.json").read_text())
    day = dt.date.fromisoformat(a.date)
    primary, secondary, why = who(schedule, day)
    print(f"{day}: primary={primary} secondary={secondary} ({why})")
    if a.apply:
        changed = False
        changed |= set_const(WORKFLOWS / "20-notify-critical.yaml", "primary", primary)
        changed |= set_const(WORKFLOWS / "20-notify-critical.yaml", "secondary", secondary)
        changed |= set_const(WORKFLOWS / "30-escalate-unacknowledged.yaml", "secondary", secondary)
        print("workflow files updated" if changed else "workflow files already current")
        print("Now load them:\n  kubectl apply -k day-20-alerting-with-keep/alerting/keep\n  kubectl -n keep rollout restart deploy/keep-backend")


if __name__ == "__main__":
    main()
