package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func get(t *testing.T, path string) (*httptest.ResponseRecorder, map[string]string) {
	t.Helper()
	rec := httptest.NewRecorder()
	newHandler("v9", "test-pod").ServeHTTP(rec, httptest.NewRequest(http.MethodGet, path, nil))
	body := map[string]string{}
	_ = json.Unmarshal(rec.Body.Bytes(), &body)
	return rec, body
}

func TestHelloDefault(t *testing.T) {
	rec, body := get(t, "/hello")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if body["message"] != "Hello, world!" {
		t.Errorf("message = %q", body["message"])
	}
	if body["version"] != "v9" || body["path"] != "/hello" {
		t.Errorf("unexpected body: %v", body)
	}
}

func TestHelloWithName(t *testing.T) {
	_, body := get(t, "/?name=Ada")
	if body["message"] != "Hello, Ada!" {
		t.Errorf("message = %q", body["message"])
	}
}

func TestHealthz(t *testing.T) {
	rec, body := get(t, "/healthz")
	if rec.Code != http.StatusOK || body["status"] != "ok" {
		t.Errorf("healthz = %d %v", rec.Code, body)
	}
}

func TestReadyz(t *testing.T) {
	rec, body := get(t, "/readyz")
	if rec.Code != http.StatusOK || body["status"] != "ready" {
		t.Errorf("readyz = %d %v", rec.Code, body)
	}
}

func TestVersion(t *testing.T) {
	_, body := get(t, "/version")
	if body["service"] != "hello-go" || body["version"] == "" {
		t.Errorf("version = %v", body)
	}
}

func TestEnvFallback(t *testing.T) {
	t.Setenv("X_TEST_VALUE", "")
	if got := env("X_TEST_VALUE", "fallback"); got != "fallback" {
		t.Errorf("env = %q", got)
	}
}
