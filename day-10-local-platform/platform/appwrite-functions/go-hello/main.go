// Appwrite Function (runtime go-1.26). The runtime calls handler.Main once per request.
// Verified against Appwrite's own Go starter template (appwrite/templates, go/starter) on 2026-11-05.
// NOT compiled by the course author: Go is not installed on that machine.
package handler

import (
	"github.com/open-runtimes/types-for-go/v4/openruntimes"
)

type Greeting struct {
	Message string `json:"message"`
	Runtime string `json:"runtime"`
}

func Main(Context openruntimes.Context) openruntimes.Response {
	if Context.Req.Path == "/ping" {
		return Context.Res.Text("pong")
	}
	name := Context.Req.Query["name"]
	if name == "" {
		name = "world"
	}
	Context.Log("greeting " + name)
	return Context.Res.Json(Greeting{Message: "Hello, " + name + "!", Runtime: "go"})
}
