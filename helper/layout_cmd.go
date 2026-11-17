package main

import (
	"fmt"
	"io"
	"os"
)

// runLayout is `helper layout check FILE`: the same check the Python tool does
// before it writes anything. Exit 0 when the file is a layout this tool will
// write, 1 with the reason when it is not, 2 for a bad command line.
func runLayout(args []string, out, errw io.Writer) int {
	if len(args) != 2 || args[0] != "check" {
		fmt.Fprintln(errw, "usage: helper layout check FILE")
		return 2
	}
	b, err := os.ReadFile(args[1])
	if err != nil {
		fmt.Fprintf(errw, "Cannot read %s: %v\n", args[1], err)
		return 1
	}
	lay, err := ParseLayout(b)
	if err != nil {
		fmt.Fprintln(errw, err)
		return 1
	}
	fmt.Fprintf(out, "ok: %d binds, %d wheel slices\n", len(lay.Binds), len(lay.Wheel))
	return 0
}
