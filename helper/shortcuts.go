package main

// Steam's shortcuts.vdf (binary VDF) and the "PokeMMO" non-Steam shortcut, the same way
// tools/install_wheel.py reads and writes them. tests/golden/shortcuts-parity.json holds what the
// Python tool does; shortcuts_test.go replays it.

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"hash/crc32"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

const shortcutName = "PokeMMO"

// Value types in a binary VDF. Kinds this tool does not edit (float, 64-bit ints) are kept as raw bytes.
const (
	bvkMap  byte = 0
	bvkStr  byte = 1
	bvkInt  byte = 2
	bvkEnd  byte = 8
	bvkEnd2 byte = 11
)

var bvRawSizes = map[byte]int{3: 4, 7: 8, 10: 8}

// bvValue is one value. Strings keep their bytes as they were (they need not be UTF-8).
type bvValue struct {
	kind byte
	str  string
	num  int32
	raw  []byte
	m    *bvMap
}

// bvMap keeps the keys in file order; setting a key that is there keeps its place.
type bvMap struct {
	keys []string
	vals map[string]*bvValue
}

func newBvMap() *bvMap { return &bvMap{vals: map[string]*bvValue{}} }

func (m *bvMap) get(k string) (*bvValue, bool) {
	v, ok := m.vals[k]
	return v, ok
}

func (m *bvMap) set(k string, v *bvValue) {
	if _, ok := m.vals[k]; !ok {
		m.keys = append(m.keys, k)
	}
	m.vals[k] = v
}

func bvS(s string) *bvValue { return &bvValue{kind: bvkStr, str: s} }
func bvI(n int32) *bvValue  { return &bvValue{kind: bvkInt, num: n} }

var errBvdf = errors.New("unexpected layout")

const bvMaxDepth = 64

func bvCstr(b []byte, i int) (string, int, error) {
	if i > len(b) {
		return "", 0, errBvdf
	}
	j := bytes.IndexByte(b[i:], 0)
	if j < 0 {
		return "", 0, errBvdf
	}
	return string(b[i : i+j]), i + j + 1, nil
}

func parseBvdf(b []byte, i, depth int) (*bvMap, int, error) {
	if depth > bvMaxDepth {
		return nil, 0, errBvdf
	}
	m := newBvMap()
	for {
		if i >= len(b) {
			return nil, 0, errBvdf
		}
		t := b[i]
		i++
		if t == bvkEnd || t == bvkEnd2 {
			return m, i, nil
		}
		k, ni, err := bvCstr(b, i)
		if err != nil {
			return nil, 0, err
		}
		i = ni
		switch {
		case t == bvkMap:
			sub, ni, err := parseBvdf(b, i, depth+1)
			if err != nil {
				return nil, 0, err
			}
			m.set(k, &bvValue{kind: bvkMap, m: sub})
			i = ni
		case t == bvkStr:
			s, ni, err := bvCstr(b, i)
			if err != nil {
				return nil, 0, err
			}
			m.set(k, bvS(s))
			i = ni
		case t == bvkInt:
			if i+4 > len(b) {
				return nil, 0, errBvdf
			}
			m.set(k, bvI(int32(binary.LittleEndian.Uint32(b[i:]))))
			i += 4
		default:
			n, ok := bvRawSizes[t]
			if !ok || i+n > len(b) {
				return nil, 0, errBvdf
			}
			m.set(k, &bvValue{kind: t, raw: append([]byte(nil), b[i:i+n]...)})
			i += n
		}
	}
}

func dumpBvdf(m *bvMap) []byte {
	var out []byte
	for _, k := range m.keys {
		v := m.vals[k]
		kb := append([]byte(k), 0)
		switch v.kind {
		case bvkMap:
			out = append(append(append(out, bvkMap), kb...), dumpBvdf(v.m)...)
		case bvkStr:
			out = append(append(append(append(out, bvkStr), kb...), v.str...), 0)
		case bvkInt:
			out = append(append(out, bvkInt), kb...)
			out = binary.LittleEndian.AppendUint32(out, uint32(v.num))
		default:
			out = append(append(append(out, v.kind), kb...), v.raw...)
		}
	}
	return append(out, bvkEnd)
}

