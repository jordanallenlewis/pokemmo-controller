package main

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestWriteAtomicNewAndReplace(t *testing.T) {
	p := filepath.Join(t.TempDir(), "sub", "main.properties")
	if err := writeAtomic(p, []byte("a=1\n")); err != nil {
		t.Fatal(err)
	}
	if err := writeAtomic(p, []byte("a=2\n")); err != nil {
		t.Fatal(err)
	}
	b, _ := os.ReadFile(p)
	if string(b) != "a=2\n" {
		t.Fatalf("%q", b)
	}
	left, _ := filepath.Glob(filepath.Join(filepath.Dir(p), "*.tmp"))
	if len(left) != 0 {
		t.Fatalf("temp files left: %v", left)
	}
}

func TestWriteAtomicKeepsMode(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("modes are not meaningful on Windows")
	}
	p := filepath.Join(t.TempDir(), "f")
	os.WriteFile(p, []byte("x"), 0o640)
	os.Chmod(p, 0o640)
	if err := writeAtomic(p, []byte("y")); err != nil {
		t.Fatal(err)
	}
	st, _ := os.Stat(p)
	if st.Mode().Perm() != 0o640 {
		t.Fatalf("mode %v", st.Mode().Perm())
	}
}

func TestWriteAtomicRefusesReadOnly(t *testing.T) {
	p := filepath.Join(t.TempDir(), "f")
	os.WriteFile(p, []byte("keep"), 0o444)
	os.Chmod(p, 0o444)
	if err := writeAtomic(p, []byte("new")); err == nil {
		t.Fatal("wrote to a read-only file")
	}
	b, _ := os.ReadFile(p)
	if string(b) != "keep" {
		t.Fatalf("changed: %q", b)
	}
}
