package main

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"unicode"
)

// The Steam Input wheel layout and the Steam config set edit: the same bytes
// tools/install_wheel.py writes (tests/golden/wheelvdf-parity.json).

const (
	configDirName = "pokemmo"
	layoutTitle   = "PokeMMO - native + right-stick wheel"
	ourBlock      = "\t\"" + configDirName + "\"\n\t{\n\t\t\"autosave\"\t\t\"1\"\n\t}\n"
	emptyConfig   = "\"controller_config\"\n{\n}\n"
)

// controllerTypes are the Steam Input pad types that get the layout.
var controllerTypes = []string{"controller_xboxone", "controller_xbox360", "controller_ps5",
	"controller_ps4", "controller_switch_pro", "controller_neptune", "controller_legion_go_s"}

type vdfInput struct{ name, binding string }

func vdfInputText(name, binding string) string {
	return "\t\t\t\"" + name + "\"\n\t\t\t{\n\t\t\t\t\"activators\"\n\t\t\t\t{\n" +
		"\t\t\t\t\t\"Full_Press\"\n\t\t\t\t\t{\n\t\t\t\t\t\t\"bindings\"\n\t\t\t\t\t\t{\n" +
		"\t\t\t\t\t\t\t\"binding\"\t\t\"" + binding + "\"\n" +
		"\t\t\t\t\t\t}\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n"
}

// vdfGroup writes one input group; settings keep the order given.
func vdfGroup(id int, mode string, inputs []vdfInput, settings [][2]string) string {
	var b strings.Builder
	fmt.Fprintf(&b, "\t\"group\"\n\t{\n\t\t\"id\"\t\t\"%d\"\n\t\t\"mode\"\t\t\"%s\"\n\t\t\"inputs\"\n\t\t{\n", id, mode)
	for _, in := range inputs {
		b.WriteString(vdfInputText(in.name, in.binding))
	}
	b.WriteString("\t\t}\n")
	if len(settings) > 0 {
		b.WriteString("\t\t\"settings\"\n\t\t{\n")
		for _, kv := range settings {
			b.WriteString("\t\t\t\"" + kv[0] + "\"\t\t\"" + kv[1] + "\"\n")
		}
		b.WriteString("\t\t}\n")
	}
	b.WriteString("\t}\n")
	return b.String()
}

