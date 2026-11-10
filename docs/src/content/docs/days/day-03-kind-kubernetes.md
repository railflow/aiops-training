---
title: "Day 3: kind Kubernetes"
description: "Files in day-03-kind-kubernetes/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 3: kind Kubernetes"
  order: 3
---

This page is the file-by-file guide to [`day-03-kind-kubernetes/`](https://github.com/railflow/aiops-training/tree/main/day-03-kind-kubernetes) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: What Kubernetes and kind are, running Java, Python, and Go hello apps on the cluster, cluster operations, and shared volumes.

Homework for this day is in [`day-03-kind-kubernetes/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-03-kind-kubernetes/homework.md) and is repeated at the bottom of this page.

## What is in the folder

9 files. Paths below are relative to the repo root unless noted.

### day-03-kind-kubernetes/k8s/

| File | What it is | How the lesson uses it |
|---|---|---|
| `k8s/hello-go.yaml` | Kubernetes manifest defining Deployment `hello-go`. | `kubectl apply -f day-03-kind-kubernetes/k8s/hello-java.yaml -f day-03-kind-kubernetes/k8s/hello-go.yaml` |
| `k8s/hello-java.yaml` | Kubernetes manifest defining Deployment `hello-java`. | `kubectl apply -f day-03-kind-kubernetes/k8s/hello-java.yaml -f day-03-kind-kubernetes/k8s/hello-go.yaml` |
| `k8s/hello-python-oneshot.yaml` | Deliberate mistake for the lab: hello.py exits after one line, so a Deployment (which wants a process that never ends) restarts it forever: CrashLoopBackOff. Defines: Deployment `hello-oneshot`. | `kubectl apply -f day-03-kind-kubernetes/k8s/hello-python-oneshot.yaml` |
| `k8s/hello-python.yaml` | Kubernetes manifest defining Deployment `hello-py`. | `kubectl apply -f day-03-kind-kubernetes/k8s/hello-python.yaml` |
| `k8s/kind-config-calico.yaml` | Same as kind-config.yaml, but without kind's default CNI (kindnet does NOT enforce NetworkPolicy) so that Calico can be installed. |  |
| `k8s/kind-config.yaml` | Cluster config for the course. Create it with the kind CLI (see day03): sed "s\|__SHARED_DIR__\|$HOME/kind-shared\|" day-03-kind-kubernetes/k8s/kind-config.yaml &gt; /tmp/kind-config.yaml kind create cluster --config /tmp/kind-config.yaml Defines: Cluster. | `sed "s\|__SHARED_DIR__\|$SHARED_DIR\|" kind-config.yaml > kind-config.local.yaml` |
| `k8s/pvc-demo.yaml` | A PersistentVolumeClaim asks the cluster for storage. kind ships a default StorageClass ("standard", rancher local-path) that creates the volume on demand. Defines: PersistentVolumeClaim `demo-data`, Pod `pvc-writer`. | `kubectl apply -f day-03-kind-kubernetes/k8s/pvc-demo.yaml` |
| `k8s/shared-emptydir.yaml` | Two containers in ONE pod share an emptyDir volume. The pod's volume lives exactly as long as the pod. Defines: Pod `shared-emptydir`. | `kubectl apply -f day-03-kind-kubernetes/k8s/shared-emptydir.yaml` |
| `k8s/shared-hostpath.yaml` | /shared inside the kind node is the folder you mounted via extraMounts in kind-config.yaml, which is a folder on your own machine. Defines: Pod `shared-hostpath`. | `kubectl apply -f day-03-kind-kubernetes/k8s/shared-hostpath.yaml` |

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/` (`go-hello/`, `java-hello/`, `python-hello/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
export SHARED_DIR="$HOME/kind-shared"
mkdir -p "$SHARED_DIR"
cd day-03-kind-kubernetes/k8s
sed "s|__SHARED_DIR__|$SHARED_DIR|" kind-config.yaml > kind-config.local.yaml
grep hostPath kind-config.local.yaml
```

```bash
export SHARED_DIR="$(cygpath -m "$HOME")/kind-shared"
mkdir -p "$SHARED_DIR"
cd day-03-kind-kubernetes/k8s
sed "s|__SHARED_DIR__|$SHARED_DIR|" kind-config.yaml > kind-config.local.yaml
grep hostPath kind-config.local.yaml
```

```bash
cd ~/aiops-training
./tools/kind destroy
kind create cluster --config day-03-kind-kubernetes/k8s/kind-config.local.yaml
./tools/kind start
echo "hi from the host" > "$SHARED_DIR/host.txt"
docker exec ai-ops-training-control-plane cat /shared/host.txt
```

```bash
docker build -t hello-py:1.0 day-02-docker-basics/python-hello
kind load docker-image hello-py:1.0 --name ai-ops-training
kubectl apply -f day-03-kind-kubernetes/k8s/hello-python-oneshot.yaml
sleep 45
kubectl get pods
kubectl logs deploy/hello-oneshot
kubectl describe pod -l app=hello-oneshot | tail -8
kubectl delete -f day-03-kind-kubernetes/k8s/hello-python-oneshot.yaml
```

```bash
kubectl apply -f day-03-kind-kubernetes/k8s/hello-python.yaml
kubectl rollout status deploy/hello-py
kubectl logs deploy/hello-py --tail=2
kubectl scale deploy/hello-py --replicas=3
kubectl delete pod -l app=hello-py --wait=false
kubectl get pods -l app=hello-py
kubectl scale deploy/hello-py --replicas=1
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
      - hostPath: /home/you/kind-shared
Creating cluster "ai-ops-training" ...
Set kubectl context to "kind-ai-ops-training"
...
Cluster: ai-ops-training is up and running.
hi from the host
```

```text
NAME                             READY   STATUS             RESTARTS      AGE
hello-oneshot-xxxxxxxxxx-xxxxx   0/1     CrashLoopBackOff   3 (20s ago)   50s
Hello, world! from Python 3.12.x on hello-oneshot-xxxxxxxxxx-xxxxx
  Warning  BackOff  10s (x4 over 50s)  kubelet  Back-off restarting failed container hello in pod ...
```

## How these files relate to other days and shared tools

- Builds on [Day 2](/days/day-02-docker-basics/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).
- Files from this folder are used by [Day 6](/days/day-06-networking-and-network-policy/), [Day 7](/days/day-07-traefik-ingress/), [Day 8](/days/day-08-security-and-supply-chain/), [Day 13](/days/day-13-ci-at-scale-build-sh/), [Day 17](/days/day-17-observability/), [Day 23](/days/day-23-server-and-application-patching/), [Day 24](/days/day-24-container-patching/), [Day 34](/days/day-34-agent-harness-adk/).

## Homework

Work in `~/heyjob-labs/day03/`. Commit after each exercise.

### Exercise 1: Three apps, three Deployments

**Do:** run the three Deployments, then edit **your copy** of each YAML so `NAME` is your name and `LOOP_SECONDS` is `5`, and re-apply.

**Deliverable:** `day03/k8s/hello-*.yaml` and `day03/pods.txt` (`kubectl get deploy,pods -o wide` plus `kubectl logs -l app=... --tail=3` for each app).

### Exercise 2: Diagnose three failures

**Do:** on a copy of one deployment, cause each failure on purpose and record symptom, diagnosis command and key line, and fix: (1) `ImagePullBackOff` (wrong tag); (2) `CrashLoopBackOff` (one-shot program); (3) `Pending` (hint: `resources.requests.cpu: "100"`).

**Deliverable:** `day03/failures.md`, one section per failure with a one-sentence root cause.

### Exercise 3: Lifecycle and the shared folder

**Do:** prove `$SHARED_DIR` works both ways; stop/start and show PVC data survives; destroy, recreate with the config, and show PVC data is gone while `$SHARED_DIR` content remains. Fill a table: Deployment, PVC data, `$SHARED_DIR` file, `emptyDir` data against "survives stop/start?" and "survives destroy?".

### Exercise 4 (stretch): Ask Claude Code, then verify

**Do:** in `~/heyjob-labs`, ask `claude` to explain every field of `hello-python.yaml` in a table, and what happens if `imagePullPolicy` is removed (no edits). Check two claims yourself with `kubectl explain pod.spec.containers.imagePullPolicy` and one other.

**Deliverable:** `day03/claude-review.md` with the answer, the commands you used to verify, and any wrong or vague claims.
