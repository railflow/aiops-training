"""Line coverage with the standard library only, so the lab runs anywhere with Python 3.10 or newer.

Runs the unittest suite under `tests/` with `src/` on the path, traces which lines of `src/` run, and writes
`coverage.json` plus a one-line summary. It is a teaching tool: use coverage.py for real work.
"""
import dis
import json
import os
import sys
import unittest


def executable_lines(path: str) -> set:
    with open(path, encoding="utf-8") as f:
        code = compile(f.read(), path, "exec")
    lines, stack = set(), [code]
    while stack:
        c = stack.pop()
        lines.update(line for _, line in dis.findlinestarts(c) if line)
        stack.extend(k for k in c.co_consts if hasattr(k, "co_code"))
    return lines


def main() -> int:
    root = os.getcwd()
    src = os.path.join(root, "src")
    sys.path.insert(0, src)
    wanted = {}
    for dirpath, _, names in os.walk(src):
        for n in names:
            if n.endswith(".py") and n != "__init__.py":
                p = os.path.join(dirpath, n)
                wanted[os.path.realpath(p)] = executable_lines(p)
    hit = {p: set() for p in wanted}

    def tracer(frame, event, arg):
        p = os.path.realpath(frame.f_code.co_filename)
        if p in hit:
            if event == "line":
                hit[p].add(frame.f_lineno)
            return tracer
        return None

    sys.settrace(tracer)
    tests_dir = os.path.join(root, "tests")
    suite = unittest.defaultTestLoader.discover(tests_dir, top_level_dir=tests_dir)
    result = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
    sys.settrace(None)
    total = sum(len(v) for v in wanted.values())
    covered = sum(len(hit[p] & wanted[p]) for p in wanted)
    percent = round(100.0 * covered / total, 1) if total else 0.0
    files = {os.path.relpath(p, root): round(100.0 * len(hit[p] & wanted[p]) / len(wanted[p]), 1) for p in wanted}
    with open("coverage.json", "w", encoding="utf-8") as f:
        json.dump({"percent": percent, "tests_run": result.testsRun, "failures": len(result.failures) + len(result.errors), "files": files}, f)
    print(f"tests={result.testsRun} failures={len(result.failures) + len(result.errors)} coverage={percent}%")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
