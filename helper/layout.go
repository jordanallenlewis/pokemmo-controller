package main

// The layout core, ported from tools/layout.py: which controller input does
// which PokeMMO action, and the macro policy (1 input = 1 action).
//
// A layout holds only binds (one input per action) and ten wheel slices (one
// action each, each at most once). Nothing else is accepted: no turbo, repeat,
// sequence, delay, combo, macro, cursor or script field, no input shared by
// two actions. The messages match the Python tool word for word; the golden
// file tests/golden/layout-parity.json keeps the two in step.

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

const (
	layoutFormat   = 1
	maxLayoutBytes = 64 * 1024
	buttons        = 15 // 0..14
	axes           = 6  // 0 left X, 1 left Y, 2 right X, 3 right Y, 4 left trigger, 5 right trigger
)

// Native game actions, in the order the writers use.
var actionOrder = []string{
	"KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_A", "KEY_B", "KEY_X", "KEY_Y",
	"KEY_RING_FOCUS", "KEY_GAMEMENU", "KEY_INVENTORY", "KEY_NEXT", "KEY_PREVIOUS",
	"KEY_HOTBAR_1", "KEY_HOTBAR_2", "KEY_HOTBAR_3", "KEY_HOTBAR_4", "KEY_HOTBAR_5",
	"KEY_TEAM", "KEY_SCREENSHOT",
}

type wheelAction struct {
	id, key, label, bind string
	code                 int
}

var wheelActions = []wheelAction{
	{"codex", "N", "Pokedex", "client.controls.gdx.codex", 42},
	{"incubator", "I", "Egg Incubators", "client.controls.gdx.incubator", 37},
	{"trainer", "C", "Trainer Card", "client.controls.gdx.trainer", 31},
	{"friendlist", "V", "Friends", "client.controls.gdx.friendlist", 50},
	{"tradelink", "P", "Global Trade Link", "client.controls.gdx.tradelink", 44},
	{"hotbar6", "6", "Hotbar 6", "client.controls.gdx.hotbar6", 13},
	{"hotbar7", "7", "Hotbar 7", "client.controls.gdx.hotbar7", 14},
	{"hotbar8", "8", "Hotbar 8", "client.controls.gdx.hotbar8", 15},
	{"hotbar9", "9", "Hotbar 9", "client.controls.gdx.hotbar9", 16},
	{"hidegui", "F12", "Hide GUI", "client.controls.gdx.hidegui", 142},
}

func isAction(a string) bool {
	for _, x := range actionOrder {
		if x == a {
			return true
		}
	}
	return false
}

func wheelByID(id string) (wheelAction, bool) {
	for _, w := range wheelActions {
		if w.id == id {
			return w, true
		}
	}
	return wheelAction{}, false
}

func isRightStick(a int) bool { return a == 2 || a == 3 }
func isTrigger(a int) bool    { return a == 4 || a == 5 }

// Input is one button, or one direction of one axis.
type Input struct {
	Axis     bool
	N        int
	Positive bool
}

// Slice is one wheel slice: the Steam key and its label.
type Slice struct{ Key, Label string }

// Bind is one action's input, in actionOrder.
type Bind struct {
	Action string
	Input  Input
}

// LayoutError means the layout breaks a rule; the message says which.
type LayoutError struct{ Msg string }

func (e *LayoutError) Error() string { return e.Msg }

func lerr(format string, a ...any) error { return &LayoutError{fmt.Sprintf(format, a...)} }

// ---------------------------------------------------------------- JSON values
// A small ordered JSON model so the checks run in the file's own order (the
// first error is the same one Python reports) and duplicate keys are refused.

type member struct {
	key string
	val any
}
type object []member

func (o object) get(k string) (any, bool) {
	for _, m := range o {
		if m.key == k {
			return m.val, true
		}
	}
	return nil, false
}

type number struct {
	isInt bool
	i     int64 // valid when isInt and it fits
	big   bool  // an integer too large for int64: never a valid index
}

