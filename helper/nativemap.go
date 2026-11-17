package main

import (
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

// The pad map PokeMMO keeps in main.properties: one entry per controller name. This file is
// the pure part of tools/apply_native.py (names, entries, "is this entry ours"); the part that
// plans and writes the file comes with the install record.

var xboxNames = []string{"Xbox Series X Controller", "Xbox One S Controller", "Xbox One Controller",
	"Xbox One Elite Controller", "Xbox One Elite 2 Controller", "Xbox 360 Controller",
	"Xbox 360 Wireless Controller", "Xbox Wireless Controller", "Xbox Adaptive Controller",
	"XInput Controller", "Microsoft X-Box 360 pad", "Microsoft X-Box One pad"}
var playstationNames = []string{"PS5 Controller", "DualSense Wireless Controller",
	"DualSense Edge Wireless Controller", "PS4 Controller",
	"DUALSHOCK 4 Wireless Controller", "Sony Interactive Entertainment Wireless Controller",
	"Wireless Controller"}
var nintendoNames = []string{"Nintendo Switch Pro Controller", "Pro Controller", "Nintendo Switch 2 Pro Controller"}
var steamNames = []string{"#SettingsController_SteamController", "Steam Virtual Gamepad", "Steam Controller",
	"Steam Deck", "Steam Deck Controller"}

// controllerNames is every pad name the map is written under.
func controllerNames() []string {
	var out []string
	for _, l := range [][]string{xboxNames, playstationNames, nintendoNames, steamNames} {
		out = append(out, l...)
	}
	return out
}

// nintendoSwap: on a Nintendo pad the printed A is on the right, so the face buttons swap in pairs.
var nintendoSwap = map[int]int{0: 1, 1: 0, 2: 3, 3: 2}

func isNintendo(name string) bool {
	return strings.Contains(strings.ToLower(name), "nintendo") || name == "Pro Controller"
}

func bindParts(binds []Bind) []string {
	var out []string
	for _, b := range binds {
		if b.Input.Axis {
			out = append(out, b.Action+",AXIS,"+strconv.Itoa(b.Input.N)+","+strconv.FormatBool(b.Input.Positive))
		} else {
			out = append(out, b.Action+",BUTTON,"+strconv.Itoa(b.Input.N))
		}
	}
	return out
}

// nintendoBinds moves every face-button action to the button with the same printed letter.
func nintendoBinds(binds []Bind) []Bind {
	out := make([]Bind, len(binds))
	for i, b := range binds {
		if s, ok := nintendoSwap[b.Input.N]; ok && !b.Input.Axis {
			b.Input.N = s
		}
		out[i] = b
	}
	return out
}

// nintendoFaceActionsOnly is what the first remap-screen code wrote: only KEY_A..KEY_Y moved.
func nintendoFaceActionsOnly(binds []Bind) []Bind {
	out := make([]Bind, len(binds))
	for i, b := range binds {
		if s, ok := nintendoSwap[b.Input.N]; ok && !b.Input.Axis &&
			(b.Action == "KEY_A" || b.Action == "KEY_B" || b.Action == "KEY_X" || b.Action == "KEY_Y") {
			b.Input.N = s
		}
		out[i] = b
	}
	return out
}

// encodeOne is the map entry for one pad name; binds nil means the shipped default.
func encodeOne(name string, nintendoLabels bool, binds []Bind) string {
	if binds == nil {
		binds = DefaultLayout().Binds
	}
	if nintendoLabels && isNintendo(name) {
		binds = nintendoBinds(binds)
	}
	return strings.Join(append([]string{escape(name)}, bindParts(binds)...), ";")
}

// partSet is a set of bind parts as one comparable key.
func partSet(parts []string) string {
	seen := map[string]bool{}
	var u []string
	for _, p := range parts {
		if !seen[p] {
			seen[p] = true
			u = append(u, p)
		}
	}
	sort.Strings(u)
	return strings.Join(u, "\n")
}

// layoutSets are the forms of a layout this project writes: positional, labels on Nintendo
// pads, and the older labels form.
func layoutSets(binds []Bind) map[string]bool {
	return map[string]bool{
		partSet(bindParts(binds)):                          true,
		partSet(bindParts(nintendoBinds(binds))):           true,
		partSet(bindParts(nintendoFaceActionsOnly(binds))): true,
	}
}

// legacyBinds: v1.0.0 to v1.1.1 put the Focus Ring on View and Hotbar 5 on LB.
func legacyBinds() []Bind {
	b := DefaultLayout().Binds
	for i := range b {
		switch b[i].Action {
		case "KEY_RING_FOCUS":
			b[i].Input = Input{N: 4}
		case "KEY_HOTBAR_5":
			b[i].Input = Input{N: 9}
		}
	}
	return b
}

func ourLayouts() map[string]bool {
	out := layoutSets(DefaultLayout().Binds)
	for k := range layoutSets(legacyBinds()) {
		out[k] = true
	}
	return out
}

// isOurs: the entry is exactly one of this project's layouts, in any order. extra holds the
// layoutSets of the player's custom layout.
func isOurs(entry string, extra map[string]bool) bool {
	var parts []string
	for _, p := range strings.Split(entry, ";")[1:] {
		if p != "" {
			parts = append(parts, p)
		}
	}
	k := partSet(parts)
	return ourLayouts()[k] || extra[k]
}

// mapEntry is one entry of the map, keyed by the pad name it holds.
type mapEntry struct{ Name, Entry string }

// splitEntries reads the map value: entries are split on a `|` that is not escaped. A name
// seen twice keeps its first position and its last entry.
func splitEntries(value string) []mapEntry {
	var out []mapEntry
	if value == "" {
		return out
	}
	idx := map[string]int{}
	add := func(e string) {
		name := unescape(strings.SplitN(e, ";", 2)[0])
		if name == "" {
			return
		}
		if i, ok := idx[name]; ok {
			out[i].Entry = e
			return
		}
		idx[name] = len(out)
		out = append(out, mapEntry{name, e})
	}
	start := 0
	for i := 0; i < len(value); i++ {
		if value[i] == '|' && (i == 0 || value[i-1] != '\\') {
			add(value[start:i])
			start = i + 1
		}
	}
	add(value[start:])
	return out
}

var logLine = regexp.MustCompile(`Controller (.+?) \( ax [0-9]+ btn [0-9]+\) .*attached`)

// loggedNamesIn lists the pad names a log says were attached, first sighting first.
func loggedNamesIn(text string, names []string) []string {
	for _, m := range logLine.FindAllStringSubmatch(text, -1) {
		dup := false
		for _, n := range names {
			if n == m[1] {
				dup = true
				break
			}
		}
		if !dup {
			names = append(names, m[1])
		}
	}
	return names
}

// validUTF8 replaces each undecodable byte with U+FFFD, as Python's errors="replace" does.
func validUTF8(b []byte) string {
	var sb strings.Builder
	for len(b) > 0 {
		r, n := utf8.DecodeRune(b)
		if r == utf8.RuneError && n == 1 {
			sb.WriteRune(utf8.RuneError)
		} else {
			sb.Write(b[:n])
		}
		b = b[n:]
	}
	return sb.String()
}

// loggedNames: pad names PokeMMO logged as attached on this machine (the *.log files of the
// data folder's log directory, in name order). An unreadable file is skipped.
func loggedNames(pokemmo string) []string {
	files, _ := filepath.Glob(filepath.Join(pokemmo, "log", "*.log"))
	sort.Strings(files)
	names := []string{}
	for _, f := range files {
		b, err := os.ReadFile(f)
		if err != nil {
			continue
		}
		names = loggedNamesIn(validUTF8(b), names)
	}
	return names
}
