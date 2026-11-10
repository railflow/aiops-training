#!/usr/bin/env python3
"""Lint a Kubernetes manifest (Job + NetworkPolicy) for the properties an agent sandbox needs. A guard rail you can run in CI or as an admission-time check's twin.
  python3 sandbox/check_job.py sandbox/good-job.yaml
Findings are rules of thumb, not a proof of isolation: a container is not a VM boundary (see the page). Exit 1 if any ERROR."""
import re
import sys

import yaml

SECRET_LIKE = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|password|token|secret|api[_-]?key)", re.I)


def pod_specs(docs):
    for d in docs:
        if d and d.get("kind") == "Job":
            yield d, d["spec"]["template"]["spec"]


def check(docs):
    errors, warns = [], []
    docs = [d for d in docs if d]
    jobs = list(pod_specs(docs))
    if not jobs:
        errors.append("no Job found")
    for job, pod in jobs:
        spec = job["spec"]
        for flag in ("hostNetwork", "hostPID", "hostIPC"):
            if pod.get(flag):
                errors.append(f"{flag} is true")
        if pod.get("automountServiceAccountToken") is not False:
            errors.append("automountServiceAccountToken must be false (the agent does not need the cluster API)")
        if not pod.get("securityContext", {}).get("runAsNonRoot"):
            errors.append("pod securityContext.runAsNonRoot is not true")
        for v in pod.get("volumes", []):
            if "hostPath" in v:
                errors.append(f"volume '{v['name']}' is a hostPath ({v['hostPath'].get('path')}): host access")
        if "activeDeadlineSeconds" not in spec:
            errors.append("no activeDeadlineSeconds: a stuck agent runs forever")
        if "ttlSecondsAfterFinished" not in spec:
            warns.append("no ttlSecondsAfterFinished: finished Jobs pile up")
        if spec.get("backoffLimit", 6) != 0:
            warns.append("backoffLimit is not 0: failed agent runs will be retried silently (cost!)")
        for c in pod.get("containers", []):
            n, sc = c["name"], c.get("securityContext", {})
            if sc.get("privileged"):
                errors.append(f"container '{n}' is privileged")
            if sc.get("allowPrivilegeEscalation") is not False:
                errors.append(f"container '{n}': allowPrivilegeEscalation must be false")
            if "ALL" not in [x.upper() for x in sc.get("capabilities", {}).get("drop", [])]:
                warns.append(f"container '{n}': capabilities.drop does not include ALL")
            if not sc.get("readOnlyRootFilesystem"):
                warns.append(f"container '{n}': root filesystem is writable")
            lim = c.get("resources", {}).get("limits", {})
            for k in ("cpu", "memory"):
                if k not in lim:
                    errors.append(f"container '{n}': no {k} limit")
            img = c.get("image", "")
            if "@sha256:" not in img:
                (errors if img.endswith(":latest") or ":" not in img else warns).append(f"container '{n}': image '{img}' is not pinned by digest")
            for vm in c.get("volumeMounts", []):
                if "docker.sock" in vm.get("mountPath", ""):
                    errors.append(f"container '{n}' mounts docker.sock: that is root on the node")
            for e in c.get("env", []):
                if "value" in e and SECRET_LIKE.search(e["name"] + " " + str(e["value"])):
                    errors.append(f"container '{n}': env {e['name']} has a literal value that looks like a secret; use secretKeyRef")
    pols = [d for d in docs if d.get("kind") == "NetworkPolicy"]
    if not any("Egress" in p["spec"].get("policyTypes", []) for p in pols):
        errors.append("no NetworkPolicy restricting Egress for the sandbox pods")
    for p in pols:
        for rule in p["spec"].get("egress", []):
            if not rule.get("to") and not rule.get("ports"):
                errors.append(f"NetworkPolicy {p['metadata']['name']}: an egress rule allows everything")
            for t in rule.get("to", []):
                if t.get("ipBlock", {}).get("cidr") == "0.0.0.0/0":
                    errors.append(f"NetworkPolicy {p['metadata']['name']}: egress to 0.0.0.0/0")
    return errors, warns


def main(argv):
    rc = 0
    for path in argv:
        errors, warns = check(list(yaml.safe_load_all(open(path))))
        for e in errors:
            print(f"{path}: ERROR {e}")
        for w in warns:
            print(f"{path}: warn  {w}")
        if not errors:
            print(f"{path}: no errors")
        rc |= bool(errors)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) if len(sys.argv) > 1 else (print(__doc__) or 2))
