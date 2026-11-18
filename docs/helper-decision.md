# Helper app: language and tray choice (H0)

> **Superseded (2026-11-18).** [FOUNDATION.md](FOUNDATION.md) replaces the Go helper with one Rust engine shared by the desktop app and the `pmc` command line tool. This file is kept as history; the Go and `fyne.io/systray` choices below no longer apply to 2.0.

The helper is a small resident program so players install nothing first and
the layout keeps working while they play (follows resolution and display mode,
re-applies the binds if the game rewrites its settings, keeps the Steam
layout right).

## Decision

- **Go, one static binary per system.** No runtime for the player, no admin.
- **`fyne.io/systray`** for the tray / menu bar icon. No embedded webview: the
  remap screen stays the existing page, served on `127.0.0.1`.
- **The app window is the system browser in app mode** (update 2026-11-17).
  The page opens in its own window, with no address bar or tabs, using the
  Chromium-based browser the system already has: Edge (shipped with Windows),
  else Chrome, Chromium or Brave on any system. Closing the window ends the
  app. With none of them, or if the window will not start, it opens a normal
  browser tab, as before (`--tab` forces that). The choice lives in
  `tools/platforms.py`; the page and everything behind it are one code path.
  This keeps the rule "nothing to install, no cgo, same code everywhere". A true
  embedded WebView2 on Windows stays a later option; it would need a loader
  that works without cgo and has no benefit the app window lacks today.
- A headless mode (`helper serve`) for Steam Deck Game Mode, where there is no
  tray, and for CI.
- The Python tools stay until one stable helper release has matched them.

## Evidence (spike, Linux x64 build machine, 2026-11-17)

| | Result | Budget |
|---|---|---|
| Binary size | 5.1 MB (Windows ARM) to 7.2 MB (Linux x64), stripped | 12 MB |
| Idle memory, headless, after 5 requests | about 7 MB | 30 MB |
| Idle CPU | 0.0% | near zero |
| Builds with `CGO_ENABLED=0` | Linux x64/ARM, Windows x64/ARM | |
| macOS | needs cgo for the menu bar; built on the macOS runners, nothing to install for the player | |

The CI job `Helper` repeats the size and idle-memory check on all six systems
(Windows x64 and ARM, macOS Apple silicon and Intel, Linux x64 and ARM) on every
change; a leg over budget fails the build.

## Alternatives

- `github.com/energye/systray`: same shape, same macOS cgo need, smaller
  community. Kept as the fallback.
- Webview or Electron-style shells: need a runtime or Linux packages; the
  page already works in the browser. Rejected.
- Rust: no pure-library tray as small to maintain here; a second toolchain
  for little gain. Not chosen.

## Not yet verified

The app window on a real desktop (Edge on Windows, Chrome or Chromium on
macOS and Linux, and Steam Deck Desktop Mode): CI has no display, so tests cover
the command line and the fallback only. Tray icon on a real desktop (Windows, macOS, KDE on Steam Deck Desktop Mode)
and the Deck Game Mode headless path: CI has no display, so these wait for a
person with the hardware. Unsigned Windows and macOS binaries will show a
first-run prompt; signing is a separate decision.