func parseValue(dec *json.Decoder) (any, error) {
	tok, err := dec.Token()
	if err != nil {
		return nil, err
	}
	switch t := tok.(type) {
	case json.Delim:
		if t == '{' {
			var o object
			seen := map[string]bool{}
			for dec.More() {
				kt, err := dec.Token()
				if err != nil {
					return nil, err
				}
				k := kt.(string)
				if seen[k] {
					return nil, lerr("%s appears twice in the file.", pyRepr(k))
				}
				seen[k] = true
				v, err := parseValue(dec)
				if err != nil {
					return nil, err
				}
				o = append(o, member{k, v})
			}
			if _, err := dec.Token(); err != nil {
				return nil, err
			}
			if o == nil {
				o = object{}
			}
			return o, nil
		}
		l := []any{}
		for dec.More() {
			v, err := parseValue(dec)
			if err != nil {
				return nil, err
			}
			l = append(l, v)
		}
		if _, err := dec.Token(); err != nil {
			return nil, err
		}
		return l, nil
	case json.Number:
		s := t.String()
		if strings.ContainsAny(s, ".eE") {
			return number{}, nil // a float in Python
		}
		i, err := strconv.ParseInt(s, 10, 64)
		if err != nil {
			return number{isInt: true, big: true}, nil
		}
		return number{isInt: true, i: i}, nil
	default: // string, bool, nil
		return tok, nil
	}
}

// ParseLayout reads layout text (bytes or string content) like layout.loads.
func ParseLayout(text []byte) (Layout, error) {
	s := strings.ToValidUTF8(string(text), "�")
	if utf8.RuneCountInString(s) > maxLayoutBytes {
		return Layout{}, lerr("This file is too big to be a layout.")
	}
	dec := json.NewDecoder(strings.NewReader(s))
	dec.UseNumber()
	v, err := parseValue(dec)
	if err != nil {
		if le, ok := err.(*LayoutError); ok {
			return Layout{}, le
		}
		return Layout{}, lerr("This is not a layout file (it is not valid JSON).")
	}
	// Nothing but whitespace may follow the one value.
	if _, err := dec.Token(); err != io.EOF {
		return Layout{}, lerr("This is not a layout file (it is not valid JSON).")
	}
	return validateLayout(v, false)
}

// Layout is a layout that passed every check.
type Layout struct {
	Binds []Bind   // in actionOrder
	Wheel []string // ten wheel action ids, clockwise from the top
	Name  string
}

// ---------------------------------------------------------------- checks

func inputOf(action string, spec any, pushedTriggers bool) (Input, error) {
	o, ok := spec.(object)
	if !ok {
		return Input{}, lerr("%s: each action takes exactly one input, like {\"button\": 0}.", action)
	}
	_, hasButton := o.get("button")
	_, hasAxis := o.get("axis")
	var allowed map[string]bool
	switch {
	case hasButton && hasAxis:
		return Input{}, lerr("%s: exactly one input is needed, not a button and an axis.", action)
	case hasButton:
		allowed = map[string]bool{"button": true}
	case hasAxis:
		allowed = map[string]bool{"axis": true, "positive": true}
	default:
		return Input{}, lerr("%s: exactly one input is needed: a \"button\" or an \"axis\".", action)
	}
	var extra []string
	for _, m := range o {
		if !allowed[m.key] {
			extra = append(extra, m.key)
		}
	}
	if len(extra) > 0 {
		sort.Strings(extra) // Python sorts code points; this is the same for ASCII names
		return Input{}, lerr("%s: unknown field %s. PokeMMO allows one input to do one action, so a bind holds only a button, or an axis with a direction.", action, pyRepr(extra[0]))
	}
	if hasButton {
		v, _ := o.get("button")
		n, isNum := v.(number)
		if !isNum || !n.isInt || n.big || n.i < 0 || n.i >= buttons {
			return Input{}, lerr("%s: button must be a whole number from 0 to %d.", action, buttons-1)
		}
		return Input{N: int(n.i)}, nil
	}
	v, _ := o.get("axis")
	n, isNum := v.(number)
	if !isNum || !n.isInt || n.big || n.i < 0 || n.i >= axes {
		return Input{}, lerr("%s: axis must be a whole number from 0 to %d.", action, axes-1)
	}
	if isRightStick(int(n.i)) {
		return Input{}, lerr("%s: the right stick (axes 2 and 3) belongs to the wheel.", action)
	}
	pv, _ := o.get("positive")
	pos, isBool := pv.(bool)
	if !isBool {
		return Input{}, lerr("%s: an axis needs \"positive\": true or false (which way it is pushed).", action)
	}
	if isTrigger(int(n.i)) && !pos && !pushedTriggers {
		return Input{}, lerr("%s: a trigger (axis %d) only works pulled, so it needs \"positive\": true. Released is its resting position and never sends anything.", action, n.i)
	}
	return Input{Axis: true, N: int(n.i), Positive: pos}, nil
}

