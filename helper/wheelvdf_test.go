package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type wheelVdfGolden struct {
	OurBlock string `json:"our_block"`
	Empty    string `json:"empty_configset"`
	Layouts  []struct {
		Label string     `json:"label"`
		Type  string     `json:"type"`
		Wheel [][]string `json:"wheel"`
		Scale *int       `json:"scale"`
		Text  string     `json:"text"`
	} `json:"layouts"`
	Configsets []struct {
		Label  string `json:"label"`
		Text   string `json:"text"`
		OK     bool   `json:"ok"`
		Result string `json:"result"`
	} `json:"configsets"`
}

func loadWheelVdf(t *testing.T) wheelVdfGolden {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("..", "tests", "golden", "wheelvdf-parity.json"))
	if err != nil {
		t.Fatal(err)
	}
	var g wheelVdfGolden
	if err := json.Unmarshal(b, &g); err != nil {
		t.Fatal(err)
	}
	return g
}

func TestWheelVdfParityWithPython(t *testing.T) {
	g := loadWheelVdf(t)
	if g.OurBlock != ourBlock || g.Empty != emptyConfig {
		t.Fatal("block constants differ from Python")
	}
	for _, c := range g.Layouts {
		t.Run(c.Label, func(t *testing.T) {
			var wheel []Slice
			if c.Wheel != nil {
				for _, s := range c.Wheel {
					wheel = append(wheel, Slice{s[0], s[1]})
				}
			} else {
				wheel = DefaultLayout().WheelSlices()
			}
			scale := 0
			if c.Scale != nil {
				scale = *c.Scale
			}
			if got := BuildWheelLayout(c.Type, wheel, scale); got != c.Text {
				t.Fatalf("layout text differs from Python\n got:  %q\n want: %q", got, c.Text)
			}
		})
	}
}

func TestConfigsetParityWithPython(t *testing.T) {
	for _, c := range loadWheelVdf(t).Configsets {
		t.Run(c.Label, func(t *testing.T) {
			got, err := ConfigsetWithBlock(c.Text, ourBlock)
			if c.OK != (err == nil) {
				t.Fatalf("ok=%v want %v (err %v)", err == nil, c.OK, err)
			}
			if c.OK && got != c.Result {
				t.Fatalf("differs\n got:  %q\n want: %q", got, c.Result)
			}
			if !c.OK && err.Error() != c.Result {
				t.Fatalf("message %q want %q", err, c.Result)
			}
		})
	}
}

// The shipped steam/*.vdf files are what the Go builder writes by default.
func TestShippedVdfMatchGo(t *testing.T) {
	for _, ct := range controllerTypes {
		want, err := os.ReadFile(filepath.Join("..", "steam", ct+".vdf"))
		if err != nil {
			t.Fatal(err)
		}
		got := BuildWheelLayout(ct, DefaultLayout().WheelSlices(), 0)
		// a Windows checkout may turn line ends into CRLF
		if got != strings.ReplaceAll(string(want), "\r\n", "\n") {
			t.Fatalf("%s differs from steam/%s.vdf", ct, ct)
		}
	}
}