// BuildWheelLayout is the Steam Input layout for one pad type. wheel is the
// slices clockwise after the top one (the top itself stays empty, so letting
// go there sends nothing). scale <= 0 means the 4K size.
func BuildWheelLayout(controllerType string, wheel []Slice, scale int) string {
	if scale <= 0 {
		scale = wheelScaleAt4K
	}
	x := func(b string) string { return "xinput_button " + b }
	// slice 1 is the top: no binding; the actions follow it
	var radial []vdfInput
	for i, s := range wheel {
		radial = append(radial, vdfInput{"touch_menu_button_" + strconv.Itoa(i+2), "key_press " + s.Key + ", " + s.Label + ", , "})
	}
	radial = append(radial, vdfInput{"click", x("JOYSTICK_RIGHT")})
	var g strings.Builder
	g.WriteString(vdfGroup(0, "four_buttons", []vdfInput{{"button_a", x("A")}, {"button_b", x("B")},
		{"button_x", x("X")}, {"button_y", x("Y")}}, nil))
	g.WriteString(vdfGroup(1, "dpad", []vdfInput{{"dpad_north", x("DPAD_UP")}, {"dpad_south", x("DPAD_DOWN")},
		{"dpad_east", x("DPAD_RIGHT")}, {"dpad_west", x("DPAD_LEFT")}}, [][2]string{{"requires_click", "0"}}))
	g.WriteString(vdfGroup(2, "joystick_move", []vdfInput{{"click", x("JOYSTICK_LEFT")}}, nil))
	g.WriteString(vdfGroup(3, "radial_menu", radial, [][2]string{
		{"touch_menu_button_count", strconv.Itoa(len(wheel) + 2)},
		{"touchmenu_button_fire_type", "2"}, // fire on release
		{"touch_menu_show_labels", "1"},
		{"touch_menu_position_x", "50"}, // screen center
		{"touch_menu_position_y", "50"},
		{"touch_menu_scale", strconv.Itoa(scale)},
		{"touch_menu_opacity", "90"}}))
	g.WriteString(vdfGroup(4, "trigger", []vdfInput{{"click", x("TRIGGER_LEFT")}}, [][2]string{{"output_trigger", "1"}}))
	g.WriteString(vdfGroup(5, "trigger", []vdfInput{{"click", x("TRIGGER_RIGHT")}}, [][2]string{{"output_trigger", "2"}}))
	g.WriteString(vdfGroup(6, "switches", []vdfInput{{"button_escape", x("START")}, {"button_menu", x("SELECT")},
		{"left_bumper", x("SHOULDER_LEFT")}, {"right_bumper", x("SHOULDER_RIGHT")}}, nil))
	return "\"controller_mappings\"\n{\n\t\"version\"\t\t\"3\"\n\t\"revision\"\t\t\"1\"\n\t\"title\"\t\t\"" + layoutTitle + "\"\n" +
		"\t\"description\"\t\t\"All buttons pass through to PokeMMO's own controller binds. Right stick opens a labeled wheel (top slice does nothing): Pokedex, Incubators, Trainer, Friends, GTL, Hotbar 6-9, Hide GUI.\"\n" +
		"\t\"creator\"\t\t\"0\"\n\t\"progenitor\"\t\t\"\"\n\t\"url\"\t\t\"\"\n\t\"export_type\"\t\t\"personal_local\"\n" +
		"\t\"controller_type\"\t\t\"" + controllerType + "\"\n" +
		"\t\"major_revision\"\t\t\"0\"\n\t\"minor_revision\"\t\t\"0\"\n\t\"Timestamp\"\t\t\"0\"\n" +
		"\t\"actions\"\n\t{\n\t\t\"Default\"\n\t\t{\n\t\t\t\"title\"\t\t\"Default\"\n\t\t\t\"legacy_set\"\t\t\"1\"\n\t\t}\n\t}\n" +
		"\t\"action_layers\"\n\t{\n\t}\n\t\"localization\"\n\t{\n\t}\n" +
		g.String() +
		"\t\"preset\"\n\t{\n\t\t\"id\"\t\t\"0\"\n\t\t\"name\"\t\t\"Default\"\n\t\t\"group_source_bindings\"\n\t\t{\n" +
		"\t\t\t\"0\"\t\t\"button_diamond active\"\n\t\t\t\"1\"\t\t\"dpad active\"\n\t\t\t\"2\"\t\t\"joystick active\"\n" +
		"\t\t\t\"3\"\t\t\"right_joystick active\"\n\t\t\t\"4\"\t\t\"left_trigger active\"\n\t\t\t\"5\"\t\t\"right_trigger active\"\n" +
		"\t\t\t\"6\"\t\t\"switch active\"\n\t\t}\n\t}\n\t\"settings\"\n\t{\n\t}\n}\n"
}

var configBlockRE = regexp.MustCompile(`(?ms)^\t"` + configDirName + `"\n\t\{\n.*?\n?^\t\}\n`)

// ConfigsetWithBlock puts block into a Steam configset_*.vdf text, replacing
// ours if it is already there. It fails when the text has no closing brace.
func ConfigsetWithBlock(text, block string) (string, error) {
	text = strings.TrimRightFunc(configBlockRE.ReplaceAllString(text, ""), unicode.IsSpace)
	if !strings.HasSuffix(text, "}") {
		return "", fmt.Errorf("unexpected layout")
	}
	return text[:len(text)-1] + block + "}\n", nil
}
