// Explicit development harness for client-to-phone contract verification.
// Authentication here is a fixed test fixture, not production Sub2API authentication.
package main

import (
	"context"
	"encoding/json"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"

	gateway "lma.local/sub2api-localgateway"
)

func main() {
	address := os.Getenv("LMA_PROBE_PHONE_ORIGIN")
	directory := os.Getenv("LMA_PROBE_DIRECTORY")
	if address == "" || directory == "" || os.Getenv("LMA_PROBE_PHONE_KEY") == "" {
		os.Exit(2)
	}
	g, e := gateway.New(gateway.Config{StateFile: filepath.Join(directory, "registry-private.json"), Accounts: []gateway.Account{{ID: 1, GroupID: 1, BaseURL: address, KeyEnv: "LMA_PROBE_PHONE_KEY"}}})
	if e != nil {
		os.Exit(3)
	}
	defer g.Close()
	if g.Sync(context.Background(), 1) != nil {
		os.Exit(4)
	}
	listener, e := net.Listen("tcp", "127.0.0.1:0")
	if e != nil {
		os.Exit(5)
	}
	server := &http.Server{Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		owner := ""
		switch r.Header.Get("Authorization") {
		case "Bearer lma-probe-alice":
			owner = "alice"
		case "Bearer lma-probe-bob":
			owner = "bob"
		default:
			w.WriteHeader(401)
			return
		}
		g.ServeHTTP(w, r, gateway.Principal{Owner: owner, GroupID: 1})
	})}
	json.NewEncoder(os.Stdout).Encode(map[string]any{"port": listener.Addr().(*net.TCPAddr).Port, "auth": "explicit_test_fixture"})
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()
	go func() { <-ctx.Done(); server.Close() }()
	server.Serve(listener)
}
