package main

import (
	"bytes"
	"encoding/base32"
	"encoding/binary"
	"fmt"
	"hash/crc32"
	"strconv"
	"strings"
)

// JSON writes the layout in the file format a player exports and imports.
func (l Layout) JSON() []byte {
	var b bytes.Buffer
	fmt.Fprintf(&b, "{\n  \"format\": %d,\n", layoutFormat)
	if l.Name != "" {
		fmt.Fprintf(&b, "  \"name\": %s,\n", strconv.Quote(l.Name))
	}
	b.WriteString("  \"binds\": {")
	for i, bd := range l.Binds {
		if i > 0 {
			b.WriteString(",")
		}
		if bd.Input.Axis {
			fmt.Fprintf(&b, "\n    \"%s\": {\"axis\": %d, \"positive\": %t}", bd.Action, bd.Input.N, bd.Input.Positive)
		} else {
			fmt.Fprintf(&b, "\n    \"%s\": {\"button\": %d}", bd.Action, bd.Input.N)
		}
	}
	b.WriteString("\n  },\n  \"wheel\": [")
	for i, w := range l.Wheel {
		if i > 0 {
			b.WriteString(", ")
		}
		b.WriteString(strconv.Quote(w))
	}
	b.WriteString("]\n}\n")
	return b.Bytes()
}

// Editor is one editing session: the layout being changed, with undo, redo
// and reset. Every change goes through the same checks as an imported file,
// so a layout the screen shows can always be applied.
type Editor struct {
	cur        Layout
	undo, redo []Layout
}

func NewEditor(l Layout) *Editor { return &Editor{cur: clone(l)} }

func clone(l Layout) Layout {
	return Layout{Binds: append([]Bind(nil), l.Binds...), Wheel: append([]string(nil), l.Wheel...), Name: l.Name}
}

// Layout is a copy of what is being edited.
func (e *Editor) Layout() Layout { return clone(e.cur) }

func (e *Editor) push(next Layout) {
	e.undo = append(e.undo, e.cur)
	e.redo = nil
	e.cur = next
}

func (e *Editor) inputOf(action string) (Input, bool) {
	for _, b := range e.cur.Binds {
		if b.Action == action {
			return b.Input, true
		}
	}
	return Input{}, false
}

// SetBind gives an action an input. If another action already holds that
// input the two swap (or the other becomes unbound when this action had
// none), and the message says so in plain words. An input the rules refuse
// (right stick, a released trigger) leaves the layout as it was.
func (e *Editor) SetBind(action string, in Input) (string, error) {
	if !isAction(action) {
		return "", lerr("unknown action %s.", pyRepr(action))
	}
	old, had := e.inputOf(action)
	next := clone(e.cur)
	msg := ""
	m := map[string]Input{}
	for _, b := range next.Binds {
		m[b.Action] = b.Input
	}
	for _, b := range next.Binds {
		if b.Action != action && b.Input == in {
			if had {
				m[b.Action] = old
				msg = fmt.Sprintf("%s now uses the input %s had, because one input does one action.", b.Action, action)
			} else {
				delete(m, b.Action)
				msg = fmt.Sprintf("%s is now unbound, because one input does one action.", b.Action)
			}
		}
	}
	m[action] = in
	next.Binds = bindsOf(m)
	if _, err := ParseLayout(next.JSON()); err != nil {
		return "", err
	}
	e.push(next)
	return msg, nil
}

// Unbind removes an action's input.
func (e *Editor) Unbind(action string) error {
	if _, had := e.inputOf(action); !had {
		return nil
	}
	next := clone(e.cur)
	m := map[string]Input{}
	for _, b := range next.Binds {
		if b.Action != action {
			m[b.Action] = b.Input
		}
	}
	next.Binds = bindsOf(m)
	e.push(next)
	return nil
}

func bindsOf(m map[string]Input) []Bind {
	var out []Bind
	for _, a := range actionOrder {
		if in, ok := m[a]; ok {
			out = append(out, Bind{a, in})
		}
	}
	return out
}

// SetSlice puts a wheel action on slice i; the slice that had it takes the
// action this slice held, so each action stays on the wheel once.
func (e *Editor) SetSlice(i int, id string) (string, error) {
	if i < 0 || i >= len(e.cur.Wheel) {
		return "", lerr("the wheel has %d slices.", len(wheelActions))
	}
	if _, ok := wheelByID(id); !ok {
		return "", lerr("wheel slice %d: unknown action %s.", i+1, pyRepr(id))
	}
	if e.cur.Wheel[i] == id {
		return "", nil
	}
	next := clone(e.cur)
	msg := ""
	for j, w := range next.Wheel {
		if w == id {
			next.Wheel[j] = next.Wheel[i]
			msg = "Each action goes on the wheel once, so the two slices swapped."
		}
	}
	next.Wheel[i] = id
	e.push(next)
	return msg, nil
}