// readShortcuts reads shortcuts.vdf into its "shortcuts" map. A file it could not write back
// byte for byte is refused, so nothing it does not understand is lost.
func readShortcuts(data []byte) (*bvMap, error) {
	top, end, err := parseBvdf(data, 0, 0)
	if err != nil {
		return nil, err
	}
	sc, ok := top.get("shortcuts")
	if !ok || sc.kind != bvkMap {
		return nil, errBvdf
	}
	if string(dumpBvdf(top))+string(data[end:]) != string(data) {
		return nil, errBvdf
	}
	return sc.m, nil
}

func writeShortcuts(sc *bvMap) []byte {
	out := append([]byte{bvkMap}, "shortcuts\x00"...)
	return append(append(out, dumpBvdf(sc)...), bvkEnd)
}

// shortcutField is AppName (or appname, as older Steam wrote it) and the like.
func shortcutField(m *bvMap, name string) (*bvValue, bool) {
	if v, ok := m.get(name); ok {
		return v, true
	}
	return m.get(strings.ToLower(name))
}

func isPokemmoShortcut(v *bvValue) bool {
	if v == nil || v.kind != bvkMap {
		return false
	}
	n, ok := shortcutField(v.m, "AppName")
	return ok && n.kind == bvkStr && n.str == shortcutName
}

func bvNumericKey(k string) (int, bool) {
	if k == "" {
		return 0, false
	}
	for _, c := range k {
		if c < '0' || c > '9' {
			return 0, false
		}
	}
	n, err := strconv.Atoi(k)
	return n, err == nil
}

func nextKey(sc *bvMap) string {
	best := -1
	for _, k := range sc.keys {
		if n, ok := bvNumericKey(k); ok && n > best {
			best = n
		}
	}
	return strconv.Itoa(best + 1)
}

// bvIdent is what makes two shortcuts the same one: appid, name and program.
func bvIdent(m *bvMap) string {
	var b strings.Builder
	for _, f := range []string{"appid", "AppName", "Exe"} {
		if v, ok := shortcutField(m, f); ok {
			one := newBvMap()
			one.set("v", v)
			b.Write(dumpBvdf(one))
		} else {
			b.WriteString("\xffnone")
		}
		b.WriteByte(0xfe)
	}
	return b.String()
}

func bvDisplay(v *bvValue, ok bool) string {
	switch {
	case !ok:
		return "None"
	case v.kind == bvkStr:
		return v.str
	case v.kind == bvkInt:
		return strconv.Itoa(int(v.num))
	}
	return "?"
}

// restoreLostShortcuts puts back shortcuts from the backup that are gone: up to v1.0.0 the PokeMMO
// shortcut could overwrite another one. Returns the names restored.
func restoreLostShortcuts(sc, old *bvMap) []string {
	ids := map[string]bool{}
	for _, k := range sc.keys {
		if v := sc.vals[k]; v.kind == bvkMap {
			ids[bvIdent(v.m)] = true
		}
	}
	var names []string
	for _, k := range old.keys {
		v := old.vals[k]
		if v.kind != bvkMap || isPokemmoShortcut(v) || ids[bvIdent(v.m)] {
			continue
		}
		if _, taken := sc.get(k); taken {
			sc.set(nextKey(sc), v)
		} else {
			sc.set(k, v)
		}
		names = append(names, bvDisplay(shortcutField(v.m, "AppName")))
	}
	if len(names) > 0 { // keep Steam's numeric order
		order := func(k string) int {
			if n, ok := bvNumericKey(k); ok {
				return n
			}
			return 1 << 30
		}
		sort.SliceStable(sc.keys, func(a, b int) bool { return order(sc.keys[a]) < order(sc.keys[b]) })
	}
	return names
}

