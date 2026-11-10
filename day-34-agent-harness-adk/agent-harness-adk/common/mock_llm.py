"""A deterministic stand-in for a model. It is NOT a model.

`decide()` is a rule-based policy over the message history. It exists so the whole lab runs offline, for free, and repeatably,
and so tests can inject the failures real models cause. The harness code around it is real; the "intelligence" is a script.

History messages (the same shape both engines use):
  {"role": "user", "text": str}
  {"role": "assistant", "text": str | None, "calls": [{"name": str, "args": dict}]}
  {"role": "tool", "name": str, "result": dict}
"""
import ast
import json
import re
from dataclasses import dataclass, field

BATCH = 6
PRICE_PER_1K_TOKENS = 0.002  # made-up price: only the arithmetic matters


@dataclass
class Call:
    name: str
    args: dict
    id: str = ""


@dataclass
class Reply:
    text: str | None = None
    calls: list = field(default_factory=list)
    error: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def cost(self) -> float:
        return (self.prompt_tokens + self.completion_tokens) / 1000 * PRICE_PER_1K_TOKENS


def estimate_tokens(obj) -> int:
    return len(json.dumps(obj, default=str)) // 4


def _sample(param: str) -> str:
    if "items" in param:
        return "[1, 2, 3]"
    if any(k in param for k in ("page", "size", "count", "limit", "offset")):
        return "1"
    if any(k in param for k in ("time", "date", "stamp")):
        return repr("2020-01-01T00:00:00")
    return repr("abc")


def _test_for(entry: dict) -> str:
    mod, fn, src = entry["file"][:-3].replace("/", "."), entry["name"], entry["source"]
    head = f"def test_{fn}():\n    m = importlib.import_module({mod!r})\n"
    if "is None" in src and "raise ValueError" in src:
        body = f"    assert m.{fn}(' x ') == 'x'\n    with pytest.raises(ValueError):\n        m.{fn}(None)\n"
        too_long = re.search(r"len\(text\) > (\d+)", src)
        if too_long:
            body += f"    with pytest.raises(ValueError):\n        m.{fn}('x' * {int(too_long.group(1)) + 1})\n"
        return head + body
    params = [a.arg for a in ast.parse(src).body[0].args.args]
    return head + f"    try:\n        m.{fn}({', '.join(_sample(p) for p in params)})\n    except Exception:\n        pass\n"


def build_test_file(entries: list[dict], wrong: bool = False) -> str:
    out = ["import importlib", "", "import pytest", ""]
    for e in entries:
        out += ["", _test_for(e)]
    if wrong:
        out += ["", "def test_wrong_expectation():\n    assert 1 == 2\n"]
    return "\n".join(out) + "\n"


def drop_tests(content: str, names: list[str]) -> str:
    blocks = re.split(r"\n(?=def test_)", content)
    return "\n".join(b for b in blocks if not any(b.startswith(f"def {n}(") for n in names)).rstrip() + "\n"


def _pairs(history):
    """(call, result) for every tool call that has a result."""
    out, pending = [], None
    for m in history:
        if m["role"] == "assistant" and m.get("calls"):
            pending = m["calls"][0]
        elif m["role"] == "tool" and pending is not None:
            out.append((pending, m["result"]))
            pending = None
    return out


def _task(history):
    text = " ".join(m.get("text") or "" for m in history[:2])
    repo = re.search(r"repo=([\w.-]+)", text)
    return repo.group(1) if repo else "repo"


def _reply(history, text=None, name=None, **args):
    calls = [Call(name, args, id=f"call-{len(history)}")] if name else []
    return Reply(text=text, calls=calls, prompt_tokens=estimate_tokens(history), completion_tokens=estimate_tokens([text, args]))


