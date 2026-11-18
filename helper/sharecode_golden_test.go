package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// spec/golden/share-code.json holds PMC1 share codes made by this Go code for every layout the
// parity golden accepts (FOUNDATION 3.3: the PMC1 form is locked). The Rust port must produce
// the same codes and read them back to the same layouts. Refresh after a deliberate change with:
//
//	PMC_WRITE_SPEC=1 go test -run ShareCodeVectors
type shareVector struct {
	Label  string          `json:"label"`
	Layout json.RawMessage `json:"layout"`
	Code   string          `json:"code"`
}

func shareVectorsPath() string {
	return filepath.Join("..", "spec", "golden", "share-code.json")
}

func buildShareVectors(t *testing.T) []byte {
	t.Helper()
	var out []shareVector
	for _, c := range loadGolden(t).Cases {
		if !c.OK {
			continue
		}
		l, err := ParseLayout([]byte(c.Text))
		if err != nil {
			t.Fatalf("%s: %v", c.Label, err)
		}
		out = append(out, shareVector{Label: c.Label, Layout: json.RawMessage(l.JSON()), Code: l.ShareCode()})
	}
	doc := map[string]any{"schema": "pmc.golden.share-code/1", "vectors": out}
	b, err := json.MarshalIndent(doc, "", " ")
	if err != nil {
		t.Fatal(err)
	}
	return append(b, '\n')
}

func TestShareCodeVectors(t *testing.T) {
	want := buildShareVectors(t)
	if os.Getenv("PMC_WRITE_SPEC") != "" {
		if err := os.WriteFile(shareVectorsPath(), want, 0o644); err != nil {
			t.Fatal(err)
		}
		return
	}
	have, err := os.ReadFile(shareVectorsPath())
	if err != nil {
		t.Fatal(err)
	}
	have = bytes.ReplaceAll(have, []byte("\r\n"), []byte("\n"))
	if !bytes.Equal(have, want) {
		t.Fatal("spec/golden/share-code.json is stale: run PMC_WRITE_SPEC=1 go test -run ShareCodeVectors")
	}
	// And every code in the file reads back to its layout.
	var doc struct {
		Vectors []shareVector `json:"vectors"`
	}
	if err := json.Unmarshal(have, &doc); err != nil {
		t.Fatal(err)
	}
	if len(doc.Vectors) < 6 {
		t.Fatalf("only %d vectors", len(doc.Vectors))
	}
	for _, v := range doc.Vectors {
		l, err := ParseShareCode(v.Code)
		if err != nil {
			t.Fatalf("%s: %v", v.Label, err)
		}
		// the code carries binds and the wheel only, not the name
		if stripName(l.JSON()) != stripName(v.Layout) {
			t.Fatalf("%s: code reads back to a different layout", v.Label)
		}
	}
}

func stripName(b []byte) string {
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		return err.Error()
	}
	delete(m, "name")
	out, _ := json.Marshal(m)
	return string(out)
}
