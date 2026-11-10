package deploy

import rego.v1

# Deploys are allowed only on Wednesdays from 20:00 up to (not including) 22:00
# in the timezone the caller names. input.now_ns lets tests and dry runs pin the clock.
window_weekday := "Wednesday"

window_start_hour := 20

window_end_hour := 22

now_ns := object.get(input, "now_ns", time.now_ns())

zone := object.get(input, "timezone", "UTC")

local_weekday := time.weekday([now_ns, zone])

local_hour := time.clock([now_ns, zone])[0]

in_window if {
	local_weekday == window_weekday
	local_hour >= window_start_hour
	local_hour < window_end_hour
}

deny contains msg if {
	not in_window
	msg := sprintf(
		"outside the deploy window (%s %02d:00-%02d:00 %s); it is %s %02d:00 there",
		[window_weekday, window_start_hour, window_end_hour, zone, local_weekday, local_hour],
	)
}