// Replace loads a whole layout (an imported file, a preset, a share code).
func (e *Editor) Replace(l Layout) {
	e.push(clone(l))
}

// Reset goes back to the layout that ships. It can be undone.
func (e *Editor) Reset() { e.push(DefaultLayout()) }

func (e *Editor) CanUndo() bool { return len(e.undo) > 0 }
func (e *Editor) CanRedo() bool { return len(e.redo) > 0 }

func (e *Editor) Undo() bool {
	if !e.CanUndo() {
		return false
	}
	e.redo = append(e.redo, e.cur)
	e.cur = e.undo[len(e.undo)-1]
	e.undo = e.undo[:len(e.undo)-1]
	return true
}

func (e *Editor) Redo() bool {
	if !e.CanRedo() {
		return false
	}
	e.undo = append(e.undo, e.cur)
	e.cur = e.redo[len(e.redo)-1]
	e.redo = e.redo[:len(e.redo)-1]
	return true
}

// ---------------------------------------------------------------- share code

const (
	codePrefix = "PMC1"
	unbound    = 0xFF
)

var codeEnc = base32.StdEncoding.WithPadding(base32.NoPadding)

func inputByte(in Input) byte {
	if !in.Axis {
		return byte(in.N)
	}
	b := 16 + in.N*2
	if in.Positive {
		b++
	}
	return byte(b)
}

func byteInput(b byte) (Input, bool) {
	switch {
	case b < buttons:
		return Input{N: int(b)}, true
	case b >= 16 && b < 16+axes*2:
		return Input{Axis: true, N: int(b-16) / 2, Positive: (b-16)%2 == 1}, true
	}
	return Input{}, false
}

// ShareCode is the layout as a short text to paste in a message: PMC1-XXXX-...
// It holds only binds and the wheel, so it cannot carry anything else.
func (l Layout) ShareCode() string {
	raw := make([]byte, 0, len(actionOrder)+len(wheelActions)+4)
	for _, a := range actionOrder {
		v := byte(unbound)
		for _, b := range l.Binds {
			if b.Action == a {
				v = inputByte(b.Input)
			}
		}
		raw = append(raw, v)
	}
	for _, w := range l.Wheel {
		for i, wa := range wheelActions {
			if wa.id == w {
				raw = append(raw, byte(i))
			}
		}
	}
	raw = binary.BigEndian.AppendUint16(raw, uint16(crc32.ChecksumIEEE(raw)))
	s := codeEnc.EncodeToString(raw)
	var parts []string
	for len(s) > 4 {
		parts = append(parts, s[:4])
		s = s[4:]
	}
	parts = append(parts, s)
	return codePrefix + "-" + strings.Join(parts, "-")
}

// ParseShareCode reads a code (any case, with or without dashes and spaces)
// and runs the layout through the same checks as an imported file.
func ParseShareCode(code string) (Layout, error) {
	s := strings.ToUpper(strings.Map(func(r rune) rune {
		if r == '-' || r == ' ' || r == '\n' || r == '\t' || r == '\r' {
			return -1
		}
		return r
	}, code))
	if !strings.HasPrefix(s, codePrefix) {
		return Layout{}, lerr("This is not a share code (it should start with %s-).", codePrefix)
	}
	raw, err := codeEnc.DecodeString(strings.TrimPrefix(s, codePrefix))
	n := len(actionOrder) + len(wheelActions)
	if err != nil || len(raw) != n+2 {
		return Layout{}, lerr("This share code is not complete. Copy all of it and try again.")
	}
	if binary.BigEndian.Uint16(raw[n:]) != uint16(crc32.ChecksumIEEE(raw[:n])) {
		return Layout{}, lerr("This share code has a typo in it. Copy it again.")
	}
	l := Layout{}
	for i, a := range actionOrder {
		if raw[i] == unbound {
			continue
		}
		in, ok := byteInput(raw[i])
		if !ok {
			return Layout{}, lerr("This share code is not one this version understands.")
		}
		l.Binds = append(l.Binds, Bind{a, in})
	}
	for _, v := range raw[len(actionOrder):n] {
		if int(v) >= len(wheelActions) {
			return Layout{}, lerr("This share code is not one this version understands.")
		}
		l.Wheel = append(l.Wheel, wheelActions[v].id)
	}
	return ParseLayout(l.JSON())
}
