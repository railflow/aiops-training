package patching.images_test

import rego.v1

import data.patching.images

deploy(image) := {"spec": {"template": {"spec": {"containers": [{"name": "app", "image": image}]}}}}

test_pinned_tag_is_allowed if {
	count(images.deny) == 0 with input as deploy("registry.local/app:1.2.3")
}

test_digest_only_is_allowed if {
	count(images.deny) == 0 with input as deploy("registry.local/app@sha256:abc")
}

test_latest_is_denied if {
	count(images.deny) == 1 with input as deploy("registry.local/app:latest")
}

test_no_tag_is_denied if {
	count(images.deny) == 1 with input as deploy("registry.local/app")
}

test_registry_port_is_not_mistaken_for_a_tag if {
	# localhost:30500/app has a colon (the port) but no tag: it is implicitly :latest.
	count(images.deny) == 1 with input as deploy("localhost:30500/app")
}

test_warn_when_not_digest_pinned if {
	count(images.warn) == 1 with input as deploy("registry.local/app:1.2.3")
}
