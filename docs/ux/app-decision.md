# The PMC app: technology decision

Goal: one download per system, no terminal, nothing to install first. The app
sets everything up, shows the player's controller and what each press does, and
is the one place to change controls.

## Decision

**A single Go program per system (already in `helper/`), with a web interface
built ahead of time and embedded in it. The window is the system's own
Chromium-based browser in app mode, with a normal browser tab as the fallback.
Live input comes from the browser Gamepad API.** Native installers wrap that one
program: Windows per-user `.exe` (Inno Setup), macOS `.dmg` holding an `.app`,
Linux `AppImage` (Flatpak later), plus a Steam Deck path that adds the app as a
non-Steam game.

- **Interface:** React with Base UI components and the shared PMC brand tokens
  (`brand/tokens.json`). It is compiled in CI into static files and embedded
  with `go:embed`, so the player never needs Node and nothing is fetched at
  runtime. A test fails if the checked-in build is stale.
- **Installer logic:** the Go port of `apply_native`, `install_wheel` and the
  uninstall path (milestone H1, mostly merged) replaces the Python tools inside
  the app. The Python tools and the one-line installers stay as the advanced
  option until the app has matched them in a stable release.
- **Size and speed targets:** download under 15 MB per system, cold start to
  first paint under 1 second on a mid laptop. CI measures size on every leg.

## Why not the alternatives

| Option | Gain | Cost for this project |
|---|---|---|
| **Tauri** (Rust, system webview) | Small installers, built-in updater and signing hooks | Needs WebKitGTK on Linux. Tauri's AppImage bundles it, which makes the download large, and WebKitGTK's Gamepad support depends on how it was built and has been unreliable. A second language and a rewrite of the Go core that is already tested and parity-checked against the Python tools. The hard rule "nothing to install" is harder to keep on Linux and Deck. |
| **Wails / webview in Go** | One language | Needs cgo and WebKitGTK on Linux, so the same Linux problem. |
| **Electron** | Familiar | About 100 MB, ships a whole browser. Rejected. |
| **SDL3 or pygame-ce for input** | Exact button identity on every pad | Needs cgo or a Python runtime on every system. The Gamepad API already names Xbox, PlayStation and Switch Pro pads and works with no install. Kept as an option for a later "pad not recognised" fallback. |
| **Stay with a Python screen** | Nothing new | The installer would have to bundle Python (15 to 30 MB per system) and the Go port already exists. |

Revisit Tauri if one of these becomes true: the browser app-mode window turns
out poor on real hardware, we need an embedded window on Linux, or its updater
and signing flow save more work than the rewrite costs.

## What this costs us, honestly

- **Window quality varies.** Windows always has Edge. macOS and Linux need
  Chrome, Chromium, Brave or Edge for the app-style window; otherwise the app
  opens a browser tab. Steam Deck ships only Firefox, so Desktop Mode will
  show a tab until a Chromium browser is present. Unverified on real hardware.
- **Live input needs the window to be focused**, and browsers show a pad only
  after its first button press. The test screen says so in plain words.
- **Unsigned binaries warn.** Windows SmartScreen and macOS Gatekeeper show an
  "unknown developer" prompt until we sign. Signing is a separate decision for
  Jordan (see the card); the installers and updates are built so signing slots
  in at release.

## Rules that do not move

Native binds and the Steam Input wheel only. One press is one action; the shared
core refuses macros, turbo, repeats and chained inputs, and a test tries each.
No admin, no telemetry (the update check is opt-in and sends nothing about the
player), MIT, public repo. CI on Windows, macOS and Linux (x64 and ARM) blocks
any release; claims about real hardware stay "unverified" until a person tests.
