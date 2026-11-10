package deploy

import rego.v1

# A deploy is allowed only when no rule produced a denial message.
default allow := false

allow if count(deny) == 0

# The single document callers ask for: the verdict and every reason, so a pipeline can print them.
decision := {
	"allow": allow,
	"reasons": [reason | some reason in deny],
}
