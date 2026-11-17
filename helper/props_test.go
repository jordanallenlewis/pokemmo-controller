package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
)

type propsGolden struct {
	Split []struct {
		Text   string   `json:"text"`
		Lines  []string `json:"lines"`
		Final  bool     `json:"final"`
		Joined string   `json:"joined"`
	} `json:"split"`
	Keys []struct {
		Line  string  `json:"line"`
		Key   *string `json:"key"`
		Value *string `json:"value"`
	} `json:"keys"`
	Get []struct {
		Text  string  `json:"text"`
		Key   string  `json:"key"`
		Value *string `json:"value"`
	} `json:"get"`
	Set []struct {
		Text string             `json:"text"`
		Want map[string]*string `json:"want"`
		Out  string             `json:"out"`
	} `json:"set"`
	Escape []struct {
		Value   string `json:"value"`
		Escaped string `json:"escaped"`
		Back    string `json:"back"`
	} `json:"escape"`
	Unescape []struct {
		Raw   string `json:"raw"`
		Value string `json:"value"`
	} `json:"unescape"`
}

func loadProps(t *testing.T) propsGolden {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("..", "tests", "golden", "props-parity.json"))
	if err != nil {
		t.Fatal(err)
	}
	var g propsGolden
	if err := json.Unmarshal(b, &g); err != nil {
		t.Fatal(err)
	}
	return g
}

func TestPropsMatchPython(t *testing.T) {
	g := loadProps(t)
	for _, c := range g.Split {
		lines, final := splitLines(c.Text)
		if len(lines) == 0 {
			lines = []string{}
		}
		if !reflect.DeepEqual(lines, c.Lines) && !(len(lines) == 0 && len(c.Lines) == 0) {
			t.Errorf("split %q: %q want %q", c.Text, lines, c.Lines)
		}
		if final != c.Final || joinLines(lines, final) != c.Joined {
			t.Errorf("split/join %q: final %v joined %q", c.Text, final, joinLines(lines, final))
		}
	}
	for _, c := range g.Keys {
		k, ok := lineKey(c.Line)
		if ok != (c.Key != nil) || (ok && (k != *c.Key || lineValue(c.Line) != *c.Value)) {
			t.Errorf("key of %q: %q %v want %v", c.Line, k, ok, c.Key)
		}
	}
	for _, c := range g.Get {
		lines, _ := splitLines(c.Text)
		v, ok := getProp(lines, c.Key)
		if ok != (c.Value != nil) || (ok && v != *c.Value) {
			t.Errorf("get %q in %q: %q %v want %v", c.Key, c.Text, v, ok, c.Value)
		}
	}
	for _, c := range g.Set {
		lines, final := splitLines(c.Text)
		var keys []string
		for k := range c.Want {
			keys = append(keys, k)
		}
		sort.Strings(keys) // the golden wants use one new key at most, so order is not in play
		if got := joinLines(setProps(lines, keys, c.Want), final); got != c.Out {
			t.Errorf("set %v in %q: %q want %q", c.Want, c.Text, got, c.Out)
		}
	}
	for _, c := range g.Escape {
		if e := escape(c.Value); e != c.Escaped {
			t.Errorf("escape %q: %q want %q", c.Value, e, c.Escaped)
		}
		if u := unescape(c.Escaped); u != c.Back {
			t.Errorf("unescape %q: %q want %q", c.Escaped, u, c.Back)
		}
	}
	for _, c := range g.Unescape {
		if u := unescape(c.Raw); u != c.Value {
			t.Errorf("unescape %q: %q want %q", c.Raw, u, c.Value)
		}
	}
}

func TestDecodeKeepsLineEndings(t *testing.T) {
	text, nl := decode([]byte("a=1\r\nb=2\r\n"))
	if text != "a=1\nb=2\n" || nl != "\r\n" || string(encode(text, nl)) != "a=1\r\nb=2\r\n" {
		t.Fatalf("%q %q", text, nl)
	}
}
