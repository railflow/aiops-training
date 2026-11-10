# Day 6: Namespaces, Services, and NetworkPolicy: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

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
