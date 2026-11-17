package main

import (
	"fmt"
	"net/http"
	"os"

	"fyne.io/systray"
)

// runTray shows a tray (menu bar) icon and serves the page on loopback.
func runTray() {
	l, err := listen()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	go func() { _ = http.Serve(l, handler()) }()
	systray.Run(func() {
		systray.SetTitle("PokeMMO controller")
		systray.SetTooltip("PokeMMO controller helper")
		quit := systray.AddMenuItem("Quit", "Stop the helper")
		go func() { <-quit.ClickedCh; systray.Quit() }()
	}, func() {})
}
