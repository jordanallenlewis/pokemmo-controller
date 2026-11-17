package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"time"
)

// writeAtomic replaces path with data in one step: a reader sees the old file
// or the new one, never half. Keeps the file's own permissions. A read-only
// file is refused with nothing changed.
func writeAtomic(path string, data []byte) error {
	st, statErr := os.Stat(path)
	if statErr == nil && st.Mode().Perm()&0o200 == 0 {
		return fmt.Errorf("%s is read-only. Make it writable, then run this again. Nothing was changed in it", path)
	}
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o777); err != nil {
		return err
	}
	f, err := os.CreateTemp(dir, filepath.Base(path)+".*.tmp")
	if err != nil {
		if statErr != nil {
			return err
		}
		// the folder is not writable but the file is: write in place
		return os.WriteFile(path, data, 0)
	}
	tmp := f.Name()
	cleanup := func() { f.Close(); os.Remove(tmp) }
	if _, err := f.Write(data); err != nil {
		cleanup()
		return err
	}
	if err := f.Sync(); err != nil {
		cleanup()
		return err
	}
	if err := f.Close(); err != nil {
		os.Remove(tmp)
		return err
	}
	if statErr == nil {
		_ = os.Chmod(tmp, st.Mode().Perm())
	} else if runtime.GOOS != "windows" {
		_ = os.Chmod(tmp, 0o666&^umask())
	}
	var last error
	for i := 0; i < 10; i++ { // antivirus and indexers can hold a file for a moment on Windows
		if last = os.Rename(tmp, path); last == nil {
			return nil
		}
		time.Sleep(300 * time.Millisecond)
	}
	os.Remove(tmp)
	return last
}
