# Day 1: Getting started: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day01/`. Commit after every exercise.

### Exercise 1: Get `./tools/kind start` to succeed

**Do:** run `./tools/kind start` until it succeeds and capture the plain-text output.

```bash
cd ~/aiops-training
NO_COLOR=1 ./tools/kind start 2>&1 | tee ~/heyjob-labs/day01/start-output.txt
```

**Deliverable:** `day01/start-output.txt` with four "yes" checks and the final "Cluster: ai-ops-training" line.

### Exercise 2: Run the full lifecycle

**Do:** run `stop`, `list`, `docker ps -a`, `start`, `destroy`, `list` in order, saving each output to `day01/*.txt` with `tee`, then recreate the cluster with `./tools/kind start`. Write `day01/notes.md` with three sentences: (1) after `stop`, was the cluster still listed and why; (2) after restart, was the busybox pod still there and why; (3) what does `destroy` remove that `stop` does not.

### Exercise 3: Tool tour

**Do:** with the cluster running, in k9s type `:pods`, select the busybox pod, press `d` (describe) then `Esc`, `l` for logs, quit with `:q`. Open lazydocker and look at the node container's logs and stats. Start `claude` in `~/aiops-training` and ask it to explain what the kind node container is in 5 bullets (no edits).

**Deliverable:** `day01/tools.md`: one line per tool (k9s, lazydocker, Docker Desktop, your terminal, Claude Code) on what you used it for and what you liked, plus Claude's 5 bullets and whether you agree.

### Exercise 4: Break it on purpose

**Do:** quit Docker Desktop, run `NO_COLOR=1 ./tools/kind list 2>&1 | tee ~/heyjob-labs/day01/docker-down.txt`, restart Docker Desktop, and re-run `./tools/kind list`.

**Deliverable:** `docker-down.txt` plus two lines appended to `notes.md`: which check failed and which hint applied.