def decide(role: str, history: list[dict], target: float, faults: frozenset = frozenset()) -> Reply:
    """role is one of: all (one loop does everything), analyze, improve, publish."""
    pairs = _pairs(history)
    repo = _task(history)
    ok = [(c, r) for c, r in pairs if "error" not in r]
    runs = [r for c, r in ok if c["name"] == "run_tests"]
    cur = runs[-1] if runs else None
    writes = [(c, r) for c, r in ok if c["name"] == "write_test_file"]
    attempted = {n for c, _ in writes for n in c["args"].get("covers", [])}
    last = history[-1]
    no_calls_yet = not any(m["role"] == "assistant" and m.get("calls") for m in history)

    if "malformed_json" in faults and not any("not valid JSON" in (m.get("text") or "") for m in history) and no_calls_yet:
        return Reply(error="tool call arguments are not valid JSON", prompt_tokens=estimate_tokens(history))
    if "bad_tool" in faults and no_calls_yet:
        return _reply(history, name="run_test")  # a typo in the tool name
    if role == "publish":
        done = {c["name"] for c, _ in ok}
        if "git_commit" not in done:
            return _reply(history, name="git_commit", branch=f"agent/coverage-{repo}", message=f"Add generated tests for {repo}")
        if "open_pr" not in done:
            return _reply(history, name="open_pr", branch=f"agent/coverage-{repo}", title=f"Raise test coverage of {repo}", body="Tests written by the coverage agent.")
        return _reply(history, text="pull request opened")
    if cur is None:
        return _reply(history, name="run_tests")
    if role == "analyze":
        return _reply(history, text=f"baseline coverage {cur['coverage']}%, {cur['uncovered_total']} uncovered functions")

    write_idx = [i for i, m in enumerate(history) if m["role"] == "assistant" and any(c["name"] == "write_test_file" for c in m.get("calls", []))]
    text_after_write = bool(write_idx) and any(m["role"] == "assistant" and m.get("text") for m in history[write_idx[-1]:])
    verifying = bool(write_idx) and last["role"] == "tool" and last["name"] == "run_tests" and not text_after_write
    if last["role"] == "tool" and last["name"] == "write_test_file" and "error" not in last["result"]:
        return _reply(history, name="run_tests")
    generated_failures = [f for f in cur["failures"] if "tests/test_gen_" in f]
    if last["role"] == "tool" and last["name"] == "run_tests" and generated_failures:
        path = generated_failures[0].split("::")[0]
        prev = [c for c, _ in writes if c["args"]["path"] == path][-1]
        names = [f.split("::")[1] for f in generated_failures if f.startswith(path)]
        return _reply(history, name="write_test_file", path=path, content=drop_tests(prev["args"]["content"], names), covers=prev["args"]["covers"])
    if role == "improve" and verifying:
        return _reply(history, text=f"iteration complete: coverage {cur['coverage']}%")
    if cur["coverage"] >= target:
        if role == "improve":
            return _reply(history, text=f"target reached: coverage {cur['coverage']}%")
        done = {c["name"] for c, _ in ok}
        if "git_commit" not in done:
            return _reply(history, name="git_commit", branch=f"agent/coverage-{repo}", message=f"Add generated tests for {repo}")
        if "open_pr" not in done:
            return _reply(history, name="open_pr", branch=f"agent/coverage-{repo}", title=f"Raise test coverage of {repo}", body="Tests written by the coverage agent.")
        return _reply(history, text=f"done: coverage {cur['coverage']}%")
    if "stuck" in faults and writes:
        c = writes[-1][0]
        return _reply(history, name="write_test_file", **c["args"])
    batch = [u for u in cur["uncovered"] if u["name"] not in attempted][:BATCH]
    if not batch:
        return _reply(history, text=f"stuck: no uncovered function left to try, coverage {cur['coverage']}%")
    n = len(writes) + 1
    args = {"path": f"tests/test_gen_{n}.py", "content": build_test_file(batch, wrong="bad_test" in faults and n == 1), "covers": [u["name"] for u in batch]}
    if "malformed_args" in faults and not write_idx:
        args.pop("content")
    return _reply(history, name="write_test_file", **args)
