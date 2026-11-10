package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
)

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s host=%s xff=%q", r.Method, r.URL.RequestURI(), r.Host, r.Header.Get("X-Forwarded-For"))
		next.ServeHTTP(w, r)
	})
}

func newHandler(version, pod string) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})
	mux.HandleFunc("/readyz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ready"}`))
	})
	mux.HandleFunc("/version", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{
			"service": "hello-go",
			"version": version,
			"commit":  env("GIT_SHA", "unknown"),
		})
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		name := r.URL.Query().Get("name")
		if name == "" {
			name = "world"
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{
			"message":   "Hello, " + name + "!",
			"served_by": "go",
			"version":   version,
			"pod":       pod,
			"path":      r.URL.Path,
		})
	})
	return mux
}

func main() {
	version := env("APP_VERSION", "v1")
	pod, _ := os.Hostname()
	addr := ":" + env("PORT", "8080")
	log.Printf("Go API %s listening on %s", version, addr)
	log.Fatal(http.ListenAndServe(addr, logRequests(newHandler(version, pod))))
}
