"""A stand-in for ImproveRepoWorkflow with the same name, so the fleet workflow can be tested without running a whole repo loop.
Lives in its own module because the Temporal sandbox re-imports the module that defines a workflow, and test modules do things (Path.resolve) it forbids."""
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from flow_models import RepoInput, RepoSummary


@workflow.defn(name="ImproveRepoWorkflow")
class StubRepo:
    @workflow.run
    async def run(self, inp: RepoInput) -> RepoSummary:
        await workflow.sleep(timedelta(minutes=5))
        return RepoSummary(inp.repo, "target-reached", 0.0, 70.0, 1.5)
