package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

type goldenCase struct {
	Label  string     `json:"label"`
	Text   string     `json:"text"`
	OK     bool       `json:"ok"`
	Error  string     `json:"error"`
	Native [][]any    `json:"native"`
	Wheel  [][]string `json:"wheel"`
}

type golden struct {
	Cases      []goldenCase `json:"cases"`
	WheelScale [][]int      `json:"wheel_scale"`
	Resolution [][]any      `json:"resolution"`
}

func loadGolden(t *testing.T) golden {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("..", "tests", "golden", "layout-parity.json"))
	if err != nil {
		t.Fatal(err)
	}
	var g golden
	if err := json.Unmarshal(b, &g); err != nil {
		t.Fatal(err)
	}
	return g
}

// Every layout text gets the same verdict, the same message and the same
// bindings as the Python tool.
func TestLayoutParityWithPython(t *testing.T) {
	for _, c := range loadGolden(t).Cases {
		t.Run(c.Label, func(t *testing.T) {
			lay, err := ParseLayout([]byte(c.Text))
			if !c.OK {
				if err == nil {
					t.Fatalf("accepted; Python refuses with %q", c.Error)
				}
				if err.Error() != c.Error {
					t.Fatalf("message differs\n go:     %s\n python: %s", err, c.Error)
				}
				return
			}
			if err != nil {
				t.Fatalf("refused (%v); Python accepts", err)
			}
			if len(lay.Binds) != len(c.Native) {
				t.Fatalf("%d binds, Python %d", len(lay.Binds), len(c.Native))
			}
			for i, b := range lay.Binds {
				want := c.Native[i]
				kind, n := "BUTTON", b.Input.N
				if b.Input.Axis {
					kind = "AXIS"
				}
				if want[0] != b.Action || want[1] != kind || int(want[2].(float64)) != n {
					t.Fatalf("bind %d: go %v, python %v", i, b, want)
				}
				if b.Input.Axis && want[3].(bool) != b.Input.Positive {
					t.Fatalf("bind %d direction differs", i)
				}
			}
			sl := lay.WheelSlices()
			if len(sl) != len(c.Wheel) {
				t.Fatalf("wheel has %d slices, Python %d", len(sl), len(c.Wheel))
			}
			for i, s := range sl {
				if s.Key != c.Wheel[i][0] || s.Label != c.Wheel[i][1] {
					t.Fatalf("slice %d: go %v, python %v", i, s, c.Wheel[i])
				}
			}
		})
	}
}

func TestWheelScaleAndResolutionParity(t *testing.T) {
	g := loadGolden(t)
	for _, s := range g.WheelScale {
		got, err := WheelScale(s[0], s[1])
		if err != nil || got != s[2] {
			t.Errorf("%dx%d: got %d (%v), python %d", s[0], s[1], got, err, s[2])
		}
	}
	for _, r := range g.Resolution {
		text, ok := r[0].(string), r[1].(bool)
		w, h, err := ParseResolution(text)
		if ok {
			want := r[2].([]any)
			if err != nil || w != int(want[0].(float64)) || h != int(want[1].(float64)) {
				t.Errorf("%q: got %dx%d (%v), python %v", text, w, h, err, want)
			}
		} else if err == nil || err.Error() != r[2].(string) {
			t.Errorf("%q: got %v, python %q", text, err, r[2])
		}
	}
}

// The macro policy does not rest on the golden file alone: each forbidden shape
// is tried here and must be refused.
func TestMacroPolicyRefused(t *testing.T) {
	bad := map[string]string{
		"turbo":      `{"format":1,"binds":{"KEY_A":{"button":0,"turbo":true}},"wheel":["codex","incubator","trainer","friendlist","tradelink","hotbar6","hotbar7","hotbar8","hotbar9","hidegui"]}`,
		"two inputs": `{"format":1,"binds":{"KEY_A":[{"button":0},{"button":1}]},"wheel":["codex","incubator","trainer","friendlist","tradelink","hotbar6","hotbar7","hotbar8","hotbar9","hidegui"]}`,
		"sequence":   `{"format":1,"binds":{},"sequence":["KEY_A","KEY_B"],"wheel":["codex","incubator","trainer","friendlist","tradelink","hotbar6","hotbar7","hotbar8","hotbar9","hidegui"]}`,
		"delay":      `{"format":1,"binds":{"KEY_A":{"button":0,"delay":10}},"wheel":["codex","incubator","trainer","friendlist","tradelink","hotbar6","hotbar7","hotbar8","hotbar9","hidegui"]}`,
		"shared":     `{"format":1,"binds":{"KEY_A":{"button":0},"KEY_B":{"button":0}},"wheel":["codex","incubator","trainer","friendlist","tradelink","hotbar6","hotbar7","hotbar8","hotbar9","hidegui"]}`,
	}
	for name, text := range bad {
		if _, err := ParseLayout([]byte(text)); err == nil {
			t.Errorf("%s was accepted", name)
		}
	}
}

func TestDefaultLayoutIsValidAndComplete(t *testing.T) {
	d := DefaultLayout()
	if len(d.Binds) != len(actionOrder) || len(d.Wheel) != len(wheelActions) {
		t.Fatal("default layout is incomplete")
	}
	seen := map[Input]bool{}
	for _, b := range d.Binds {
		if seen[b.Input] {
			t.Fatalf("%s shares an input", b.Action)
		}
		seen[b.Input] = true
	}
}

func TestLayoutCheckCommand(t *testing.T) {
	dir := t.TempDir()
	good, bad := filepath.Join(dir, "good.json"), filepath.Join(dir, "bad.json")
	g := loadGolden(t)
	for _, c := range g.Cases {
		switch c.Label {
		case "default":
			os.WriteFile(good, []byte(c.Text), 0o600)
		case "turbo field":
			os.WriteFile(bad, []byte(c.Text), 0o600)
		}
	}
	var out, errw bytes.Buffer
	if code := runLayout([]string{"check", good}, &out, &errw); code != 0 {
		t.Fatalf("good layout: exit %d: %s", code, errw.String())
	}
	out.Reset()
	errw.Reset()
	if code := runLayout([]string{"check", bad}, &out, &errw); code != 1 || errw.Len() == 0 {
		t.Fatalf("turbo layout: exit %d, stderr %q", code, errw.String())
	}
	if code := runLayout([]string{"check"}, &out, &errw); code != 2 {
		t.Fatalf("no file: exit %d", code)
	}
	if code := runLayout([]string{"check", filepath.Join(dir, "missing.json")}, &out, &errw); code != 1 {
		t.Fatalf("missing file: exit %d", code)
	}
}
