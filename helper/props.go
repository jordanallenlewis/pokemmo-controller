package main

import (
	"regexp"
	"strconv"
	"strings"
	"unicode/utf16"
)

// Java .properties editing, a port of tools/common.py. Every other line of a
// file is kept exactly as it was; only the keys asked for change.

var keyRe = regexp.MustCompile(`^[ \t\f]*((?:\\.|[^\s\p{Z}\x1c-\x1f\x85=:\\])+)[ \t\f]*[=:]?[ \t\f]*`)

// decode turns file bytes into text with \n line ends and reports the file's newline.
func decode(data []byte) (string, string) {
	nl := "\n"
	if strings.Contains(string(data), "\r\n") {
		nl = "\r\n"
	}
	return strings.ReplaceAll(string(data), "\r\n", "\n"), nl
}

func encode(text, nl string) []byte { return []byte(strings.ReplaceAll(text, "\n", nl)) }

// splitLines returns the lines and whether the text ended with a newline.
func splitLines(text string) ([]string, bool) {
	lines := strings.Split(text, "\n")
	final := lines[len(lines)-1] == ""
	if final {
		lines = lines[:len(lines)-1]
	}
	return lines, final
}

func joinLines(lines []string, final bool) string {
	s := strings.Join(lines, "\n")
	if final && len(lines) > 0 {
		return s + "\n"
	}
	return s
}

// lineKey is the key on a line, or ok=false for blank, comment and keyless lines.
func lineKey(line string) (string, bool) {
	s := strings.TrimLeft(line, " \t\f")
	if s == "" || s[0] == '#' || s[0] == '!' {
		return "", false
	}
	m := keyRe.FindStringSubmatch(line)
	if m == nil {
		return "", false
	}
	return m[1], true
}

func lineValue(line string) string {
	m := keyRe.FindString(line)
	return line[len(m):]
}

// getProp is the raw value of key; the last line wins, as in Java.
func getProp(lines []string, key string) (string, bool) {
	val, found := "", false
	for _, l := range lines {
		if k, ok := lineKey(l); ok && k == key {
			val, found = lineValue(l), true
		}
	}
	return val, found
}

// setProps sets keys to raw values (nil deletes). New keys go at the end in the order given.
func setProps(lines []string, keys []string, want map[string]*string) []string {
	var out []string
	seen := map[string]bool{}
	for _, l := range lines {
		if k, ok := lineKey(l); ok {
			if v, in := want[k]; in {
				seen[k] = true
				if v == nil {
					continue
				}
				l = k + "=" + *v
			}
		}
		out = append(out, l)
	}
	for _, k := range keys {
		if v := want[k]; v != nil && !seen[k] {
			out = append(out, k+"="+*v)
		}
	}
	return out
}

var unescRe = regexp.MustCompile(`\\(u[0-9a-fA-F]{4}|.)`)
var pairRe = regexp.MustCompile(`\\u([dD][89abAB][0-9a-fA-F]{2})\\u([dD][c-fC-F][0-9a-fA-F]{2})`)

// unescape turns java.util.Properties escapes into text.
func unescape(v string) string {
	v = pairRe.ReplaceAllStringFunc(v, func(m string) string { // a surrogate pair is one character
		hi, _ := strconv.ParseUint(m[2:6], 16, 32)
		lo, _ := strconv.ParseUint(m[8:12], 16, 32)
		return string(utf16.DecodeRune(rune(hi), rune(lo)))
	})
	return unescRe.ReplaceAllStringFunc(v, func(m string) string {
		s := m[1:]
		if s[0] == 'u' && len(s) == 5 {
			n, _ := strconv.ParseUint(s[1:], 16, 32)
			return string(rune(n))
		}
		switch s {
		case "t":
			return "\t"
		case "n":
			return "\n"
		case "r":
			return "\r"
		case "f":
			return "\f"
		}
		return s
	})
}

// escape turns text into a value the way PokeMMO itself writes it.
func escape(v string) string {
	var b strings.Builder
	for i, ch := range []rune(v) {
		switch {
		case ch == ' ' && i == 0:
			b.WriteString(`\ `)
		case ch == '\\' || ch == '#' || ch == '!' || ch == '=' || ch == ':':
			b.WriteByte('\\')
			b.WriteRune(ch)
		case ch == '\t':
			b.WriteString(`\t`)
		case ch == '\n':
			b.WriteString(`\n`)
		case ch == '\r':
			b.WriteString(`\r`)
		case ch == '\f':
			b.WriteString(`\f`)
		case ch < 0x20 || ch > 0x7E:
			for _, u := range utf16.Encode([]rune{ch}) {
				b.WriteString(`\u` + strings.ToUpper(pad4(strconv.FormatUint(uint64(u), 16))))
			}
		default:
			b.WriteRune(ch)
		}
	}
	return b.String()
}

func pad4(s string) string { return strings.Repeat("0", 4-len(s)) + s }
