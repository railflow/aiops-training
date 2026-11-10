package deploy

import rego.v1

# Minimum line or instruction coverage, in percent. Change it here once, for every service.
min_coverage := 80

deny contains msg if {
	not input.coverage
	msg := "no coverage figure was supplied; refusing to deploy untested code"
}

deny contains msg if {
	input.coverage < min_coverage
	msg := sprintf("coverage %.1f%% is below the required %d%%", [input.coverage, min_coverage])
}
