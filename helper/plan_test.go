package main

import (
	"encoding/base64"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
)

type planPut struct {
	File     string `json:"file"`
	Text     string `json:"text"`
	BackupOK *bool  `json:"backup_ok"`
}

type planStep struct {
	Op           string              `json:"op"`
	File         string              `json:"file"`
	Text         string              `json:"text"`
	Fresh        bool                `json:"fresh"`
	Uninstall    bool                `json:"uninstall"`
	Puts         []planPut           `json:"puts"`
	Deletes      []string            `json:"deletes"`
	RestoreExact []string            `json:"restore_exact"`
	DropBackups  []string            `json:"drop_backups"`
	Result       *string             `json:"result"`
	Pending      []string            `json:"pending"`
	After        map[string]snapFile `json:"after"`
}

type snapFile struct {
	B64   string         `json:"b64"`
	State map[string]any `json:"state"`
}

type planGolden struct {
	Version string `json:"version"`
	Cases   []struct {
		Name  string     `json:"name"`
		Steps []planStep `json:"steps"`
	} `json:"cases"`
}

func normPath(s, root string) string {
	return strings.ReplaceAll(strings.ReplaceAll(s, root, "$ROOT"), "\\", "/")
}

// snapshot mirrors snapshot() in tests/gen_plan_golden.py.
func snapshot(t *testing.T, root string) map[string]snapFile {
	t.Helper()
	out := map[string]snapFile{}
	filepath.Walk(root, func(p string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || strings.HasSuffix(p, ".tmp") {
			return nil
		}
		rel, _ := filepath.Rel(root, p)
		rel = filepath.ToSlash(rel)
		b, _ := os.ReadFile(p)
		if rel == "config/"+stateName {
			var st map[string]any
			if err := json.Unmarshal(b, &st); err != nil {
				t.Fatalf("record is not JSON: %v", err)
			}
			files := map[string]any{}
			for k, v := range st["files"].(map[string]any) {
				files[normPath(k, root)] = v
			}
			st["files"] = files
			dirs := []any{}
			cd, _ := st["created_dirs"].([]any)
			for _, d := range cd {
				dirs = append(dirs, normPath(d.(string), root))
			}
			st["created_dirs"] = dirs
			out[rel] = snapFile{State: st}
		} else {
			out[rel] = snapFile{B64: base64.StdEncoding.EncodeToString(b)}
		}
		return nil
	})
	return out
}

func TestPlanMatchesPython(t *testing.T) {
	b, err := os.ReadFile(filepath.Join("..", "tests", "golden", "plan-parity.json"))
	if err != nil {
		t.Fatal(err)
	}
	var g planGolden
	if err := json.Unmarshal(b, &g); err != nil {
		t.Fatal(err)
	}
	if g.Version != recordVersion {
		t.Fatalf("recordVersion %q but tools/common.py VERSION is %q", recordVersion, g.Version)
	}
	for _, c := range g.Cases {
		t.Run(c.Name, func(t *testing.T) {
			root, _ := filepath.EvalSymlinks(t.TempDir())
			at := func(rel string) string { return filepath.Join(root, filepath.FromSlash(rel)) }
			for i, st := range c.Steps {
				switch st.Op {
				case "write":
					if err := writeAtomic(at(st.File), []byte(st.Text)); err != nil {
						t.Fatal(err)
					}
				case "exact":
					orig, existed, ok := newPlan(root).exactOriginal(at(st.File))
					var got *string
					switch {
					case !ok:
						s := "differs"
						got = &s
					case existed:
						s := base64.StdEncoding.EncodeToString(orig)
						got = &s
					}
					if (got == nil) != (st.Result == nil) || (got != nil && *got != *st.Result) {
						t.Fatalf("step %d exact %s: got %v want %v", i, st.File, got, st.Result)
					}
				case "plan":
					plan := newPlan(root)
					plan.Fresh = st.Fresh
					for _, m := range st.RestoreExact {
						orig, existed, ok := plan.exactOriginal(at(m))
						if !ok {
							continue
						}
						if existed {
							plan.put(at(m), orig, true)
						} else {
							plan.delete(at(m))
						}
					}
					for _, p := range st.Puts {
						ok := p.BackupOK == nil || *p.BackupOK
						plan.put(at(p.File), []byte(p.Text), ok)
					}
					for _, d := range st.Deletes {
						plan.delete(at(d))
					}
					for _, d := range st.DropBackups {
						plan.DropBackups = append(plan.DropBackups, backupPath(at(d)))
					}
					var pend []string
					for _, p := range plan.pending() {
						pend = append(pend, normPath(p, root))
					}
					sort.Strings(pend)
					if !reflect.DeepEqual(append([]string{}, pend...), append([]string{}, st.Pending...)) {
						t.Fatalf("step %d pending: %v want %v", i, pend, st.Pending)
					}
					if err := plan.commit(st.Uninstall); err != nil {
						t.Fatal(err)
					}
				}
				if got := snapshot(t, root); !reflect.DeepEqual(got, st.After) {
					gj, _ := json.MarshalIndent(got, "", " ")
					wj, _ := json.MarshalIndent(st.After, "", " ")
					t.Fatalf("step %d (%s) folder differs from Python.\ngot:\n%s\nwant:\n%s", i, st.Op, gj, wj)
				}
			}
		})
	}
}

func TestPlanReadOnlyStopsBeforeAnyWrite(t *testing.T) {
	root := t.TempDir()
	a, b := filepath.Join(root, "a"), filepath.Join(root, "b")
	os.WriteFile(a, []byte("a0"), 0o644)
	os.WriteFile(b, []byte("b0"), 0o444)
	os.Chmod(b, 0o444)
	p := newPlan(root)
	p.put(a, []byte("a1"), true)
	p.put(b, []byte("b1"), true)
	if err := p.commit(false); err == nil {
		t.Fatal("wrote over a read-only file")
	}
	if got, _ := os.ReadFile(a); string(got) != "a0" {
		t.Fatalf("first file changed before the check: %q", got)
	}
	if _, err := os.Stat(backupPath(a)); err == nil {
		t.Fatal("a backup was written for a run that changed nothing")
	}
}

func TestPlanKeepsUnknownRecordKeys(t *testing.T) {
	root := t.TempDir()
	os.MkdirAll(filepath.Join(root, "config"), 0o755)
	os.WriteFile(filepath.Join(root, "config", stateName), []byte(`{"files":{},"extra":{"n":12345678901234567890}}`), 0o644)
	p := newPlan(root)
	p.put(filepath.Join(root, "config", "x"), []byte("1"), true)
	if err := p.commit(false); err != nil {
		t.Fatal(err)
	}
	b, _ := os.ReadFile(filepath.Join(root, "config", stateName))
	if !strings.Contains(string(b), "12345678901234567890") {
		t.Fatalf("an unknown key was changed: %s", b)
	}
}
