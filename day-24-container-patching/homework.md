# Day 24: Container patching and hardening: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

### Exercise 1: Choose a base for your own app

**Do:** pick an app from earlier days, evaluate two bases, and write a one-page decision with size, findings (dated), debug story and risks.
### Exercise 2: Multi-stage everything

**Do:** convert one `Dockerfile` so build tools and caches stay in a builder stage.
### Exercise 3: Break it, a root image under restricted

**Do:** deploy an image that insists on running as root (for example the stock `nginx` image, which expects to bind port 80 as root) into `hardened`.
### Exercise 4: DNS for the default-deny namespace

**Do:** extend the NetworkPolicy so pods in `hardened` can resolve names (egress to kube-dns on port 53) and nothing else.
### Exercise 5: Extend the policy

**Do:** add rules to `no-latest.rego` that deny `hostNetwork: true` and containers with no `resources.limits.memory`, each with a test.
### Exercise 6: A scheduled rebuild

**Do:** write the workflow that rebuilds, scans, and fails loudly when the weekly scan finds something new.
### Exercise 7: Read a vendor's terms

**Do:** pick one hardened-image vendor and one Bitnami-style catalogue, and write down what is free, what is paid, which tags you can pin, and how updates are delivered. Cite the page and date.
