---
title: "Day 7: Traefik, one front door for your apps"
description: "Files in day-07-traefik-ingress/: what each one is for, how to run it, what to expect."
sidebar:
  label: "Day 7: Traefik, one front door for your apps"
  order: 7
---

This page is the file-by-file guide to [`day-07-traefik-ingress/`](https://github.com/railflow/aiops-training/tree/main/day-07-traefik-ingress) in the aiops-training repo. The lesson text itself is on the course site; this page only covers the files. Topic of the day: Replace a pile of port-forwards and NodePorts with one ingress controller. Route by host and path, add middlewares, split traffic 80/20, and add TLS, all on kind.

Homework for this day is in [`day-07-traefik-ingress/homework.md`](https://github.com/railflow/aiops-training/blob/main/day-07-traefik-ingress/homework.md) and is repeated at the bottom of this page.

## What is in the folder

13 files. Paths below are relative to the repo root unless noted.

### day-07-traefik-ingress/go-api/

| File | What it is | How the lesson uses it |
|---|---|---|
| `go-api/Dockerfile` | Container image recipe (base `golang:1.23`). |  |
| `go-api/go.mod` | Go module definition. |  |
| `go-api/main.go` | Go program entry point (`main`). |  |
| `go-api/main_test.go` | Automated tests for main. |  |

### day-07-traefik-ingress/traefik/

| File | What it is | How the lesson uses it |
|---|---|---|
| `traefik/apps.yaml` | Three REST apps in namespace "apps", each a plain ClusterIP Service on port 80. Defines: Namespace `apps`, Deployment, Service, Deployment and 3 more. | `kubectl apply -f day-07-traefik-ingress/traefik/apps.yaml` |
| `traefik/ingress-host.yaml` | (a1) Standard Kubernetes Ingress, host-based routing. ingressClassName selects Traefik. Defines: Ingress `hello-hosts`. | `cat day-07-traefik-ingress/traefik/ingress-host.yaml` |
| `traefik/ingress-paths.yaml` | (a2) Standard Kubernetes Ingress, path-based routing on ONE hostname. Without stripping the prefix, an app sees /py or /go as its own path: the Go app echoes any path, the Python app returns 404 for /py. Defines: Ingress `hello-paths`. | `kubectl apply -f day-07-traefik-ingress/traefik/ingress-paths.yaml` |
| `traefik/ingressroute-auth.yaml` | Protect the Java API with basic auth. Defines: IngressRoute `hello-java-secure`. | `kubectl apply -f day-07-traefik-ingress/traefik/ingressroute-auth.yaml` |
| `traefik/ingressroute-paths.yaml` | (b) The same path routing as ingress-paths.yaml, as a Traefik IngressRoute with middlewares. Apply this INSTEAD of ingress-paths.yaml (both would claim apps.localhost/py and /go). Defines: IngressRoute `hello-paths-crd`. | `cat day-07-traefik-ingress/traefik/ingressroute-paths.yaml` |
| `traefik/ingressroute-tls.yaml` | TLS with a local certificate. Create the secret first (see the lesson, mkcert section): kubectl -n apps create secret tls hello-py-tls --cert=hello-py.localhost.pem --key=hello-py.localhost-key.pem Defines: IngressRoute `hello-py-tls`, IngressRoute `hello-py-http-redirect`. | `kubectl apply -f day-07-traefik-ingress/traefik/ingressroute-tls.yaml` |
| `traefik/middlewares.yaml` | (c) Traefik Middlewares (CRDs). Reference them as &lt;namespace&gt;-&lt;name&gt;@kubernetescrd from an Ingress annotation, or as &#123;name, namespace&#125; from an IngressRoute. | `kubectl apply -f day-07-traefik-ingress/traefik/middlewares.yaml` |
| `traefik/values-kind.yaml` | Helm values for Traefik on the kind cluster ai-ops-training. Always compare with the chart you install: helm show values traefik/traefik \| less | `cat day-07-traefik-ingress/traefik/values-kind.yaml` |
| `traefik/weighted.yaml` | (d) Weighted routing between two versions of the Go app: 80% v1, 20% v2. Defines: Deployment, Deployment, Service, Service and 2 more. | `kubectl apply -f day-07-traefik-ingress/traefik/weighted.yaml` |

## Files this day uses from other folders

From [Day 2](/days/day-02-docker-basics/): `day-02-docker-basics/` (`python-hello/`).

From [Day 3](/days/day-03-kind-kubernetes/): `day-03-kind-kubernetes/` (`k8s/`).

From [Day 4](/days/day-04-data-services-and-appwrite/): `day-04-data-services-and-appwrite/` (`java-app/`).

## How to run it

Run commands from the repo root (`~/aiops-training`) unless a line starts with a `cd`. Text after `#` is what the line is expected to show.

```bash
./tools/kind destroy
# Calico variant from Day 6 (preferred): follow Day 6 step 2 with day-03-kind-kubernetes/k8s/kind-config-calico.yaml
# Plain variant:
sed "s|__SHARED_DIR__|$HOME/kind-shared|" day-03-kind-kubernetes/k8s/kind-config.yaml > day-03-kind-kubernetes/k8s/kind-config.local.yaml
kind create cluster --config day-03-kind-kubernetes/k8s/kind-config.local.yaml
```

```bash
docker build -t hello-go-api:1.0 day-07-traefik-ingress/go-api
kind load docker-image hello-py-app:1.1 hello-java-app:1.1 hello-go-api:1.0 --name ai-ops-training
kubectl apply -f day-07-traefik-ingress/traefik/apps.yaml
kubectl -n apps rollout status deploy/hello-py deploy/hello-java deploy/hello-go
kubectl -n apps get pods,svc
```

```bash
cat day-07-traefik-ingress/traefik/values-kind.yaml
```

```bash
helm install traefik traefik/traefik -n traefik --create-namespace -f day-07-traefik-ingress/traefik/values-kind.yaml
kubectl -n traefik rollout status deploy/traefik
helm list -n traefik
kubectl get pods,svc -n traefik
kubectl get crd | grep traefik
```

```bash
cat day-07-traefik-ingress/traefik/ingress-host.yaml
kubectl apply -f day-07-traefik-ingress/traefik/ingress-host.yaml
kubectl -n apps get ingress
curl -s http://hello-py.localhost:8080/hello; echo
curl -s http://hello-java.localhost:8080/hello; echo
curl -s http://hello-go.localhost:8080/hello; echo
```

## Expected output

Output shown by the lesson for the commands above (your hash, timestamps, ports and sizes will differ):

```text
NAME                              READY   STATUS    RESTARTS   AGE
pod/hello-go-xxxxxxxxxx-xxxxx     1/1     Running   0          20s
pod/hello-java-xxxxxxxxxx-xxxxx   1/1     Running   0          20s
pod/hello-py-xxxxxxxxxx-xxxxx     1/1     Running   0          20s

NAME                 TYPE        CLUSTER-IP      PORT(S)   AGE
service/hello-go     ClusterIP   10.96.x.y       80/TCP    20s
service/hello-java   ClusterIP   10.96.x.y       80/TCP    20s
service/hello-py     ClusterIP   10.96.x.y       80/TCP    20s
```

```text
deployment "traefik" successfully rolled out
NAME      NAMESPACE   REVISION   STATUS     CHART           APP VERSION
traefik   traefik     1          deployed   traefik-3x.y.z  v3.x.y

NAME                           READY   STATUS    RESTARTS   AGE
pod/traefik-xxxxxxxxxx-xxxxx   1/1     Running   0          30s

NAME              TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)
service/traefik   ClusterIP   10.96.x.y      <none>        80/TCP,443/TCP

ingressroutes.traefik.io            2026-...
middlewares.traefik.io              2026-...
traefikservices.traefik.io          2026-...
...
```

## How these files relate to other days and shared tools

- Builds on [Day 6](/days/day-06-networking-and-network-policy/) (cluster, images or secrets created there).
- The lesson also uses files from [Day 2](/days/day-02-docker-basics/).
- The lesson also uses files from [Day 3](/days/day-03-kind-kubernetes/).
- The lesson also uses files from [Day 4](/days/day-04-data-services-and-appwrite/).
- Files from this folder are used by [Day 9](/days/day-09-build-tools-and-tests/), [Day 10](/days/day-10-local-platform/), [Day 13](/days/day-13-ci-at-scale-build-sh/), [Day 18](/days/day-18-monitoring-your-kubernetes-cluster/), [Day 21](/days/day-21-is-my-app-up-gatus/), [Day 22](/days/day-22-progressive-delivery-flux-flagger/), [Day 23](/days/day-23-server-and-application-patching/).

## Homework

Work in `~/heyjob-labs/day07/`. Copy the manifests you change there; do not edit files you cannot explain.

### Exercise 1: Pain, then relief

**Do:** open three terminals with `port-forward` to the three apps and record, in `before-after.md`, how many terminals, ports, and URLs you needed. Then remove them and reach all three via Traefik with one host-based Ingress. Add one paragraph on what you gained and lost.

### Exercise 2: Host and path rules

**Do:** write `routes.yaml` so that `apps.localhost/python` goes to the Python API, `/java` to the Java API, and `/go` to the Go API, with a StripPrefix middleware for each.

### Exercise 3: Rate limit, proved

**Do:** apply a rate-limit of average 2, burst 3 to one route. Run the loop from step 8 and save the `200`/`429` counts. Then wait 5 seconds and show a single request succeeds.

### Exercise 4: Basic auth

**Do:** protect one app with basic auth using a Secret you create with `kubectl` (no secret in any file you commit). Show `401` without credentials, `401` with wrong ones, and `200` with the right ones.

### Exercise 5: A measured 80/20 split

**Do:** use `weighted.yaml` and a 200-request loop to count responses per version. Then change to 90/10, re-apply, and measure again. In `split.md` explain why the counts are never exactly 80/20.

### Exercise 6: Break it and diagnose it

**Do:** change the Service port in an Ingress backend from `80` to `8080` (the Service has no such port) and re-apply. Find the problem using three tools: `curl -i`, the Traefik dashboard (HTTP Routers/Services), and `kubectl -n apps get endpoints` plus `kubectl -n traefik logs deploy/traefik`. Then fix it.

**Deliverable:** `diagnosis.md`: the symptom (status code), what each tool showed, the root cause, and the fix.

### Exercise 7 (optional): TLS for the Java API

**Do:** generate a certificate for `hello-java.localhost` with mkcert, create a TLS Secret, and write an IngressRoute on `websecure` plus an HTTP-to-HTTPS redirect. Verify with `curl -v` that the issuer is mkcert.
