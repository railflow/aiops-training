package deploy

import rego.v1

# Block any HIGH or CRITICAL vulnerability that was reported for the image or source tree.
deny contains msg if {
	count_of("critical") + count_of("high") > 0
	msg := sprintf(
		"%d CRITICAL and %d HIGH vulnerabilities found; fix or accept them first",
		[count_of("critical"), count_of("high")],
	)
}

deny contains msg if {
	not input.vulnerabilities
	msg := "no vulnerability report was supplied"
}

count_of(severity) := n if {
	n := object.get(object.get(input, "vulnerabilities", {}), severity, 0)
}
