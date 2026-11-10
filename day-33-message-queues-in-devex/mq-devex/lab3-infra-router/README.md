# Lab 3: the infra request router

```
platform request k8s-namespace-rds ...  --publishes-->  infra.request.<kind>
router.py (routes.yaml)  -->  infra.work.terraform   -> terraform_runner.py (STAND-IN) -> infra.result.<id>
                         -->  infra.human.<team>     -> human_desk.py (ticket)  <- platform request approve|complete -> infra.approval|completion.<id>
                         -->  infra.status.<id>      every state change; `platform request status <id>` reads these
```

## Run

```bash
export PYTHONPATH=../lib NATS_URL=nats://127.0.0.1:4222 STATE_DIR=.state
python3 router.py & python3 terraform_runner.py & python3 human_desk.py &

cd ../../../day-10-local-platform/platform                       # day-10-local-platform/platform
./platform request kinds
./platform request k8s-namespace-rds --name orders --owner alice --env dev --wait          # automation path: routed -> done
./platform request k8s-namespace-rds --name orders --owner alice --env prod --id req-1 --wait   # human path: waiting-on-human
./platform request approve req-1 --by bob          # the desk starts the automation named in `then`
./platform request status req-1
./platform request aws-account --name sandbox-7 --owner carol --id req-2
./platform request complete req-2 --by dana        # a human did it by hand
./platform request teleporter --name x --owner a --wait    # no route: rejected, with the next step in the message
```

`./platform` needs `python3` with `nats-py` and `pyyaml` importable (activate your venv first). On Windows use Git Bash or WSL, as for the rest of `./platform`.

Change `routes.yaml`, restart `router.py`, and the routing changes: that is the point. `router.decide()` is a pure function with table tests in `tests/test_infra_router.py`.

## What is real and what is not

- The routing, status events, approval flow, idempotent resubmission (`--id`) and the CLI are real and tested against a real NATS server.
- `terraform_runner.py` does NOT run Terraform. `fake_apply` invents outputs. To make it real, run Terraform in a Kubernetes Job (the capstone's `JobRunner` seam) with a per-request workspace, and publish its outputs.
- `human_desk.py` writes tickets to a JSONL file. With `FORGEJO_URL`, `FORGEJO_TOKEN`, `FORGEJO_REPO` it also calls Forgejo's create-issue endpoint; that path was not run (no Forgejo here). Swap in a Slack webhook the same way.
