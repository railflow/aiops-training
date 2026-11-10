import os

import yaml

import check_job  # noqa: E402

D = os.path.join(os.path.dirname(__file__), "..", "sandbox")


def load(n):
    return list(yaml.safe_load_all(open(os.path.join(D, n))))


def test_good_job_has_no_errors():
    errors, _ = check_job.check(load("good-job.yaml"))
    assert errors == []


def test_bad_job_is_flagged_for_every_classic_mistake():
    errors, _ = check_job.check(load("bad-job.yaml"))
    text = "\n".join(errors)
    for needle in ("hostNetwork", "privileged", "hostPath", "docker.sock", "looks like a secret", "automountServiceAccountToken", "activeDeadlineSeconds",
                   "no cpu limit", "no memory limit", "not pinned", "NetworkPolicy"):
        assert needle in text, needle


def test_open_egress_policy_is_an_error():
    docs = load("good-job.yaml")
    docs[1]["spec"]["egress"] = [{"to": [{"ipBlock": {"cidr": "0.0.0.0/0"}}]}]
    assert any("0.0.0.0/0" in e for e in check_job.check(docs)[0])


def test_cli_exit_codes():
    assert check_job.main([os.path.join(D, "good-job.yaml")]) == 0
    assert check_job.main([os.path.join(D, "bad-job.yaml")]) == 1
