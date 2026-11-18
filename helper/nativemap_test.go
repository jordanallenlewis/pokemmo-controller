package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
)

type nativeGolden struct {
	Names   []string   `json:"names"`
	Default [][]string `json:"default_sets"`
	Legacy  [][]string `json:"legacy_sets"`
	Extra   [][]string `json:"custom_extra"`
	Entries []struct {
		Name   string  `json:"name"`
		Labels bool    `json:"labels"`
		Layout *string `json:"layout"`
		Entry  string  `json:"entry"`
	} `json:"entries"`
	Ours []struct {
		Entry   string `json:"entry"`
		Default bool   `json:"default"`
		Custom  bool   `json:"custom"`
	} `json:"ours"`
	Split []struct {
		Value   string      `json:"value"`
		Entries [][2]string `json:"entries"`
	} `json:"split"`
	Logged []struct {
		Text  string   `json:"text"`
		Names []string `json:"names"`
	} `json:"logged"`
	Nintendo        [][]any  `json:"is_nintendo"`
	ControllerNames []string `json:"controller_names"`
}

func loadNative(t *testing.T) nativeGolden {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("..", "tests", "golden", "native-parity.json"))
	if err != nil {
		t.Fatal(err)
	}
	var g nativeGolden
	if err := json.Unmarshal(b, &g); err != nil {
		t.Fatal(err)
	}
	return g
}

// customBinds finds the native binds of a named layout case in the layout golden file.
func customBinds(t *testing.T, label string) []Bind {
	t.Helper()
	for _, c := range loadGolden(t).Cases {
		if c.Label == label {
			lay, err := ParseLayout([]byte(c.Text))
			if err != nil {
				t.Fatal(err)
			}
			return lay.Binds
		}
	}
	t.Fatalf("no layout case %q", label)
	return nil
}

func setKeys(sets [][]string) []string {
	var out []string
	for _, s := range sets {
		c := append([]string(nil), s...)
		out = append(out, partSet(c))
	}
	sort.Strings(out)
	return out
}

func keysOf(m map[string]bool) []string {
	var out []string
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func TestNativeNamesAndSetsMatchPython(t *testing.T) {
	g := loadNative(t)
	if !reflect.DeepEqual(controllerNames(), g.ControllerNames) {
		t.Fatalf("pad names differ from Python")
	}
	if got, want := keysOf(layoutSets(DefaultLayout().Binds)), setKeys(g.Default); !reflect.DeepEqual(got, want) {
		t.Fatalf("default layout forms differ from Python")
	}
	if got, want := keysOf(layoutSets(legacyBinds())), setKeys(g.Legacy); !reflect.DeepEqual(got, want) {
		t.Fatalf("legacy layout forms differ from Python")
	}
	for _, p := range g.Nintendo {
		if isNintendo(p[0].(string)) != p[1].(bool) {
			t.Fatalf("isNintendo(%q) differs from Python", p[0])
		}
	}
}

func TestNativeEntriesMatchPython(t *testing.T) {
	g := loadNative(t)
	for _, e := range g.Entries {
		var binds []Bind
		if e.Layout != nil {
			binds = customBinds(t, *e.Layout)
		}
		if got := encodeOne(e.Name, e.Labels, binds); got != e.Entry {
			t.Fatalf("%q labels=%v layout=%v\n go:     %s\n python: %s", e.Name, e.Labels, e.Layout, got, e.Entry)
		}
	}
}

func TestNativeIsOursMatchesPython(t *testing.T) {
	g := loadNative(t)
	extra := map[string]bool{}
	for _, k := range setKeys(g.Extra) {
		extra[k] = true
	}
	for _, o := range g.Ours {
		if got := isOurs(o.Entry, nil); got != o.Default {
			t.Errorf("isOurs(%q) = %v, Python %v", o.Entry, got, o.Default)
		}
		if got := isOurs(o.Entry, extra); got != o.Custom {
			t.Errorf("isOurs(%q, custom) = %v, Python %v", o.Entry, got, o.Custom)
		}
	}
}

func TestNativeSplitAndLogsMatchPython(t *testing.T) {
	g := loadNative(t)
	for _, c := range g.Split {
		var got [][2]string
		for _, e := range splitEntries(c.Value) {
			got = append(got, [2]string{e.Name, e.Entry})
		}
		if len(got) != len(c.Entries) || (len(got) > 0 && !reflect.DeepEqual(got, c.Entries)) {
			t.Errorf("splitEntries(%q)\n go:     %q\n python: %q", c.Value, got, c.Entries)
		}
	}
	for _, c := range g.Logged {
		got := loggedNamesIn(c.Text, []string{})
		// Python lists every match; Go lists first sightings. Same set, first sightings in order.
		var first []string
		for _, n := range c.Names {
			dup := false
			for _, f := range first {
				dup = dup || f == n
			}
			if !dup {
				first = append(first, n)
			}
		}
		if len(got) != len(first) || (len(first) > 0 && !reflect.DeepEqual(got, first)) {
			t.Errorf("log %q: go %q, python %q", c.Text, got, first)
		}
	}
}

func TestLoggedNamesReadsLogFolder(t *testing.T) {
	dir := t.TempDir()
	os.MkdirAll(filepath.Join(dir, "log"), 0o755)
	os.WriteFile(filepath.Join(dir, "log", "b.log"), []byte("Controller Pad B ( ax 1 btn 1) 1 attached\n"), 0o644)
	os.WriteFile(filepath.Join(dir, "log", "a.log"), []byte("x\xffy\nController Pad A ( ax 1 btn 1) 1 attached\nController Pad B ( ax 1 btn 1) attached\n"), 0o644)
	os.WriteFile(filepath.Join(dir, "log", "c.txt"), []byte("Controller Pad C ( ax 1 btn 1) attached\n"), 0o644)
	if got := strings.Join(loggedNames(dir), ","); got != "Pad A,Pad B" {
		t.Fatalf("got %q", got)
	}
	if got := loggedNames(filepath.Join(dir, "none")); len(got) != 0 {
		t.Fatalf("got %q", got)
	}
}
