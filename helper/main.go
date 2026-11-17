// The helper is a small resident program for the PokeMMO controller layout.
// This is the H0 spike: it proves the shape (one static binary per system, a
// loopback page, a tray icon) before any of the Python tools are ported.
package main

import (
	"fmt"
	"net"
	"net/http"
	"os"
	"runtime"
)

const version = "0.0.0-spike"

func main() {
	args := os.Args[1:]
	cmd := "tray"
	if len(args) > 0 {
		cmd = args[0]
	}
	switch cmd {
	case "version":
		fmt.Printf("pokemmo-controller-helper %s %s/%s\n", version, runtime.GOOS, runtime.GOARCH)
	case "serve": // headless: no tray, for Steam Deck Game Mode, servers and CI
		l, err := listen()
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Println("http://" + l.Addr().String())
		os.Stdout.Sync()
		_ = http.Serve(l, handler())
	case "tray":
		runTray()
	default:
		fmt.Fprintln(os.Stderr, "usage: helper [serve|tray|version]")
		os.Exit(2)
	}
}

// listen binds loopback only, on a free port.
func listen() (net.Listener, error) { return net.Listen("tcp", "127.0.0.1:0") }

func handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		fmt.Fprintln(w, "ok")
	})
	return mux
}
