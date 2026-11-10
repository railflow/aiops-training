"""The first version everyone writes: ask the model, run the tool it names, feed the result back, repeat until it stops asking.

It works on a good day. Day 34 walks through what each bad day does to it (tests/test_naive_loop.py runs those days).
"""
import sys

from common import faults as F
from common import repo_tools as T
from common import repos
from hand_rolled.llm import MockLLM


def naive_run(repo_dir: str, llm, repo: str, target: float = 80.0) -> str:
    tools = {
        "run_tests": lambda: T.run_tests(repo_dir),
        "write_test_file": lambda path, content, covers: T.write_test_file(repo_dir, path, content, covers),
        "git_commit": lambda branch, message: T.git_commit(repo_dir, branch, message),
        "open_pr": lambda branch, title, body: T.open_pr(repo_dir, branch, title, body),
    }
    history = [{"role": "user", "text": f"Raise test coverage of repo={repo} to {target}%."}]
    while True:
        reply = llm.complete(history, [])
        history.append({"role": "assistant", "text": reply.text, "calls": [{"name": c.name, "args": c.args} for c in reply.calls]})
        if not reply.calls:
            return reply.text
        call = reply.calls[0]
        history.append({"role": "tool", "name": call.name, "result": tools[call.name](**call.args)})


if __name__ == "__main__":
    spec = repos.make_specs(1)[0]
    chaos = sys.argv[1] if len(sys.argv) > 1 else ""
    faults = F.parse(chaos, spec["name"])
    path = repos.materialise(spec, "/tmp/naive")
    print(naive_run(path, MockLLM("all", 80.0, F.model_faults(faults), F.RateLimiter(faults)), spec["name"]))
