//go:build windows

package main

import "os"

func umask() os.FileMode { return 0 }
