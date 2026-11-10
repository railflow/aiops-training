package patching.images

import rego.v1

# Input is a Kubernetes Deployment (or anything with spec.template.spec.containers), for example the output of
#   kubectl get deploy NAME -o json
# Run:  opa eval -d policies -i deploy.json 'data.patching.images.deny'   or   opa test policies
# NOT RUN when this file was written (no OPA on the author's machine): run `opa test policies` and fix what it says.

containers := input.spec.template.spec.containers

# A registry host may contain a colon (the port), so look for a tag only in the last path segment.
last_segment(image) := split(image, "/")[count(split(image, "/")) - 1]

untagged(image) if {
	not contains(image, "@")
	not contains(last_segment(image), ":")
}

deny contains msg if {
	some c in containers
	untagged(c.image)
	msg := sprintf("container %q uses image %q with no tag or digest (implicitly :latest)", [c.name, c.image])
}

deny contains msg if {
	some c in containers
	endswith(c.image, ":latest")
	msg := sprintf("container %q uses the mutable tag :latest (%s)", [c.name, c.image])
}

# Stricter, switch it on when your pipeline pins digests everywhere: digest required for every image.
warn contains msg if {
	some c in containers
	not contains(c.image, "@sha256:")
	msg := sprintf("container %q is not pinned by digest (%s)", [c.name, c.image])
}

# Containers must not run privileged.
deny contains msg if {
	some c in containers
	c.securityContext.privileged == true
	msg := sprintf("container %q is privileged", [c.name])
}
