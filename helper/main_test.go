package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestHealth(t *testing.T) {
	s := httptest.NewServer(handler())
	defer s.Close()
	r, err := http.Get(s.URL + "/health")
	if err != nil {
		t.Fatal(err)
	}
	b, _ := io.ReadAll(r.Body)
	if strings.TrimSpace(string(b)) != "ok" {
		t.Fatalf("got %q", b)
	}
}

func TestListenIsLoopbackOnly(t *testing.T) {
	l, err := listen()
	if err != nil {
		t.Fatal(err)
	}
	defer l.Close()
	if !strings.HasPrefix(l.Addr().String(), "127.0.0.1:") {
		t.Fatalf("listens on %s, want loopback only", l.Addr())
	}
}
