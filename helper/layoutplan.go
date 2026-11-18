package main

// The wheel layout files for one Steam account and the configset entry that picks them, the same
// way tools/install_wheel.py layout_plan does. tests/golden/layoutplan-parity.json holds what the
// Python tool plans; layoutplan_test.go replays it.

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// steamUserdirs lists the Steam account folders under userdata ("0" is not an account), in name order.
func steamUserdirs(steam string) []string {
	entries, err := os.ReadDir(filepath.Join(steam, "userdata"))
	if err != nil {
		return nil
	}
	var out []string
	for _, e := range entries { // os.ReadDir sorts by name
		if n := e.Name(); n != "0" && isASCIIDigits(n) {
			out = append(out, filepath.Join(steam, "userdata", n))
		}
	}
	return out
}

func isASCIIDigits(s string) bool {
	if s == "" {
		return false
	}
	for _, c := range s {
		if c < '0' || c > '9' {
			return false
		}
	}
	return true
}

// layoutPlan plans the layout text for each pad type in layouts and our entry in that type's
// configset. A layout Steam saved for a "PokeMMO" shortcut before, or a configset that already
// picks ours, is not kept as the original.
func layoutPlan(p *Plan, steam, account string, layouts map[string]string) {
	cfg := filepath.Join(steam, "steamapps", "common", "Steam Controller Configs", account, "config")
	for _, ctype := range controllerTypes {
		text, ok := layouts[ctype]
		if !ok {
			continue
		}
		f := filepath.Join(cfg, configDirName, ctype+".vdf")
		cur, exists := p.current(f)
		p.put(f, encode(text, "\n"), !exists || !bytes.Contains(cur, []byte(layoutTitle)))
		cs := filepath.Join(cfg, "configset_"+ctype+".vdf")
		textCS, nl := emptyConfig, "\n"
		if data, exists := p.current(cs); exists {
			textCS, nl = decode(data)
		}
		updated, err := ConfigsetWithBlock(textCS, ourBlock)
		if err != nil {
			p.Notes = append(p.Notes, fmt.Sprintf("Could not read %s; pick the PokeMMO layout in Steam by hand.", cs))
			continue
		}
		p.put(cs, encode(updated, nl), !strings.Contains(textCS, ourBlock))
	}
}