// newShortcut is the "PokeMMO" non-Steam shortcut for a program, with Steam's appid for it.
func newShortcut(exe, startDir, options string) (*bvMap, uint32) {
	appid := crc32.ChecksumIEEE([]byte(exe+shortcutName)) | 0x80000000
	icon := ""
	if strings.HasSuffix(exe, `.exe"`) {
		icon = strings.Trim(exe, `"`)
	}
	m := newBvMap()
	m.set("appid", bvI(int32(appid)))
	m.set("AppName", bvS(shortcutName))
	m.set("Exe", bvS(exe))
	m.set("StartDir", bvS(startDir))
	m.set("icon", bvS(icon))
	m.set("ShortcutPath", bvS(""))
	m.set("LaunchOptions", bvS(options))
	for _, k := range []string{"IsHidden", "AllowDesktopConfig", "AllowOverlay", "OpenVR", "Devkit"} {
		n := int32(0)
		if k == "AllowDesktopConfig" || k == "AllowOverlay" {
			n = 1
		}
		m.set(k, bvI(n))
	}
	m.set("DevkitGameID", bvS(""))
	m.set("DevkitOverrideAppID", bvI(0))
	m.set("LastPlayTime", bvI(0))
	m.set("FlatpakAppID", bvS(""))
	m.set("sortas", bvS(""))
	m.set("tags", &bvValue{kind: bvkMap, m: newBvMap()})
	return m, appid
}

func stateTruthy(v any) bool {
	switch x := v.(type) {
	case nil:
		return false
	case string:
		return x != ""
	case bool:
		return x
	case fmt.Stringer: // json.Number
		return x.String() != "0" && x.String() != ""
	}
	return true
}

// shortcutPlan adds the PokeMMO shortcut to one Steam user's shortcuts.vdf (exe, startDir and
// options come from the platform code), as tools/install_wheel.py shortcut_plan does.
func shortcutPlan(p *Plan, userdir, exe, startDir, options string) {
	path := filepath.Join(userdir, "config", "shortcuts.vdf")
	data, _ := p.current(path)
	added, _ := p.state["shortcuts_added"].([]any)
	if added == nil {
		added = []any{}
	}
	p.state["shortcuts_added"] = added
	legacy := !stateTruthy(p.state["version"]) && !p.Fresh // installed by a version without a record
	bak, _ := readBytes(backupPath(path))
	sc, old := newBvMap(), newBvMap()
	var err error
	if len(data) > 0 {
		sc, err = readShortcuts(data)
	}
	if err == nil && len(bak) > 0 { // an empty backup holds no shortcuts
		old, err = readShortcuts(bak)
	}
	if err != nil {
		p.Notes = append(p.Notes, fmt.Sprintf("Could not read %s; add PokeMMO to Steam by hand (Add a Non-Steam Game).", path))
		return
	}
	if legacy {
		if lost := restoreLostShortcuts(sc, old); len(lost) > 0 {
			p.put(path, writeShortcuts(sc), true)
			p.Notes = append(p.Notes, "Restored Steam shortcuts an older version overwrote: "+strings.Join(lost, ", "))
		}
	}
	has := func(m *bvMap) bool {
		for _, k := range m.keys {
			if isPokemmoShortcut(m.vals[k]) {
				return true
			}
		}
		return false
	}
	if has(sc) {
		if legacy && !containsAny(added, path) && !has(old) {
			p.state["shortcuts_added"] = append(added, path) // the older version added it
		}
		return
	}
	entry, appid := newShortcut(exe, startDir, options)
	sc.set(nextKey(sc), &bvValue{kind: bvkMap, m: entry})
	p.put(path, writeShortcuts(sc), true)
	if !containsAny(added, path) {
		p.state["shortcuts_added"] = append(added, path)
	}
	p.Notes = append(p.Notes, fmt.Sprintf("Steam shortcut %s (appid %d) in %s", shortcutName, appid, path))
}
