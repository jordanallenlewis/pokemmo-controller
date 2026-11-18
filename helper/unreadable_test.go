package main

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

// A file that is there but cannot be read must stop the run before anything is written, as the
// Python tool does. Treating it as missing would plan a new file with no backup and replace the
// player's own (their Steam Input choices for other games, their shortcuts).

func steamAccount(t *testing.T) (steam, cfg string) {
	t.Helper()
	steam = filepath.Join(tempRoot(t), "Steam")
	cfg = filepath.Join(steam, "steamapps", "common", "Steam Controller Configs", "12345", "config")
	if err := os.MkdirAll(cfg, 0o755); err != nil {
		t.Fatal(err)
	}
	return steam, cfg
}

func assertNothingWritten(t *testing.T, p *Plan, paths ...string) {
	t.Helper()
	if err := p.commit(false); err == nil {
		t.Fatal("commit went ahead although a file could not be read")
	}
	for _, f := range paths {
		if _, err := os.Stat(f); err == nil {
			t.Fatalf("%s was written", f)
		}
	}
}

func TestFolderInPlaceOfConfigsetStopsTheRun(t *testing.T) {
	steam, cfg := steamAccount(t)
	if err := os.Mkdir(filepath.Join(cfg, "configset_controller_xboxone.vdf"), 0o755); err != nil {
		t.Fatal(err)
	}
	p := newPlan(filepath.Join(tempRoot(t), "PokeMMO"))
	layoutPlan(p, steam, "12345", map[string]string{"controller_xboxone": "layout\n", "controller_ps5": "layout\n"})
	assertNothingWritten(t, p, filepath.Join(cfg, configDirName, "controller_xboxone.vdf"),
		filepath.Join(cfg, "configset_controller_ps5.vdf"))
}

func TestFolderInPlaceOfShortcutsStopsTheRun(t *testing.T) {
	userdir := filepath.Join(tempRoot(t), "userdata", "12345")
	path := filepath.Join(userdir, "config", "shortcuts.vdf")
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatal(err)
	}
	p := newPlan(filepath.Join(tempRoot(t), "PokeMMO"))
	shortcutPlan(p, userdir, `"/x/PokeMMO.sh"`, `"/x/"`, "")
	if err := p.commit(false); err == nil {
		t.Fatal("commit went ahead although shortcuts.vdf could not be read")
	}
}

func TestFolderInPlaceOfShortcutsBackupStopsTheRun(t *testing.T) {
	userdir := filepath.Join(tempRoot(t), "userdata", "12345")
	path := filepath.Join(userdir, "config", "shortcuts.vdf")
	if err := writeAtomic(path, writeShortcuts(newBvMap())); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(backupPath(path), 0o755); err != nil {
		t.Fatal(err)
	}
	before, _ := readBytes(path)
	p := newPlan(filepath.Join(tempRoot(t), "PokeMMO"))
	shortcutPlan(p, userdir, `"/x/PokeMMO.sh"`, `"/x/"`, "")
	if err := p.commit(false); err == nil {
		t.Fatal("commit went ahead although the backup could not be read")
	}
	if after, _ := readBytes(path); string(after) != string(before) {
		t.Fatal("shortcuts.vdf changed")
	}
}

func TestUnreadableConfigsetStopsTheRun(t *testing.T) {
	if runtime.GOOS == "windows" || os.Geteuid() == 0 {
		t.Skip("needs a file permission the test user cannot read past")
	}
	steam, cfg := steamAccount(t)
	cs := filepath.Join(cfg, "configset_controller_xboxone.vdf")
	if err := writeAtomic(cs, []byte("\"controller_config\"\n{\n}\n")); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(cs, 0o200); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.Chmod(cs, 0o644) })
	p := newPlan(filepath.Join(tempRoot(t), "PokeMMO"))
	layoutPlan(p, steam, "12345", map[string]string{"controller_xboxone": "layout\n"})
	assertNothingWritten(t, p, filepath.Join(cfg, configDirName, "controller_xboxone.vdf"))
}

func TestSteamUserdirsReportsAnUnreadableFolder(t *testing.T) {
	steam := tempRoot(t)
	if dirs, err := steamUserdirs(filepath.Join(steam, "missing")); err != nil || len(dirs) != 0 {
		t.Fatalf("no userdata folder: %v, %v", dirs, err)
	}
	if err := writeAtomic(filepath.Join(steam, "file", "userdata"), nil); err != nil {
		t.Fatal(err)
	}
	if dirs, err := steamUserdirs(filepath.Join(steam, "file")); err != nil || len(dirs) != 0 {
		t.Fatalf("userdata is a file: %v, %v", dirs, err) // Python: not a folder, no accounts
	}
	if runtime.GOOS == "windows" || os.Geteuid() == 0 {
		return
	}
	ud := filepath.Join(steam, "locked", "userdata")
	if err := os.MkdirAll(filepath.Join(ud, "12345"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(ud, 0o300); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.Chmod(ud, 0o755) })
	if _, err := steamUserdirs(filepath.Join(steam, "locked")); err == nil {
		t.Fatal("an unreadable userdata folder was read as no accounts")
	}
}
