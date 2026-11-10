package main

import (
	"fmt"
	"os"
	"runtime"
	"strconv"
	"time"
)

func main() {
	name := os.Getenv("NAME")
	if name == "" {
		name = "world"
	}
	// LOOP_SECONDS=0 (default): print once and exit.
	// LOOP_SECONDS=10: print every 10 seconds forever.
	interval, _ := strconv.Atoi(os.Getenv("LOOP_SECONDS"))
	host, _ := os.Hostname()
	for {
		fmt.Printf("Hello, %s! from Go %s on %s\n", name, runtime.Version(), host)
		if interval <= 0 {
			break
		}
		time.Sleep(time.Duration(interval) * time.Second)
	}
}
