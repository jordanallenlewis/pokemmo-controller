package main

import (
	"path/filepath"
	"strconv"
	"strings"
)

// keyboardBinds are the libGDX key codes PokeMMO stores in main.properties for the wheel's
// ten keys, in the order the Python tool writes them (tools/install_wheel.py KEYBOARD_BINDS).
var keyboardBinds = []struct {
	Key  string
	Code int
}{
	{"client.controls.gdx.codex", 42}, {"client.controls.gdx.incubator", 37},
	{"client.controls.gdx.trainer", 31}, {"client.controls.gdx.friendlist", 50},
	{"client.controls.gdx.tradelink", 44}, {"client.controls.gdx.hidegui", 142},
	{"client.controls.gdx.hotbar6", 13}, {"client.controls.gdx.hotbar7", 14},
	{"client.controls.gdx.hotbar8", 15}, {"client.controls.gdx.hotbar9", 16},
}

// propsPlan schedules the keyboard binds in config/main.properties, keeping every other line
// and the file's line endings.
func propsPlan(p *Plan, pokemmo string) {
	path := filepath.Join(pokemmo, "config", "main.properties")
	data, _ := p.current(path)
	text, nl := decode(data)
	lines, final := splitLines(text)
	keys := make([]string, 0, len(keyboardBinds))
	want := map[string]*string{}
	for _, b := range keyboardBinds {
		v := strconv.Itoa(b.Code)
		keys = append(keys, b.Key)
		want[b.Key] = &v
	}
	lines = setProps(lines, keys, want)
	p.put(path, encode(joinLines(lines, final), nl), true)
}

// shortcutTarget returns the Steam non-Steam-game shortcut (exe, start dir, launch options) for
// this system. goos is runtime.GOOS; exists tells whether a path is there (the macOS app is in
// /Applications or in the user's own Applications folder).
func shortcutTarget(goos, pokemmo, home string, exists func(string) bool) (string, string, string) {
	switch goos {
	case "windows":
		return `"` + pokemmo + `\PokeMMO.exe"`, `"` + pokemmo + `\"`, ""
	case "darwin":
		app := "/Applications/PokeMMO.app"
		if !exists(app) {
			app = home + "/Applications/PokeMMO.app"
		}
		return `"` + app + `"`, `"` + app[:strings.LastIndex(app, "/")] + `/"`, ""
	}
	if strings.Contains(pokemmo, ".var/app/com.pokemmo.PokeMMO") {
		return `"/usr/bin/flatpak"`, `"/usr/bin/"`, "run com.pokemmo.PokeMMO"
	}
	if strings.Contains(pokemmo, "snap/pokemmo") {
		return `"/snap/bin/pokemmo"`, `"/snap/bin/"`, ""
	}
	return `"` + pokemmo + `/PokeMMO.sh"`, `"` + pokemmo + `/"`, ""
}