func validateLayout(v any, pushedTriggers bool) (Layout, error) {
	lay, ok := v.(object)
	if !ok {
		return Layout{}, lerr("A layout is a JSON object with \"format\", \"binds\" and \"wheel\".")
	}
	var extra []string
	for _, m := range lay {
		switch m.key {
		case "format", "binds", "wheel", "name":
		default:
			extra = append(extra, m.key)
		}
	}
	if len(extra) > 0 {
		sort.Strings(extra)
		return Layout{}, lerr("unknown field %s. A layout holds only binds and the wheel: PokeMMO's rule is one input, one action, so there are no macros, turbo, repeats, sequences or delays.", pyRepr(extra[0]))
	}
	f, _ := lay.get("format")
	if n, isNum := f.(number); !isNum || !n.isInt || n.big || n.i != layoutFormat {
		return Layout{}, lerr("This layout has format %s; this version reads format %d.", pyRepr(f), layoutFormat)
	}
	out := Layout{}
	if nv, has := lay.get("name"); has {
		s, isStr := nv.(string)
		if !isStr || utf8.RuneCountInString(s) > 60 {
			return Layout{}, lerr("name must be text of at most 60 characters.")
		}
		out.Name = s
	}
	bv, _ := lay.get("binds")
	binds, ok := bv.(object)
	if !ok {
		return Layout{}, lerr("\"binds\" must be an object: action -> one input.")
	}
	seen := map[Input]string{}
	got := map[string]Input{}
	for _, m := range binds {
		if !isAction(m.key) {
			return Layout{}, lerr("unknown action %s.", pyRepr(m.key))
		}
		in, err := inputOf(m.key, m.val, pushedTriggers)
		if err != nil {
			return Layout{}, err
		}
		if other, dup := seen[in]; dup {
			return Layout{}, lerr("%s and %s use the same input. PokeMMO allows one input to do one action: give one of them another input.", m.key, other)
		}
		seen[in] = m.key
		got[m.key] = in
	}
	for _, a := range actionOrder {
		if in, has := got[a]; has {
			out.Binds = append(out.Binds, Bind{a, in})
		}
	}
	wv, _ := lay.get("wheel")
	wheel, ok := wv.([]any)
	if !ok || len(wheel) != len(wheelActions) {
		return Layout{}, lerr("\"wheel\" must list exactly %d slices.", len(wheelActions))
	}
	used := map[string]bool{}
	for i, x := range wheel {
		a, isStr := x.(string)
		if !isStr {
			return Layout{}, lerr("wheel slice %d: one action per slice, written as its name.", i+1)
		}
		if _, known := wheelByID(a); !known {
			return Layout{}, lerr("wheel slice %d: unknown action %s.", i+1, pyRepr(a))
		}
		if used[a] {
			return Layout{}, lerr("wheel slice %d: %s is on the wheel more than once; each action goes on it once.", i+1, a)
		}
		used[a] = true
		out.Wheel = append(out.Wheel, a)
	}
	return out, nil
}

