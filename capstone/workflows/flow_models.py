"""Plain dataclasses: the shapes that cross the workflow/activity boundary. Keep them small, JSON-friendly and versionable (add fields with defaults)."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RepoInput:
    repo: str                                   # "org/name"
    target_coverage: float = 60.0
    max_iterations: int = 4
    max_no_improve: int = 2                     # stop after this many iterations without gaining at least min_gain points
    min_gain: float = 1.0
    budget_usd: float = 10.0                    # per repo, across all iterations
    per_run_budget_usd: float = 3.0             # passed to the agent as its own hard cap
    require_approval: bool = False              # wait for a human_approval signal before counting an iteration as accepted
    approval_timeout_hours: int = 72
    focus: str = ""
    model: str = ""                             # empty = the CLI's default; a tier name or id YOU choose, never hardcoded here


@dataclass
class AgentSpec:
    repo: str
    run_id: str
    iteration: int
    task: str = "coverage"                      # coverage | fix-issue
    target_coverage: float = 60.0
    focus: str = ""
    issue_number: int = 0
    max_budget_usd: float = 3.0
    model: str = ""
    prompt_version: str = "v1"
    deadline_seconds: int = 1800


@dataclass
class AgentResult:
    run_id: str
    outcome: str                                # pushed | no-changes | integrity-failed | secret-in-diff | push-failed | clone-failed | job-failed | timeout
    branch: str = ""
    pr_url: str = ""
    commits: int = 0
    cost_usd: float = 0.0
    duration_s: int = 0
    model: str = ""
    prompt_version: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    tool_versions: dict = field(default_factory=dict)


@dataclass
class EvalSpec:
    repo: str
    run_id: str
    branch: str = "main"
    iteration: int = 0
    agent_run_id: str = ""
    prev_coverage: Optional[float] = None
    allow_src_changes: bool = False
    deadline_seconds: int = 1800


@dataclass
class EvalResult:
    ok: bool
    coverage: Optional[float] = None
    tests_failed: int = 0
    reasons: List[str] = field(default_factory=list)
    measurement: dict = field(default_factory=dict)


@dataclass
class IterationRecord:
    iteration: int
    outcome: str
    coverage: Optional[float]
    gain: float
    cost_usd: float
    branch: str = ""
    pr_url: str = ""
    accepted: bool = False


@dataclass
class RepoSummary:
    repo: str
    stop_reason: str
    baseline_coverage: Optional[float]
    final_coverage: Optional[float]
    total_cost_usd: float
    iterations: List[IterationRecord] = field(default_factory=list)


@dataclass
class FleetInput:
    repos: List[str]
    max_parallel: int = 3                       # LAPTOP: keep this at 1-3
    fleet_budget_usd: float = 50.0
    per_repo: RepoInput = field(default_factory=lambda: RepoInput(repo=""))


@dataclass
class FleetSummary:
    started: int
    completed: int
    failed: int
    total_cost_usd: float
    stop_reason: str
    by_repo: dict = field(default_factory=dict)
