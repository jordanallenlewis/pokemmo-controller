//go:build !windows

package main

import (
	"os"
	"syscall"
)

func umask() os.FileMode {
	m := syscall.Umask(0)
	syscall.Umask(m)
	return os.FileMode(m)
}
