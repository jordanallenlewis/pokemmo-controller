package main

import (
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

func TestShortcutTargetPerSystem(t *testing.T) {
	none := func(string) bool { return false }
	all := func(string) bool { return true }
	cases := []struct {
		name, goos, pm string
		exists         func(string) bool
		exe, dir, opt  string
	}{
		{"windows", "windows", `C:\Games\PokeMMO`, none, `"C:\Games\PokeMMO\PokeMMO.exe"`, `"C:\Games\PokeMMO\"`, ""},
		{"mac system app", "darwin", "/x", all, `"/Applications/PokeMMO.app"`, `"/Applications/"`, ""},
		{"mac user app", "darwin", "/x", none, `"/Users/a/Applications/PokeMMO.app"`, `"/Users/a/Applications/"`, ""},
		{"flatpak", "linux", "/home/a/.var/app/com.pokemmo.PokeMMO/data/PokeMMO", none, `"/usr/bin/flatpak"`, `"/usr/bin/"`, "run com.pokemmo.PokeMMO"},
		{"snap", "linux", "/home/a/snap/pokemmo/current/PokeMMO", none, `"/snap/bin/pokemmo"`, `"/snap/bin/"`, ""},
		{"linux", "linux", "/home/a/PokeMMO", none, `"/home/a/PokeMMO/PokeMMO.sh"`, `"/home/a/PokeMMO/"`, ""},
	}
	for _, c := range cases {
		exe, dir, opt := shortcutTarget(c.goos, c.pm, "/Users/a", c.exists)
		if exe != c.exe || dir != c.dir || opt != c.opt {
			t.Errorf("%s: got %q %q %q", c.name, exe, dir, opt)
		}
	}
}

func TestPropsPlanSetsTheTenKeysAndKeepsTheRest(t *testing.T) {
	pm := t.TempDir()
	cfg := filepath.Join(pm, "config")
	writeFile(t, filepath.Join(cfg, "main.properties"),
		"a=1\r\nclient.controls.gdx.codex=99\r\nb=2\r\n")
	p := newPlan(pm)
	propsPlan(p, pm)
	got, _ := p.current(filepath.Join(cfg, "main.properties"))
	text := string(got)
	if !strings.Contains(text, "a=1\r\n") || !strings.Contains(text, "b=2\r\n") {
		t.Fatalf("other lines lost: %q", text)
	}
	if strings.Contains(text, "codex=99") || !strings.Contains(text, "client.controls.gdx.codex=42\r\n") {
		t.Fatalf("codex not replaced in place: %q", text)
	}
	for _, b := range keyboardBinds {
		if strings.Count(text, b.Key+"=") != 1 {
			t.Errorf("%s not exactly once: %q", b.Key, text)
		}
	}
	if strings.Contains(strings.ReplaceAll(text, "\r\n", ""), "\n") {
		t.Fatalf("line endings changed: %q", text)
	}
}

func TestPropsPlanCreatesMissingFile(t *testing.T) {
	pm := t.TempDir()
	p := newPlan(pm)
	propsPlan(p, pm)
	got, ok := p.current(filepath.Join(pm, "config", "main.properties"))
	if !ok || strings.Count(string(got), "\n") != len(keyboardBinds) {
		t.Fatalf("got %q", got)
	}
}

func writeFile(t *testing.T, path, text string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

// The Python tool stays the advanced option, so its key list and ours must not drift apart.
func TestKeyboardBindsMatchPythonTool(t *testing.T) {
	b, err := os.ReadFile(filepath.Join("..", "tools", "install_wheel.py"))
	if err != nil {
		t.Fatal(err)
	}
	re := regexp.MustCompile(`"(client\.controls\.gdx\.\w+)": (\d+)`)
	m := re.FindAllStringSubmatch(string(b), -1)
	if len(m) != len(keyboardBinds) {
		t.Fatalf("python has %d binds, go has %d", len(m), len(keyboardBinds))
	}
	for i, x := range m {
		if x[1] != keyboardBinds[i].Key || x[2] != strconv.Itoa(keyboardBinds[i].Code) {
			t.Errorf("bind %d: python %v, go %v", i, x[1:], keyboardBinds[i])
		}
	}
}
