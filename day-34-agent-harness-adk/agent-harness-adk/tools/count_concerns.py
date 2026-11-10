"""Count the lines of code each concern costs, per owner, from the `# >> Cnn name` / `# << Cnn` markers in the source.

Blank lines, comments and docstring-only lines are not counted. Regions can nest: the innermost region owns a line.
`# >> LAB` marks code that only exists so the lab runs offline (the mock model); it is left out of the totals.
Code outside every region is the loop itself and its plumbing; it is reported as "everything else".
Columns: hand_rolled/ (the loop you write), adk/ (what you still write with ADK), shared (common/ and fanout/: identical for both engines or the orchestrator).
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OWNERS = {"hand_rolled": "hand_rolled", "adk": "adk", "common": "shared", "fanout": "shared"}
OPEN, CLOSE = re.compile(r"^\s*# >> (C\d\d|LAB) (.+)$"), re.compile(r"^\s*# << (C\d\d|LAB)\s*$")


def code_lines(text: str):
    """Yield (lineno, line) for lines that are code: no blanks, comments or docstring bodies."""
    in_doc = False
    for n, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if in_doc:
            in_doc = '"""' not in s
            continue
        if s.startswith('"""'):
            in_doc = s.count('"""') == 1
            continue
        yield n, raw, s


def count(root: Path = ROOT) -> dict:
    names: dict[str, str] = {}
    table: dict[str, dict[str, int]] = defaultdict(lambda: {"hand_rolled": 0, "adk": 0, "shared": 0})
    rest = {"hand_rolled": 0, "adk": 0, "shared": 0}
    for pkg, owner in OWNERS.items():
        for path in sorted((root / pkg).rglob("*.py")):
            if "skeletons" in path.parts or "coverage_agent" in path.parts or path.name == "parallel_batch.py":
                continue
            stack: list[str] = []
            for n, raw, s in code_lines(path.read_text()):
                if m := OPEN.match(raw):
                    stack.append(m.group(1))
                    names[m.group(1)] = m.group(2)
                elif m := CLOSE.match(raw):
                    if not stack or stack[-1] != m.group(1):
                        raise ValueError(f"{path}:{n}: unbalanced marker {m.group(1)}")
                    stack.pop()
                elif s and not s.startswith("#"):
                    if stack and stack[-1] != "LAB":
                        table[stack[-1]][owner] += 1
                    elif not stack and pkg != "common":
                        rest[owner] += 1
            if stack:
                raise ValueError(f"{path}: region {stack[-1]} never closed")
    return {"names": names, "lines": {k: dict(v) for k, v in sorted(table.items())}, "everything_else": rest}


def markdown(result: dict) -> str:
    rows = ["| # | Concern | Hand-rolled agent | ADK agent | Shared / orchestrator |", "|---|---|---:|---:|---:|"]
    totals = {"hand_rolled": 0, "adk": 0, "shared": 0}
    for cid, v in result["lines"].items():
        rows.append(f"| {cid} | {result['names'][cid]} | {v['hand_rolled']} | {v['adk']} | {v['shared']} |")
        for k in totals:
            totals[k] += v[k]
    rest = result["everything_else"]
    rows.append(f"| | Everything else (the loop, plumbing, entry point) | {rest['hand_rolled']} | {rest['adk']} | {rest['shared']} |")
    for k in totals:
        totals[k] += rest[k]
    rows.append(f"| | **Total** | **{totals['hand_rolled']}** | **{totals['adk']}** | **{totals['shared']}** |")
    return "\n".join(rows)


if __name__ == "__main__":
    res = count()
    print(json.dumps(res, indent=2) if "--json" in sys.argv else markdown(res))
