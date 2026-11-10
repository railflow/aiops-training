---
title: "Day 6: Namespaces, Services, and NetworkPolicy"
description: "Files in day-06-networking-and-network-policy/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 6: Namespaces, Services, and NetworkPolicy"
  order: 6
---

This page is the file-by-file guide to [`day-06-networking-and-network-policy/`](https://github.com/railflow/aiops-training/tree/main/day-06-networking-and-network-policy) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Turn the hello apps into REST APIs, call one pod from another through Services and DNS, then allow and deny traffic with NetworkPolicy on a Calico-enabled kind cluster.

Homework for this day is in [`day-06-networking-and-network-policy/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-06-networking-and-network-policy/homework.md) and is repeated at the bottom of this page.

## What is in the folder

6 files. Paths below are relative to the repo root unless noted.

### day-06-networking-and-network-policy/net/

| File | What it is | How the lesson uses it |
|---|---|---|
| `net/00-namespaces.yaml` | Kubernetes manifest defining Namespace `frontend`, Namespace `backend`, Namespace `intruder`. | `kubectl apply -f day-06-networking-and-network-policy/net/00-namespaces.yaml` |
| `net/java-api.yaml` | The "backend": the Java REST API in namespace backend, reachable inside the cluster as java-api.backend. Defines: Deployment `java-api`, Service `java-api`. | `kubectl apply -f day-06-networking-and-network-policy/net/java-api.yaml -f day-06-networking-and-network-policy/net/python-api.yaml` |
| `net/netpol-allow-python-to-java.yaml` | Re-open exactly one path: pods labelled app=python-api in namespace frontend may reach the Java API on 8080. Defines: NetworkPolicy `allow-python-api-to-java-api`. | `cat day-06-networking-and-network-policy/net/netpol-allow-python-to-java.yaml` |
| `net/netpol-default-deny-backend.yaml` | Select every pod in namespace backend and allow NO ingress. (Needs a CNI that enforces NetworkPolicy.) Defines: NetworkPolicy `default-deny-ingress`. | `kubectl apply -f day-06-networking-and-network-policy/net/netpol-default-deny-backend.yaml` |
| `net/netshoot.yaml` | A toolbox pod with curl, dig, tcpdump, and more. Created in the namespace you choose: kubectl apply -n frontend -f netshoot.yaml kubectl apply -n intruder -f netshoot.yaml Defines: Pod `netshoot`. | `kubectl apply -n frontend -f day-06-networking-and-network-policy/net/netshoot.yaml` |
| `net/python-api.yaml` | The "frontend": the Python REST API in namespace frontend. /relay calls the Java API. Also exposed on NodePort 30090, which kind-config.yaml maps to http://localhost:30090 on your laptop. Defines: Deployment `python-api`, Service `python-api`. | `kubectl apply -f day-06-networking-and-network-policy/net/java-api.yaml -f day-06-networking-and-network-policy/net/python-api.yaml` |

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/` (`python-hello/`).

From [Day 3](/days/day-03-kind-kubernetes/): `day-03-kind-kubernetes/` (`k8s/`).

From [Day 4](/days/day-04-data-services-and-appwrite/): `day-04-data-services-and-appwrite/` (`java-app/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
cd ~/aiops-training
docker build -f day-02-docker-basics/python-hello/Dockerfile.app -t hello-py-app:1.1 day-02-docker-basics/python-hello
docker build -t hello-java-app:1.1 day-04-data-services-and-appwrite/java-app
docker images | grep -E "REPOSITORY|hello-(py|java)-app"
```

```bash
cd ~/aiops-training
./tools/kind destroy
export SHARED_DIR="$HOME/kind-shared"; mkdir -p "$SHARED_DIR"      # Git Bash: SHARED_DIR="$(cygpath -m "$HOME")/kind-shared"
sed "s|__SHARED_DIR__|$SHARED_DIR|" day-03-kind-kubernetes/k8s/kind-config-calico.yaml > day-03-kind-kubernetes/k8s/kind-config.local.yaml
kind create cluster --config day-03-kind-kubernetes/k8s/kind-config.local.yaml
kubectl get nodes
```

```bash
kind load docker-image hello-py-app:1.1 hello-java-app:1.1 --name ai-ops-training
kubectl apply -f day-06-networking-and-network-policy/net/00-namespaces.yaml
kubectl apply -f day-06-networking-and-network-policy/net/java-api.yaml -f day-06-networking-and-network-policy/net/python-api.yaml
kubectl -n backend rollout status deploy/java-api
kubectl -n frontend rollout status deploy/python-api
kubectl get pods,svc -n backend
kubectl get pods,svc -n frontend
curl -s localhost:30090/hello?name=Ada
curl -s localhost:30090/relay
```

```bash
kubectl apply -n frontend -f day-06-networking-and-network-policy/net/netshoot.yaml
kubectl -n frontend wait --for=condition=Ready pod/netshoot --timeout=120s
kubectl -n frontend exec netshoot -- nslookup java-api.backend
kubectl -n frontend exec netshoot -- curl -s http://java-api.backend/hello
```

```bash
kubectl apply -n intruder -f day-06-networking-and-network-policy/net/netshoot.yaml
kubectl -n intruder wait --for=condition=Ready pod/netshoot --timeout=120s
kubectl -n intruder exec netshoot -- curl -s -m 3 -o /dev/null -w "%{http_code}\n" http://java-api.backend/hello
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
REPOSITORY       TAG   IMAGE ID       CREATED         SIZE
hello-py-app     1.1   xxxxxxxxxxxx   10 seconds ago  ~170MB
hello-java-app   1.1   xxxxxxxxxxxx   1 minute ago    ~290MB
```

```text
Creating cluster "ai-ops-training" ...
 ✓ Preparing nodes 📦
 ✓ Starting control-plane 🕹️
NAME                         STATUS     ROLES           AGE   VERSION
ai-ops-training-control-plane   NotReady   control-plane   40s   v1.32.x
```

## How these files relate to other days and shared tools

- Builds on [Day 3](/days/day-03-kind-kubernetes/), [Day 4](/days/day-04-data-services-and-appwrite/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).
- The lesson also uses files from [Day 3](/days/day-03-kind-kubernetes/).
- The lesson also uses files from [Day 4](/days/day-04-data-services-and-appwrite/).
- Files from this folder are used by [Day 7](/days/day-07-traefik-ingress/), [Day 24](/days/day-24-container-patching/).

## Homework

Work in `~/heyjob-labs/day06/`. Commit after each exercise.

### Exercise 1: A call that works, is blocked, and is re-allowed

**Do:** record the three states in `netpol.md` with the exact commands and output: (1) intruder call returns 200; (2) after default-deny returns `000`; (3) after the allow policy, `/relay` works and intruder is still blocked.

### Exercise 2: Lock down egress too

**Do:** write `netpol-egress-frontend.yaml`: a policy in `frontend` that selects `app=python-api`, allows egress only to `backend` pods on TCP 8080 **and DNS** (UDP/TCP 53 to `kube-system`), and test that `/relay` still works but `curl https://example.com` from the python pod fails.

**Deliverable:** the YAML plus before/after output.

### Exercise 3: Prove it from the packet level

**Do:** with `tcpdump` in an ephemeral container on the Java pod, capture a successful call and a blocked call (the blocked packets never arrive at the pod). Save 10-15 lines of each in `traffic.md` and explain the difference.

### Exercise 4: Names and endpoints

**Do:** list the three DNS name forms for `java-api`, and show with `nslookup` and `curl` that each works from the correct namespaces (and which fail from another namespace). Scale `java-api` to 3 replicas and show the Service endpoints list three IPs and that repeated `/relay` calls hit different pods.
