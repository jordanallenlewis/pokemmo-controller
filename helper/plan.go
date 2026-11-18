package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

// This file is the Go twin of Plan in tools/common.py: collect every file change first, write them
// all at the end, keep each original once as <file>.bak-pokemmo-controller, and record what was
// written so an update or uninstall can put the exact original bytes back. The record is the same
// config/pokemmo-controller.json the Python installer reads, so either tool can undo the other.
// tests/golden/plan-parity.json holds what Python does; plan_test.go replays it.

const (
	backupSuffix = ".bak-pokemmo-controller"
	stateName    = "pokemmo-controller.json"
	// recordVersion is written into the record; it must equal VERSION in tools/common.py
	// (plan_test.go checks it against the golden file).
	recordVersion = "1.3.0-beta.1"
)

func shaHex(b []byte) string {
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

// readBytes returns nil, false when the file does not exist.
// isMissing: the file is not there (or a parent is a file), which the Python tool reads as missing.
func isMissing(err error) bool {
	return errors.Is(err, fs.ErrNotExist) || errors.Is(err, syscall.ENOTDIR)
}

func readBytes(p string) ([]byte, bool) {
	b, err := os.ReadFile(p)
	if err != nil {
		return nil, false
	}
	return b, true
}

func backupPath(p string) string { return p + backupSuffix }

// sweepTmp deletes name.XXXX.tmp leftovers of writeAtomic next to path that a killed process left
// behind. minAge: only those older than this (another run may be writing one right now).
func sweepTmp(path string, minAge time.Duration) {
	matches, _ := filepath.Glob(filepath.Join(filepath.Dir(path), escapeGlob(filepath.Base(path))+".*.tmp"))
	for _, f := range matches {
		if minAge > 0 {
			if st, err := os.Stat(f); err != nil || time.Since(st.ModTime()) < minAge {
				continue
			}
		}
		os.Remove(f)
	}
}

func escapeGlob(s string) string {
	return strings.NewReplacer("[", `\[`, "*", `\*`, "?", `\?`, `\`, `\\`).Replace(s)
}

type pendingChange struct {
	data     []byte // nil with del set = delete the file
	del      bool
	backupOK bool
}

// Plan collects every file change first, then writes them all. Nothing touches the disk until
// commit, so a bad file found halfway stops the run before anything changed.
type Plan struct {
	pokemmo     string
	state       map[string]any
	files       map[string]map[string]any
	changes     map[string]*pendingChange
	order       []string
	Notes       []string
	DropBackups []string // uninstall: backups to delete at the end
	Fresh       bool     // nothing installed: backups left by an old uninstall are stale
	readErrs    []error  // files that are there but could not be read: commit stops before any write
}

func newPlan(pokemmo string) *Plan {
	p := &Plan{pokemmo: pokemmo, changes: map[string]*pendingChange{}}
	p.state = p.loadState()
	files, _ := p.state["files"].(map[string]any)
	if files == nil {
		files = map[string]any{}
		p.state["files"] = files
	}
	p.files = map[string]map[string]any{}
	for k, v := range files {
		if m, ok := v.(map[string]any); ok {
			p.files[k] = m
		}
	}
	return p
}

func (p *Plan) statePath() string {
	if p.pokemmo == "" {
		return ""
	}
	return filepath.Join(p.pokemmo, "config", stateName)
}

func (p *Plan) loadState() map[string]any {
	st := map[string]any{}
	if p.statePath() == "" {
		return st
	}
	b, ok := readBytes(p.statePath())
	if !ok {
		return st
	}
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.UseNumber() // keep keys we do not know about exactly as they were
	var m map[string]any
	if err := dec.Decode(&m); err != nil || m == nil {
		return st
	}
	return m
}

// read is readBytes for planning: a file that is there but cannot be read (a folder in its place,
// no permission, locked) is not taken as missing; it is remembered and commit stops before any write.
func (p *Plan) read(path string) ([]byte, bool) {
	b, err := os.ReadFile(path)
	if err == nil {
		return b, true
	}
	if !isMissing(err) {
		p.readErrs = append(p.readErrs, fmt.Errorf("could not read %s: %w", path, err))
	}
	return nil, false
}

// current is what the file will look like after commit.
func (p *Plan) current(path string) ([]byte, bool) {
	if c, ok := p.changes[path]; ok {
		if c.del {
			return nil, false
		}
		return c.data, true
	}
	return p.read(path)
}

// put schedules path to hold data. backupOK=false: the file already holds our changes, so do not
// keep a copy of it as the original.
func (p *Plan) put(path string, data []byte, backupOK bool) {
	prev, seen := p.changes[path]
	if !seen {
		p.order = append(p.order, path)
	}
	ok := backupOK && (!seen || prev.backupOK)
	p.changes[path] = &pendingChange{data: data, backupOK: ok}
}

func (p *Plan) delete(path string) {
	if _, seen := p.changes[path]; !seen {
		p.order = append(p.order, path)
	}
	p.changes[path] = &pendingChange{del: true, backupOK: true}
}

// pending lists the files whose planned content differs from what is on disk, in plan order.
func (p *Plan) pending() []string {
	var out []string
	for _, path := range p.order {
		c := p.changes[path]
		cur, exists := readBytes(path)
		if c.del {
			if exists {
				out = append(out, path)
			}
		} else if !exists || !bytes.Equal(cur, c.data) {
			out = append(out, path)
		}
	}
	return out
}

// exactOriginal: orig is the original bytes (found && orig == nil: the file did not exist) when
// only we changed path since its backup; ok is false when someone else changed it too and a
// merge is needed.
func (p *Plan) exactOriginal(path string) (orig []byte, existed bool, ok bool) {
	rec := p.files[path]
	cur, exists := readBytes(path)
	pristine, _ := rec["pristine"].(bool)
	want, _ := rec["sha"].(string)
	if rec == nil || !pristine || !exists || shaHex(cur) != want {
		return nil, false, false
	}
	if created, _ := rec["created"].(bool); created {
		return nil, false, true
	}
	bak, have := readBytes(backupPath(path))
	if !have {
		return nil, false, false
	}
	return bak, true, true
}

func (p *Plan) commit(uninstall bool) error {
	if len(p.readErrs) > 0 {
		return fmt.Errorf("%v. Nothing was changed", p.readErrs[0])
	}
	pending := p.pending()
	for _, path := range pending { // a read-only file stops the run before any write
		if st, err := os.Stat(path); err == nil && st.Mode().Perm()&0o200 == 0 {
			return fmt.Errorf("%s is read-only. Make it writable, then run this again. Nothing was changed", path)
		}
	}
	for _, path := range pending {
		c := p.changes[path]
		cur, exists := readBytes(path)
		if c.del {
			os.Remove(path)
			sweepTmp(path, 0)
			delete(p.files, path)
			continue
		}
		if uninstall {
			if err := writeAtomic(path, c.data); err != nil {
				return err
			}
			sweepTmp(path, 0)
			delete(p.files, path)
			continue
		}
		rec := p.files[path]
		fresh := false
		if _, haveBak := readBytes(backupPath(path)); exists && c.backupOK && (p.Fresh || !haveBak) {
			if err := writeAtomic(backupPath(path), cur); err != nil {
				return err
			}
			fresh = true
		}
		var pristine, created bool
		if rec != nil && !p.Fresh {
			rp, _ := rec["pristine"].(bool)
			rc, _ := rec["created"].(bool)
			if rp {
				if exists {
					pristine = shaHex(cur) == rec["sha"]
				} else {
					pristine = rc
				}
			}
			created = rc
		} else {
			pristine, created = !exists || fresh, !exists
		}
		dirs, _ := p.state["created_dirs"].([]any)
		if dirs == nil {
			dirs = []any{}
		}
		for d := filepath.Dir(path); ; d = filepath.Dir(d) {
			if _, err := os.Stat(d); err == nil || d == filepath.Dir(d) {
				break
			}
			if !containsAny(dirs, d) {
				dirs = append(dirs, d)
			}
		}
		p.state["created_dirs"] = dirs
		if err := writeAtomic(path, c.data); err != nil {
			return err
		}
		nrec := map[string]any{}
		for k, v := range rec {
			nrec[k] = v
		}
		nrec["sha"], nrec["pristine"], nrec["created"] = shaHex(c.data), pristine, created
		p.files[path] = nrec
		if p.pokemmo != "" {
			if err := p.saveState(false); err != nil { // an interrupted run still knows what it wrote
				return err
			}
		}
	}
	if uninstall {
		for _, b := range p.DropBackups {
			os.Remove(b)
		}
		if p.statePath() != "" {
			os.Remove(p.statePath())
		}
		return nil
	}
	if p.pokemmo != "" {
		return p.saveState(true)
	}
	return nil
}

func containsAny(list []any, s string) bool {
	for _, v := range list {
		if x, ok := v.(string); ok && x == s {
			return true
		}
	}
	return false
}

func (p *Plan) saveState(final bool) error {
	if final {
		p.state["version"] = recordVersion
	}
	files := map[string]any{}
	for k, v := range p.files {
		files[k] = v
	}
	p.state["files"] = files
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(p.state); err != nil { // Encode ends with a newline, like the Python record
		return err
	}
	return writeAtomic(p.statePath(), buf.Bytes())
}
