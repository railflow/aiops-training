package deploy_test

import rego.v1

import data.deploy

# Instants computed for America/Los_Angeles (UTC-8 in November):
wed_21 := 1793854800000000000 # Wednesday 21:00 PST (it is already Thursday in UTC)
wed_19 := 1793847600000000000 # Wednesday 19:00 PST
wed_22 := 1793858400000000000 # Wednesday 22:00 PST (window is closed)
thu_21 := 1793941200000000000 # Thursday 21:00 PST

good := {
	"coverage": 85.0,
	"vulnerabilities": {"critical": 0, "high": 0},
	"timezone": "America/Los_Angeles",
	"now_ns": wed_21,
}

test_allowed_when_everything_is_fine if {
	deploy.allow with input as good
}

test_denied_when_coverage_is_low if {
	not deploy.allow with input as object.union(good, {"coverage": 42.0})
}

test_coverage_reason_mentions_the_threshold if {
	reasons := deploy.decision.reasons with input as object.union(good, {"coverage": 42.0})
	some r in reasons
	contains(r, "below the required 80%")
}

test_denied_when_coverage_is_missing if {
	not deploy.allow with input as object.remove(good, ["coverage"])
}

test_denied_on_critical_vulnerability if {
	not deploy.allow with input as object.union(good, {"vulnerabilities": {"critical": 1, "high": 0}})
}

test_denied_on_high_vulnerability if {
	not deploy.allow with input as object.union(good, {"vulnerabilities": {"critical": 0, "high": 2}})
}

test_denied_on_wrong_weekday if {
	not deploy.allow with input as object.union(good, {"now_ns": thu_21})
}

test_denied_before_the_window if {
	not deploy.allow with input as object.union(good, {"now_ns": wed_19})
}

test_denied_when_the_window_has_closed if {
	not deploy.allow with input as object.union(good, {"now_ns": wed_22})
}

test_timezone_matters if {
	# The same instant is Thursday in UTC, so the Wednesday window rule fails there.
	not deploy.allow with input as object.union(good, {"timezone": "UTC"})
}

test_all_reasons_are_reported_together if {
	bad := {"coverage": 10.0, "vulnerabilities": {"critical": 3, "high": 0}, "timezone": "UTC", "now_ns": thu_21}
	count(deploy.decision.reasons) == 3 with input as bad
}
