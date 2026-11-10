# Day 7: Traefik, one front door for your apps: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

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