// DefaultLayout is the layout that ships.
func DefaultLayout() Layout {
	b := func(n int) Input { return Input{N: n} }
	ax := func(n int, pos bool) Input { return Input{Axis: true, N: n, Positive: pos} }
	m := map[string]Input{
		"KEY_UP": ax(1, false), "KEY_DOWN": ax(1, true), "KEY_LEFT": ax(0, false), "KEY_RIGHT": ax(0, true),
		"KEY_A": b(0), "KEY_B": b(1), "KEY_X": b(2), "KEY_Y": b(3),
		"KEY_RING_FOCUS": b(9), "KEY_GAMEMENU": b(6), "KEY_INVENTORY": b(10),
		"KEY_NEXT": ax(5, true), "KEY_PREVIOUS": ax(4, true),
		"KEY_HOTBAR_1": b(11), "KEY_HOTBAR_2": b(14), "KEY_HOTBAR_3": b(12), "KEY_HOTBAR_4": b(13), "KEY_HOTBAR_5": b(4),
		"KEY_TEAM": b(7), "KEY_SCREENSHOT": b(8),
	}
	l := Layout{}
	for _, a := range actionOrder {
		l.Binds = append(l.Binds, Bind{a, m[a]})
	}
	for _, w := range wheelActions {
		l.Wheel = append(l.Wheel, w.id)
	}
	return l
}

// WheelSlices is what the Steam layout draws, clockwise from the top.
func (l Layout) WheelSlices() []Slice {
	out := make([]Slice, 0, len(l.Wheel))
	for _, id := range l.Wheel {
		w, _ := wheelByID(id)
		out = append(out, Slice{w.key, w.label})
	}
	return out
}

// ---------------------------------------------------------------- wheel size

const (
	wheelScaleAt4K  = 400
	referenceHeight = 2160
	minWheelScale   = 60
	minSide         = 320
	maxSide         = 16384
)

var resolutionRE = regexp.MustCompile(`^\s*(\d{3,5})\s*[x*X,\x{00d7}]\s*(\d{3,5})\s*$`)

// ParseResolution reads '1920x1080' (also 1920*1080, 1920 x 1080, 1920,1080).
func ParseResolution(text string) (int, int, error) {
	m := resolutionRE.FindStringSubmatch(text)
	if m == nil {
		return 0, 0, lerr("%s is not a resolution. Write it like 1920x1080.", pyRepr(text))
	}
	w, _ := strconv.Atoi(m[1])
	h, _ := strconv.Atoi(m[2])
	return checkResolution(w, h)
}

func checkResolution(w, h int) (int, int, error) {
	if w < minSide || w > maxSide || h < minSide || h > maxSide {
		return 0, 0, lerr("%dx%d is outside %d to %d pixels a side.", w, h, minSide, maxSide)
	}
	return w, h, nil
}

// WheelScale is the wheel's Steam size for a game picture of w x h pixels.
func WheelScale(w, h int) (int, error) {
	if _, _, err := checkResolution(w, h); err != nil {
		return 0, err
	}
	short := w
	if h < short {
		short = h
	}
	// Python's round() rounds half to even.
	v := int(math.RoundToEven(float64(wheelScaleAt4K) * float64(short) / float64(referenceHeight)))
	if v > wheelScaleAt4K {
		v = wheelScaleAt4K
	}
	if v < minWheelScale {
		v = minWheelScale
	}
	return v, nil
}

// ---------------------------------------------------------------- Python repr

// pyRepr writes a value the way Python's repr() does, for the cases a layout
// can hold, so error messages match the Python tool.
func pyRepr(v any) string {
	switch t := v.(type) {
	case nil:
		return "None"
	case bool:
		if t {
			return "True"
		}
		return "False"
	case number:
		if t.isInt && !t.big {
			return strconv.FormatInt(t.i, 10)
		}
		return "0.0"
	case string:
		q := byte('\'')
		if strings.Contains(t, "'") && !strings.Contains(t, "\"") {
			q = '"'
		}
		var b bytes.Buffer
		b.WriteByte(q)
		for _, r := range t {
			switch {
			case r == rune(q) || r == '\\':
				b.WriteByte('\\')
				b.WriteRune(r)
			case r == '\n':
				b.WriteString(`\n`)
			case r == '\r':
				b.WriteString(`\r`)
			case r == '\t':
				b.WriteString(`\t`)
			case r < 0x20 || r == 0x7f:
				fmt.Fprintf(&b, `\x%02x`, r)
			default:
				b.WriteRune(r)
			}
		}
		b.WriteByte(q)
		return b.String()
	case []any:
		return "[...]"
	default:
		return "{...}"
	}
}
