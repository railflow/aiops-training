"""The tools the model gets, as plain functions. Both engines use exactly these, so the comparison is fair.

Nothing here knows about a framework. `repo_dir` is always the first argument; the engines bind it.
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_TEST_BYTES = 20_000
MAX_READ_LINES = 200
MAX_UNCOVERED = 12
TEST_PATH = re.compile(r"^tests/test_[a-z0-9_]+\.py$")
FORBIDDEN = re.compile(r"\b(subprocess|socket|requests|urllib|os\.system|shutil\.rmtree|eval|exec)\b")


class ToolError(Exception):
    """A problem the model can read and react to (bad path, bad syntax). Not a crash."""


def _inside(repo: Path, rel: str) -> Path:
    p = (repo / rel).resolve()
    if p != repo.resolve() and repo.resolve() not in p.parents:
        raise ToolError("path escapes the repository")
    return p


def _package(repo: Path) -> str:
    for d in sorted(repo.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.name != "tests":
            return d.name
    raise ToolError("no python package found")


def _functions(path: Path):
    tree = ast.parse(path.read_text())
    src = path.read_text().splitlines()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            yield node.name, node.lineno, node.end_lineno, src[node.lineno - 1:node.end_lineno]


def _pytest(repo: Path, timeout_s: int):
    cov_json = tempfile.mktemp(suffix=".json")
    env = dict(os.environ, COVERAGE_FILE=tempfile.mktemp(suffix=".cov"), PYTHONDONTWRITEBYTECODE="1")
    cmd = [sys.executable, "-m", "pytest", "-q", "-rf", "-p", "no:cacheprovider", f"--cov={_package(repo)}", f"--cov-report=json:{cov_json}"]
    try:
        out = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        raise ToolError(f"pytest timed out after {timeout_s}s")
    return out.stdout + out.stderr, cov_json


def run_tests(repo_dir: str, timeout_s: int = 120) -> dict:
    """Run the repository's tests with coverage. Returns the total coverage percent, failures, and the least-covered functions (at most 12, sources truncated)."""
    repo = Path(repo_dir)
    text, cov_json = _pytest(repo, timeout_s)
    failures = re.findall(r"^FAILED (\S+)", text, re.M)
    if failures:  # one re-run filters out flaky tests; a test that fails twice is a real failure
        text, cov_json = _pytest(repo, timeout_s)
        failures = re.findall(r"^FAILED (\S+)", text, re.M)
    try:
        cov = json.loads(Path(cov_json).read_text())
    except (OSError, ValueError):
        raise ToolError("coverage report missing; the tests probably failed to import:\n" + "\n".join(text.splitlines()[-12:]))
    passed = int((re.search(r"(\d+) passed", text) or [0, 0])[1])
    uncovered = []
    for rel, data in cov["files"].items():
        missing = set(data["missing_lines"])
        for name, start, end, lines in _functions(repo / rel):
            n = len(missing & set(range(start, end + 1)))
            if n:
                uncovered.append({"file": rel, "name": name, "line": start, "missing": n, "source": "\n".join(lines[:12])})
    uncovered.sort(key=lambda u: (-u["missing"], u["file"], u["name"]))
    return {"coverage": round(cov["totals"]["percent_covered"], 1), "passed": passed, "failed": len(failures), "failures": failures,
            "uncovered": uncovered[:MAX_UNCOVERED], "uncovered_total": len(uncovered), "tail": "\n".join(text.splitlines()[-8:]) if failures else ""}


def read_file(repo_dir: str, path: str) -> dict:
    """Read a text file from the repository (first 200 lines)."""
    p = _inside(Path(repo_dir), path)
    if not p.is_file():
        raise ToolError(f"{path} is not a file")
    lines = p.read_text().splitlines()
    return {"path": path, "lines": len(lines), "text": "\n".join(lines[:MAX_READ_LINES])}


def write_test_file(repo_dir: str, path: str, content: str, covers: list[str]) -> dict:
    """Create or replace a test file under tests/. `covers` lists the function names the tests target."""
    if not TEST_PATH.match(path):
        raise ToolError("tests must be written to tests/test_<name>.py")
    if len(content.encode()) > MAX_TEST_BYTES:
        raise ToolError(f"test file larger than {MAX_TEST_BYTES} bytes")
    if FORBIDDEN.search(content):
        raise ToolError("tests may not use subprocess, sockets, the network, eval or exec")
    try:
        ast.parse(content)
    except SyntaxError as e:
        raise ToolError(f"syntax error: {e}")
    p = _inside(Path(repo_dir), path)
    p.write_text(content)
    return {"written": path, "bytes": len(content), "tests": len(re.findall(r"^def test_", content, re.M)), "covers": covers}


def _git(repo: str, *args: str) -> str:
    out = subprocess.run(["git", "-c", "user.name=coverage-agent", "-c", "user.email=agent@example.invalid", *args], cwd=repo, capture_output=True, text=True)
    if out.returncode:
        raise ToolError(out.stderr.strip() or "git failed")
    return out.stdout.strip()


def git_commit(repo_dir: str, branch: str, message: str) -> dict:
    """Commit the new test files on a branch. Never touches main."""
    if not re.match(r"^agent/[a-z0-9-]+$", branch):
        raise ToolError("branch must look like agent/<name>")
    _git(repo_dir, "checkout", "-q", "-B", branch)
    _git(repo_dir, "add", "tests")
    if not _git(repo_dir, "status", "--porcelain", "tests"):
        raise ToolError("nothing to commit")
    _git(repo_dir, "commit", "-q", "-m", message)
    return {"branch": branch, "sha": _git(repo_dir, "rev-parse", "--short", "HEAD")}


class FileForge:
    """A stand-in for Forgejo's pull-request API: one JSON file per open PR. Replace with real API calls (Day 10) in production."""

    def __init__(self, root: str):
        self.root = Path(root)

    def find_open_pr(self, repo: str, branch: str):
        p = self.root / f"{repo}.json"
        if p.exists() and json.loads(p.read_text())["branch"] == branch:
            return json.loads(p.read_text())
        return None

    def create_pr(self, repo: str, branch: str, title: str, body: str) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        pr = {"repo": repo, "branch": branch, "title": title, "body": body, "url": f"forge.invalid/{repo}/pulls/1"}
        (self.root / f"{repo}.json").write_text(json.dumps(pr))
        return pr


def open_pr(repo_dir: str, branch: str, title: str, body: str) -> dict:
    """Open a pull request for the branch (reuses an existing open PR for the same branch)."""
    forge = FileForge(os.environ.get("FORGE_DIR", "/tmp/forge"))
    repo = Path(repo_dir).name
    # >> C14 PR and branch dedup
    existing = forge.find_open_pr(repo, branch)
    if existing:
        return {"url": existing["url"], "deduplicated": True}
    return {"url": forge.create_pr(repo, branch, title, body)["url"], "deduplicated": False}
    # << C14
