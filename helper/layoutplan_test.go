package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type layoutPlanGolden struct {
	Types   []string          `json:"types"`
	Layouts map[string]string `json:"layouts"`
	Account string            `json:"account"`
	Plans   []struct {
		Label string            `json:"label"`
		Files map[string]string `json:"files"`
		Puts  []struct {
			Path     string `json:"path"`
			Data     string `json:"data"`
			BackupOK bool   `json:"backup_ok"`
		} `json:"puts"`
		Notes []string `json:"notes"`
	} `json:"plans"`
	Userdirs struct {
		Dirs       []string `json:"dirs"`
		Files      []string `json:"files"`
		Picked     []string `json:"picked"`
		NoUserdata []string `json:"no_userdata"`
	} `json:"userdirs"`
}

func loadLayoutPlanGolden(t *testing.T) layoutPlanGolden {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("..", "tests", "golden", "layoutplan-parity.json"))
	if err != nil {
		t.Fatal(err)
	}
	var g layoutPlanGolden
	if err := json.Unmarshal(b, &g); err != nil {
		t.Fatal(err)
	}
	if len(g.Plans) == 0 {
		t.Fatal("golden file has no cases")
	}
	return g
}

func tempRoot(t *testing.T) string {
	t.Helper()
	root, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	return root
}

func TestControllerTypesMatchPython(t *testing.T) {
	g := loadLayoutPlanGolden(t)
	if strings.Join(g.Types, ",") != strings.Join(controllerTypes, ",") {
		t.Fatalf("controllerTypes %v, Python %v", controllerTypes, g.Types)
	}
}

func TestLayoutPlanMatchesPython(t *testing.T) {
	g := loadLayoutPlanGolden(t)
	for _, c := range g.Plans {
		t.Run(c.Label, func(t *testing.T) {
			steam := filepath.Join(tempRoot(t), "STEAM")
			for rel, data := range c.Files {
				if err := writeAtomic(filepath.Join(steam, filepath.FromSlash(rel)), unb64(t, data)); err != nil {
					t.Fatal(err)
				}
			}
			p := &Plan{changes: map[string]*pendingChange{}, state: map[string]any{}}
			layoutPlan(p, steam, g.Account, g.Layouts)
			norm := func(s string) string {
				return strings.Replace(strings.ReplaceAll(s, `\`, "/"), filepath.ToSlash(steam), "$S", 1)
			}
			if len(p.order) != len(c.Puts) {
				t.Fatalf("%d files planned, Python %d", len(p.order), len(c.Puts))
			}
			for i, want := range c.Puts {
				path := p.order[i]
				ch := p.changes[path]
				if norm(path) != want.Path {
					t.Fatalf("file %d is %s, Python %s", i, norm(path), want.Path)
				}
				if !bytes.Equal(ch.data, unb64(t, want.Data)) {
					t.Fatalf("%s: bytes differ from Python", want.Path)
				}
				if ch.backupOK != want.BackupOK {
					t.Fatalf("%s: backup kept=%v, Python %v", want.Path, ch.backupOK, want.BackupOK)
				}
			}
			var notes []string
			for _, n := range p.Notes {
				notes = append(notes, norm(n))
			}
			if strings.Join(notes, "\n") != strings.Join(c.Notes, "\n") {
				t.Fatalf("notes %q, Python %q", notes, c.Notes)
			}
		})
	}
}

func TestSteamUserdirsMatchPython(t *testing.T) {
	g := loadLayoutPlanGolden(t).Userdirs
	steam := tempRoot(t)
	for _, d := range g.Dirs {
		if err := os.MkdirAll(filepath.Join(steam, "userdata", d), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	for _, f := range g.Files {
		if err := writeAtomic(filepath.Join(steam, "userdata", f), nil); err != nil {
			t.Fatal(err)
		}
	}
	var picked []string
	dirs, err := steamUserdirs(steam)
	if err != nil {
		t.Fatal(err)
	}
	for _, u := range dirs {
		picked = append(picked, filepath.Base(u))
	}
	if strings.Join(picked, ",") != strings.Join(g.Picked, ",") {
		t.Fatalf("picked %v, Python %v", picked, g.Picked)
	}
	if got, err := steamUserdirs(filepath.Join(steam, "nothing")); err != nil || len(got) != len(g.NoUserdata) {
		t.Fatalf("no userdata folder: picked %v, Python %v", got, g.NoUserdata)
	}
}
