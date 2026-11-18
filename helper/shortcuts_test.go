package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type shortcutsGolden struct {
	Parse []struct {
		Label     string  `json:"label"`
		Data      string  `json:"data"`
		OK        bool    `json:"ok"`
		Rewritten *string `json:"rewritten"`
	} `json:"parse"`
	Plans []struct {
		Label       string    `json:"label"`
		Data        *string   `json:"data"`
		Bak         *string   `json:"bak"`
		Version     *string   `json:"version"`
		Fresh       bool      `json:"fresh"`
		AddedBefore bool      `json:"added_before"`
		Target      [3]string `json:"target"`
		Put         *string   `json:"put"`
		Notes       []string  `json:"notes"`
		Added       []string  `json:"added"`
	} `json:"plans"`
}

func loadShortcutsGolden(t *testing.T) shortcutsGolden {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("..", "tests", "golden", "shortcuts-parity.json"))
	if err != nil {
		t.Fatal(err)
	}
	var g shortcutsGolden
	if err := json.Unmarshal(b, &g); err != nil {
		t.Fatal(err)
	}
	if len(g.Parse) == 0 || len(g.Plans) == 0 {
		t.Fatal("golden file has no cases")
	}
	return g
}

func unb64(t *testing.T, s string) []byte {
	t.Helper()
	b, err := base64.StdEncoding.DecodeString(s)
	if err != nil {
		t.Fatal(err)
	}
	return b
}

func TestShortcutsReadWriteMatchPython(t *testing.T) {
	for _, c := range loadShortcutsGolden(t).Parse {
		t.Run(c.Label, func(t *testing.T) {
			sc, err := readShortcuts(unb64(t, c.Data))
			if (err == nil) != c.OK {
				t.Fatalf("read ok=%v, Python ok=%v (%v)", err == nil, c.OK, err)
			}
			if c.OK && !bytes.Equal(writeShortcuts(sc), unb64(t, *c.Rewritten)) {
				t.Fatalf("written bytes differ from Python")
			}
		})
	}
}

func TestShortcutPlanMatchesPython(t *testing.T) {
	for _, c := range loadShortcutsGolden(t).Plans {
		t.Run(c.Label, func(t *testing.T) {
			root, _ := filepath.EvalSymlinks(t.TempDir())
			userdir := filepath.Join(root, "USERDIR")
			path := filepath.Join(userdir, "config", "shortcuts.vdf")
			if c.Data != nil {
				if err := writeAtomic(path, unb64(t, *c.Data)); err != nil {
					t.Fatal(err)
				}
			}
			if c.Bak != nil {
				if err := writeAtomic(backupPath(path), unb64(t, *c.Bak)); err != nil {
					t.Fatal(err)
				}
			}
			p := &Plan{changes: map[string]*pendingChange{}, state: map[string]any{}, Fresh: c.Fresh}
			if c.Version != nil {
				p.state["version"] = *c.Version
			}
			if c.AddedBefore {
				p.state["shortcuts_added"] = []any{path}
			}
			shortcutPlan(p, userdir, c.Target[0], c.Target[1], c.Target[2])

			norm := func(s string) string {
				return strings.ReplaceAll(strings.ReplaceAll(s, userdir, "$U"), `\`, "/")
			}
			ch, put := p.changes[path]
			if put != (c.Put != nil) {
				t.Fatalf("wrote the file=%v, Python wrote it=%v", put, c.Put != nil)
			}
			if put && !bytes.Equal(ch.data, unb64(t, *c.Put)) {
				t.Fatalf("shortcuts.vdf bytes differ from Python")
			}
			var notes []string
			for _, n := range p.Notes {
				notes = append(notes, norm(n))
			}
			if strings.Join(notes, "\n") != strings.Join(c.Notes, "\n") {
				t.Fatalf("notes %q, Python %q", notes, c.Notes)
			}
			var added []string
			list, ok := p.state["shortcuts_added"].([]any)
			if !ok {
				t.Fatal("shortcuts_added missing from the record")
			}
			for _, a := range list {
				added = append(added, norm(a.(string)))
			}
			if strings.Join(added, "\n") != strings.Join(c.Added, "\n") {
				t.Fatalf("shortcuts_added %q, Python %q", added, c.Added)
			}
		})
	}
}

func TestShortcutsRefuseDeepNesting(t *testing.T) {
	var b []byte
	for i := 0; i < 10000; i++ {
		b = append(b, 0, 'k', 0)
	}
	if _, err := readShortcuts(b); err == nil {
		t.Fatal("a file nested 10000 deep was read")
	}
}

func TestShortcutAddIsOneEntry(t *testing.T) {
	// Adding twice must not add a second PokeMMO shortcut.
	sc := newBvMap()
	entry, _ := newShortcut(`"/x/PokeMMO.sh"`, `"/x/"`, "")
	sc.set(nextKey(sc), &bvValue{kind: bvkMap, m: entry})
	data := writeShortcuts(sc)
	root, _ := filepath.EvalSymlinks(t.TempDir())
	path := filepath.Join(root, "config", "shortcuts.vdf")
	if err := writeAtomic(path, data); err != nil {
		t.Fatal(err)
	}
	p := &Plan{changes: map[string]*pendingChange{}, state: map[string]any{"version": "1.3.0"}}
	shortcutPlan(p, root, `"/x/PokeMMO.sh"`, `"/x/"`, "")
	if len(p.changes) != 0 || len(p.Notes) != 0 {
		t.Fatalf("second add changed something: %v", p.Notes)
	}
}
