# Runbook: emergency patch for a vulnerable dependency or base image

**Use when:** a critical advisory affects something we run (for example a remotely exploitable flaw in a library or base image), or a scanner gate fails on a deployed version.
**Do not use for:** routine updates (those arrive as Renovate pull requests and follow the normal flow).
**Owner:** platform on-call. **Last reviewed:** (set a date when you adopt this; stale runbooks mislead).

## The rule

**Never patch a running container.** No `kubectl exec ... apt upgrade`, no editing files in a pod. The pod is replaced on the next restart and your fix vanishes; worse, nobody can tell what is actually running. Fix the **source**, rebuild an **immutable image**, and redeploy through the normal pipeline, faster.

## 0. Declare it (5 minutes)

- [ ] Open an incident or ticket. Name one incident lead. Write the advisory ID and the affected package and versions.
- [ ] Decide severity from **exposure**, not the score alone: is the vulnerable code reachable, is it internet-facing, is it already being exploited? Write your reasoning down.

## 1. Find what is affected

```bash
# Who runs the package, from stored SBOMs (day-23-server-and-application-patching/patching/sbom):
python3 sbom_query.py sboms/ --name <package> --below <fixed-version>
# What is running right now (image names across the cluster):
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{range .spec.containers[*]}{.image}{" "}{end}{"\n"}{end}'
```

Record: service, namespace, current image (tag and digest), owner.

## 2. Decide: patch, mitigate, or both

- **Patch available:** bump the pin in the source repo (step 3).
- **No patch yet:** mitigate. Options: disable the feature by configuration, block the path at the ingress, tighten a NetworkPolicy, scale the exposed component to zero. Write down what you did and what removes it.

## 3. Fix the source and ship through the pipeline

1. Branch, change the pin (or base image digest), run tests locally.
2. Push. CI must: test, scan (`ci/patch-gate.sh`), build, tag with the commit, push, sign, store the SBOM.
3. Commit the new image tag to the **config repo**. Flux applies it; Flagger canaries it.
4. Do **not** skip the canary. A fast pipeline is the point; a bypassed one is a second incident.

If the pipeline itself is the problem, the break-glass path is: `kubectl set image` on the specific Deployment, **plus a git commit within the hour** that makes git match, noted on the incident.

## 4. Nodes and the operating system

If the issue is in the node OS or kernel: one node at a time.

```bash
kubectl cordon <node>
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data --timeout=5m
# patch or replace the node
kubectl uncordon <node>
```

Check `kubectl get pdb -A` first: a PodDisruptionBudget that cannot be satisfied blocks the drain (that is its job).

## 5. Verify

- [ ] New image digest is what runs: `kubectl -n <ns> get pod -l app=<app> -o jsonpath='{.items[*].status.containerStatuses[*].imageID}'`
- [ ] Scanner shows the finding gone for the **deployed digest**.
- [ ] SBOM query shows no remaining match (`sbom_query.py` exit status 0).
- [ ] Dashboards and alerts are quiet; the canary promoted.

## 6. Close out

- [ ] Timeline, root cause, time to detect and time to fix.
- [ ] What would have made this faster? (a missing SBOM, no owner, a flaky test)
- [ ] Add a regression guard: a pinned-dependency check, a policy, a Renovate rule.

> Never paste secrets, tokens or exploit payloads into the incident ticket.
