package main

import (
	"math/rand"
	"testing"
)

func noSharedInput(t *testing.T, l Layout) {
	t.Helper()
	seen := map[Input]string{}
	for _, b := range l.Binds {
		if o, dup := seen[b.Input]; dup {
			t.Fatalf("%s and %s share an input", b.Action, o)
		}
		seen[b.Input] = b.Action
	}
	seen2 := map[string]bool{}
	for _, w := range l.Wheel {
		if seen2[w] {
			t.Fatalf("wheel repeats %s", w)
		}
		seen2[w] = true
	}
}

func TestDefaultRoundTripsThroughJSONAndCode(t *testing.T) {
	d := DefaultLayout()
	back, err := ParseLayout(d.JSON())
	if err != nil {
		t.Fatal(err)
	}
	if string(back.JSON()) != string(d.JSON()) {
		t.Fatal("file round trip changed the layout")
	}
	code := d.ShareCode()
	got, err := ParseShareCode(code)
	if err != nil {
		t.Fatal(err)
	}
	if string(got.JSON()) != string(d.JSON()) {
		t.Fatal("share code round trip changed the layout")
	}
	if _, err := ParseShareCode("  " + code[:len(code)/2] + "\n" + code[len(code)/2:] + " "); err != nil {
		t.Fatalf("a pasted code with spaces should read: %v", err)
	}
}

func TestShareCodeRefusesDamage(t *testing.T) {
	code := DefaultLayout().ShareCode()
	for _, bad := range []string{"", "hello", code[:20], code + "AAAA", "PMC2" + code[4:], code[:12] + "Z" + code[13:]} {
		if bad == code {
			continue
		}
		if _, err := ParseShareCode(bad); err == nil {
			t.Fatalf("accepted %q", bad)
		}
	}
}

func TestSetBindSwapsOnADoubleBind(t *testing.T) {
	e := NewEditor(DefaultLayout())
	a, _ := e.inputOf("KEY_A")
	b, _ := e.inputOf("KEY_B")
	msg, err := e.SetBind("KEY_A", b)
	if err != nil || msg == "" {
		t.Fatalf("want a plain message, got %q %v", msg, err)
	}
	if g, _ := e.inputOf("KEY_A"); g != b {
		t.Fatal("A did not take B's input")
	}
	if g, _ := e.inputOf("KEY_B"); g != a {
		t.Fatal("B did not take A's old input")
	}
	noSharedInput(t, e.Layout())
}

func TestRefusedInputLeavesTheLayoutAlone(t *testing.T) {
	e := NewEditor(DefaultLayout())
	before := string(e.Layout().JSON())
	if _, err := e.SetBind("KEY_A", Input{Axis: true, N: 2, Positive: true}); err == nil {
		t.Fatal("the right stick belongs to the wheel")
	}
	if _, err := e.SetBind("KEY_A", Input{Axis: true, N: 4, Positive: false}); err == nil {
		t.Fatal("a released trigger never sends anything")
	}
	if e.CanUndo() || string(e.Layout().JSON()) != before {
		t.Fatal("a refused change must not touch the layout or the history")
	}
}

func TestUndoRedoReset(t *testing.T) {
	e := NewEditor(DefaultLayout())
	start := string(e.Layout().JSON())
	e.SetBind("KEY_A", Input{N: 14})
	e.SetSlice(0, "hidegui")
	changed := string(e.Layout().JSON())
	e.Reset()
	if string(e.Layout().JSON()) != start {
		t.Fatal("reset should give the default layout")
	}
	e.Undo()
	if string(e.Layout().JSON()) != changed {
		t.Fatal("undo should bring back the layout from before the reset")
	}
	e.Undo()
	e.Undo()
	if string(e.Layout().JSON()) != start || e.Undo() {
		t.Fatal("undo should stop at the start")
	}
	e.Redo()
	e.SetBind("KEY_B", Input{N: 13}) // a new change drops the redo line
	if e.CanRedo() {
		t.Fatal("a new change must clear redo")
	}
}

// Whatever the screen does, no two actions end on one input and every layout
// shown is one that can be written and read back.
func TestRandomEditsKeepOneInputOneAction(t *testing.T) {
	r := rand.New(rand.NewSource(7))
	e := NewEditor(DefaultLayout())
	for i := 0; i < 3000; i++ {
		switch r.Intn(5) {
		case 0, 1:
			in := Input{N: r.Intn(buttons)}
			if r.Intn(3) == 0 {
				in = Input{Axis: true, N: r.Intn(axes), Positive: r.Intn(2) == 0}
			}
			e.SetBind(actionOrder[r.Intn(len(actionOrder))], in) // refusals are fine
		case 2:
			e.SetSlice(r.Intn(len(wheelActions)), wheelActions[r.Intn(len(wheelActions))].id)
		case 3:
			e.Unbind(actionOrder[r.Intn(len(actionOrder))])
		default:
			e.Undo()
		}
		l := e.Layout()
		noSharedInput(t, l)
		if _, err := ParseLayout(l.JSON()); err != nil {
			t.Fatalf("step %d: layout on screen cannot be written: %v", i, err)
		}
		if got, err := ParseShareCode(l.ShareCode()); err != nil || string(got.JSON()) != string(l.JSON()) {
			t.Fatalf("step %d: share code round trip failed: %v", i, err)
		}
	}
}

// Any single wrong character in a code is caught (the last character carries
// spare bits that decode the same, so it is left out).
func TestShareCodeCatchesEverySingleTypo(t *testing.T) {
	code := DefaultLayout().ShareCode()
	body := []byte(code[len(codePrefix)+1:])
	count := 0
	for i := 0; i < len(body)-1; i++ {
		if body[i] == '-' {
			continue
		}
		for _, c := range []byte("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567") {
			if c == body[i] {
				continue
			}
			mut := append([]byte(nil), body...)
			mut[i] = c
			if _, err := ParseShareCode(codePrefix + "-" + string(mut)); err == nil {
				t.Fatalf("accepted a code with character %d changed to %c", i, c)
			}
			count++
		}
	}
	if count < 1000 {
		t.Fatalf("only %d typos tried", count)
	}
}
