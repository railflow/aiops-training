Go starter. The `go.sum` file is not included because Go was not available where this was written: generate it with
`go mod tidy` on your machine (or set the function's build command to `go mod tidy`; check the Appwrite Go runtime docs).
`Context.Req.Query` as a map is an assumption taken from the Python and Node runtimes: check the types package if the build fails.
