# PokeMMO Controller foundation

Status: draft for Jordan's approval. Once approved, this file is the permanent foundation. Only a decision record approved by Jordan can change it (see section 8).

Date: 2026-11-18. Applies from version 2.0.0.

---

## 1. Decision

PokeMMO Controller 2.0 is built on one Rust engine, and both the desktop app and the `pmc` command line tool use that engine. This replaces the Go helper as well as the Python tools.

- **App window:** Tauri v2. The screens are plain TypeScript, CSS and web components, with no UI framework.
- **Controller input:** read natively through SDL3, the same controller library PokeMMO uses. The browser Gamepad API is not used.
- **Install and update:** signed per-user installers for Windows, macOS and Linux/Steam Deck. They update in one click and roll back on their own if an update fails.
- **Shared contracts:** a set of contracts that stay the same whatever language they are written in. These are the golden test files, versioned schemas, the CLI contract, a signed update manifest and one design-token source. Everything else is built on top of them.

The product rules do not change. The tool writes only PokeMMO's own controller binds and an optional Steam Input wheel layout. One press does one thing. There are no macros, no turbo, no injection and no virtual-gamepad driver.

Yes, this is a switch away from Go. The Go helper is a spike at about 25 to 30 percent of the product, so switching costs the least it ever will. Its logic is reused as a line-by-line reference for the port.

## 2. Why

### 2.1 The evidence

1. **Controller input is the deciding factor, and only Rust has a mature native option.**
   - Rust can use SDL3 through `sdl3-sys`, which tracks SDL 3.4.x (https://crates.io/crates/sdl3-sys). It also has `gilrs` 0.11 (https://docs.rs/gilrs/latest/gilrs/).
   - Go has no mature cross-platform controller library. `go-xinput` is archived and covers XInput only (https://pkg.go.dev/github.com/harry1453/go-xinput). The only way for Go to match is SDL3 through young purego bindings, which are not yet stable (https://pkg.go.dev/github.com/zyko0/go-sdl3).

2. **SDL3 reads controllers the way PokeMMO does.**
   - Our binds already use SDL3 positional numbers: 15 buttons and 6 axes.
   - SDL3 has HIDAPI drivers for PlayStation, Switch Pro, Steam Deck, the 2026 Steam Controller, Xbox and others (https://github.com/libsdl-org/SDL/tree/main/src/joystick/hidapi).
   - It hides Steam's virtual pads unless Steam launched the app (https://discourse.libsdl.org/t/sdl-only-use-steam-virtual-gamepads-if-were-running-under-steam/55028).
   - It can read input without window focus (https://wiki.libsdl.org/SDL3/SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS).

3. **The browser Gamepad API is not good enough, even though its bugs are fixed.**
   - WebKit bug 258264 is fixed (https://bugs.webkit.org/show_bug.cgi?id=258264).
   - It still only works in the focused view, and only after the first press.
   - It depends on how each Linux distribution built WebKitGTK (https://lists.buildroot.org/pipermail/buildroot/2021-June/312339.html).
   - It gives no vendor or product IDs and does no Steam filtering.
   - The CLI tester needs native input anyway.

4. **The app shell, updater and installer bundler are all native to Rust.**
   - Tauri's updater requires signatures, and they cannot be turned off (https://v2.tauri.app/plugin/updater/).
   - Its NSIS installer is per-user by default (https://v2.tauri.app/distribute/windows-installer/).
   - Velopack, the fallback updater, has a Rust SDK and no Go SDK (https://docs.velopack.io/).

5. **One shared source for brand and screens.**
   - The remap screen, the website and the brand CSS are already HTML/CSS. A webview app shares one token CSS file with the site.
   - It is also the stack that AI agents and new contributors know best.

6. **Rust's compiler protects the riskiest code: exact restore, the three-way uninstall merge and legacy detection.**
   - Plan operations become exhaustive enums, so a new file kind cannot be added without its uninstall branch.
   - Records are typed and refuse unknown keys.
   - An ignored error does not compile.

7. **The existing goldens carry over unchanged.**
   - The 7 golden parity files plus `binds-default.txt` already act as a specification that any language can replay.
   - Rust replays them exactly as Go does today.

### 2.2 How the options were judged

Three independent judges reviewed three full proposals:

| Proposal | Stability and upkeep | What players see | Security | Average |
|---|---|---|---|---|
| Rust + Tauri v2 (chosen) | 8 | 7.5 | 7 | 7.5 |
| Rust + Slint + Velopack | 6.5 | 8 | 7.5 | 7.3 |
| Keep Go + Wails v3 | 5 | 5.5 | 5 | 5.2 |

**Rust + Slint + Velopack (runner-up, 7.3).**

It was the best on Linux and Steam Deck. It has no WebKitGTK, its app is a few MB, and it looks the same on every OS. Its signed-manifest and rollback design was the strongest, and much of it is adopted here.

It lost for three reasons:
- Slint's licence is GPL-3.0 or royalty-free with required attribution. Neither is MIT, and both likely rule out free SignPath signing, which requires OSI licences with no commercial dual-licensing (https://signpath.org/terms).
- Its `.slint` language would duplicate the site's CSS, so the website and the app would stop sharing one source.
- Agents and new contributors know `.slint` far less well than HTML and CSS.

Because the UI sits behind a typed bridge, a native shell such as Slint can still replace Tauri later without touching the engine.

**Keep Go + Wails v3 (5.2).**

It keeps about 3,700 lines of Go and builds fast. But it bets the two riskiest new parts on the least mature options:
- Wails v3 has been stable for about three weeks (https://github.com/wailsapp/wails/releases).
- Input would go through a hand-written purego binding to SDL3. A mistake there crashes the app instead of failing to compile.

It also locked a loopback HTTP API that can install and update as a permanent contract. That is a standing local attack surface.

The webviews are the same as Tauri's, so Go saves nothing at the UI layer. The 3,700 lines are about 40 percent of the pure core and are reused as a reference either way.

### 2.3 Corrections from review

Skeptic reviews disproved several claims in the first draft. This document includes the fixes:
- A "what PokeMMO sees" view must be simulated. It cannot be observed.
- Rollback needs a watchdog process.
- Update manifests must be signed as a whole.
- Python 1.3 needs a bridge release before any Rust beta.
- The Deck needs specific handling.

Sections 3, 5 and 7 carry these fixes.

## 3. The bedrock (LOCKED)

Everything in this section is locked. Within a major version, changes may only add. Removing or renaming anything needs a decision record (section 8), a migration that still reads the old form, and a new golden file.

All locked contracts live under `spec/`:
- `spec/schema/`: JSON Schemas.
- `spec/golden/`: golden files, which move here from `tests/golden/`.
- `spec/cli/`: CLI transcripts.
- `spec/fixtures/`: sandbox file trees.

A change under `spec/` needs the `spec-change` label and Jordan's approval as CODEOWNER.

### 3.1 Product rules

1. **What it writes.** The tool writes only these:
   - PokeMMO's own native controller binds in `config/main.properties` (`client.controls.controller_input_maps_gdx_2` and `client.input.controllers.enable_native_support`);
   - the keyboard binds the wheel needs (`client.controls.gdx.*`);
   - a Steam Input layout, its configset block and the PokeMMO non-Steam shortcut.
2. **One input, one action.** One press of one input does one game action. There are no macros, turbo, sequences or chords.
3. **Nothing in the game process.** No injection into the game, no virtual-gamepad driver, no overlay drawn over the game. The wheel is drawn by Steam Input itself.
4. **Fixed inputs.** The right stick is reserved for the wheel. Triggers count only when pulled.
5. **Never forces a close or acts as admin.**
   - It never kills PokeMMO. It asks the player to close it, then offers to relaunch it.
   - It refuses to touch Steam files while a Steam game is running.
   - It refuses to run as root or admin.
6. **Clean uninstall.** Uninstall restores the exact original bytes when a file is unchanged since install. Otherwise it removes only our entries and keeps everything the player or Steam added.
7. **No telemetry.** The only network call is the update check (3.6), and it can be turned off.
8. **Read-only input.** Input reading changes nothing on the controller:
   - enhanced reports stay on `auto`;
   - lightbar, LED and rumble hints are off;
   - input is opened only while the live view, remap or `pmc input` is active, never in the background follower.
9. **Unofficial, said once.** The footer and the About text say the tool is unofficial, in the wording from `brand/VOICE.md`.

### 3.2 Engine boundary and API (`pmc.engine/1`)

One Cargo workspace holds these crates. Each has one job.

| Crate | Job | Rule |
|---|---|---|
| `pmc-core` | Game model tables, profile validation and migrations, `.properties` codec, native map grammar, text and binary VDF codecs, wheel VDF, Plan/Record model, uninstall merge, follower maths | Pure. No I/O, no `unsafe`. |
| `pmc-fs` | Atomic writes, backups, SHA tracking, plan commit | The only crate that writes user files. |
| `pmc-platform` | Finding PokeMMO and Steam, processes, RunningAppID, Steam stop/restart, window measurement, login entries, Deck/gamescope detection | Behind a `Platform` trait with a `FakePlatform` for tests. |
| `pmc-input` | Wrapper over `sdl3-sys` that produces `InputFrame` | Only this crate and `pmc-platform` may use FFI. |
| `pmc-engine` | Install, update, repair, uninstall, doctor, apply-profile, follow; Steam restart sequence; engine lock | Has no Tauri dependency. |
| `pmc-api` | Serializable DTOs and generated JSON Schemas | The contract the app and the CLI share. |
| `pmc-update` | Signed manifest, channels, rollback store, watchdog, self-test | |
| `pmc-cli` | The `pmc` binary | Thin. Writes no files itself. |
| `src-tauri` | App adapter: maps engine calls to Tauri commands and events | Thin, about 300 lines. |

**The contract is the DTOs, not the Rust internals.** The DTOs are:
- `Discovery`, `Status`, `Intent` (Install, Update, Repair, Uninstall, ApplyProfile, ResetProfile, SetScreen, Follow);
- `Plan` (a list of `FileChange {path, kind, before_sha, after_sha, reason}` plus `needs_steam_restart` and `refusals`);
- `Report`, `DoctorFinding`, `InputFrame`, `Event`.

Their JSON Schemas are generated, committed to `spec/schema/`, and checked in CI. A removal fails the build.

**Rules:**
- Every write goes plan, then preview, then commit with consent, through one engine.
- A per-install lock file, `config/pokemmo-controller.lock`, makes the app, CLI, follower and updater take turns, so there is only ever one writer.
- The app talks to the engine in-process. There is no loopback HTTP server.
- The frontend has no filesystem or shell access. Tauri capabilities allow only our commands and the updater, single-instance and opener plugins.

### 3.3 Profile and layout schema (`pmc.profile`), so remaps survive every update

- **Format 1** is today's layout file: `format`, `name`, `binds`, `wheel`.
  - It is readable forever.
  - Its validation rules and exact error messages are locked: unknown keys refused, duplicate keys refused, 64 KB maximum, right stick reserved, triggers only with `positive: true`, exactly 10 unique wheel ids.
- **New formats get a new number and are never edited in place.**
  - Format 2 adds `"$schema"`, `"format": 2` and optional metadata (an id, the version that created it, a pad hint).
  - Every later field also needs a new format number.
- **Migrations are pure functions in `pmc-core`**, one step at a time (vN to vN+1).
  - Each has frozen fixture pairs in `spec/golden/migrations/`.
  - Fixtures may only be added, never edited.
- **Newer files.** A file with a newer format opens read-only with the message "Made by a newer PokeMMO Controller."
- **Locked identifiers.** Action ids (`KEY_UP` to `KEY_SCREENSHOT`), wheel ids and SDL positional input numbers are frozen.
- **Share code.**
  - `PMC1-` is locked: base32 of 20 action bytes, 10 wheel bytes and a CRC.
  - Any future form uses `PMC2-`, and `PMC1-` stays readable.
- **Where profiles live.**
  - Presets and saved profiles live in the app config folder (`<config>/profiles/*.json`), never in PokeMMO's folder.
  - The active profile is copied into the install record **as format 1, forever**. This lets older tools still read the record (see 7.2).

Rule for every update: user remaps live in the install record and the profile store. An update re-applies them, never replaces them, and a golden test proves it.

### 3.4 Install record (`pmc.record`)

- **Path:** `<PokeMMO data>/config/pokemmo-controller.json`, sorted and indented by 2.
- **Version 2** adds `"record_format": 2`.
  - A record without that field is version 1 and is read by today's rules.
  - A missing record means a v1.0 install.
- **Locked keys.** These keys keep their meaning forever: `version`, `files {path: {sha, pristine, created}}`, `names`, `extra_names`, `switch_positional`, `layout`, `screen`, `screen_manual`, `follow`, `autostart`, `app`, `shortcuts_added`, `created_dirs`. Fields may only be added.
- **A newer `record_format` makes the engine refuse to write.** Uninstall still works from the `files` data alone.
- **These strings are locked**, because uninstall must recognise them forever:
  - the backup suffix `.bak-pokemmo-controller`;
  - the bind entry grammar;
  - the 27 pad names (append-only);
  - the log regex;
  - the wheel VDF template;
  - the configset block `"pokemmo" { "autosave" "1" }`;
  - the shortcut fields with `AppName` `PokeMMO`;
  - the appid recipe;
  - the controller type list (append-only);
  - the legacy "ours" detectors.

### 3.5 CLI contract (`pmc.cli/1`)

**Binary:** `pmc`.

**Commands:**

```
pmc install | uninstall | repair | status | doctor
pmc update [--check] [--channel stable|beta]
pmc remap {set, clear, import, export, reset}
pmc profile {list, show, use, save, import, export, delete, share}
pmc input [--json]                 # live input tester
pmc wheel {size, reset}
pmc follow [--once]
pmc config {get, set}
pmc version
```

**Global flags:** `--dry-run`, `--json`, `--yes`, `--pokemmo PATH`, `--steam PATH`, `--quiet`, `--no-color`.

**Exit codes (locked):**

| Code | Meaning |
|---|---|
| 0 | OK, including "already up to date" |
| 1 | Failed |
| 2 | Usage error |
| 3 | Blocked, needs user action (PokeMMO running, a Steam game running, Game Mode deferral) |
| 4 | Refused by product policy (a macro or a shared input) |
| 5 | Not found (PokeMMO or Steam) |
| 6 | Data made by a newer version |
| 7 | Update verification failed, nothing changed |
| 10 | Update failed and was rolled back |

**JSON output:**
- `--json` prints one envelope: `{"schema":"pmc.cli/1","command","ok","data","warnings":[],"error":{"code","message"}}`.
- Streams (`input`, `follow`) print NDJSON frames.
- Error codes are a stable list, for example `POKEMMO_NOT_FOUND` and `STEAM_GAME_RUNNING`.
- Human wording follows `VOICE.md` and may change. Codes and JSON shapes may not.
- `trycmd` transcripts in `spec/cli/` enforce all of this.

**Compatibility:**
- The 1.x flags (`--layout`, `--reset-layout`, `--no-wheel`, `--name`, `--switch-positional` and the rest) are accepted as aliases through all of 2.x.
- The messages "Installed vX", "Updated from vA to vB" and "Already up to date" stay.

### 3.6 Update manifest, signing keys, rollback (`pmc.update/1`)

**Manifest:**
- A static file at `https://pokemmocontroller.com/update/v1/{channel}/{target}-{arch}.json`, with a detached minisign signature beside it.
- The whole document is signed, not only the artifacts. `pmc-update` checks the signature before reading any field.
- Fields: `schema`, `channel`, `version`, `seq` (always increasing), `expires`, `released`, `notes_url`, `min_record_format`, `retracted[]`, and per artifact the URL, size, SHA-256 and Tauri signature. There is also a `cli` entry.
- The client refuses a manifest whose `seq` is lower than the last one it saw, or that has expired. An expired manifest only stops update checks. It never blocks using the app.

**Downgrades:**
- Tauri's `requireSignedVersion` is on and `allowDowngrades` is off.
- The server can never push a downgrade. The only downgrade path is the local rollback store.
- Retracting a version stops it being offered and shows a banner. It does not downgrade anyone automatically.

**Keys:**
- There is an online release key and an offline root key, and both public keys are embedded in every binary.
- The online key lives in a GitHub environment that needs a reviewer's approval.
- Jordan holds the offline root key on a hardware token, with a sealed backup copy.
- A new release key counts only when both keys co-sign it, and it ships one release before it signs anything.
- A written key ceremony and break-glass procedure live in `docs/release-keys.md`.

**Rollback:**
1. Before installing, `pmc-update` saves a copy of the current install outside the install folder:
   - the signed `setup.exe` of the current version on Windows;
   - the `.app` bundle on macOS;
   - the AppImage file on Linux.
   It also snapshots every managed user file and the install record through the engine.
2. A small watchdog binary, copied to `<data>/rollback/`, starts detached.
3. The new version runs a self-test: the engine loads, the record migrates, and `doctor` re-plans to zero pending changes. Only then does it write a `healthy` marker and re-apply binds and the wheel from the record.
4. If the marker is missing after the time limit, or there are two failed starts, the watchdog does three things:
   - restores the saved copy and the file snapshot;
   - adds the version to a local list of bad versions;
   - reports exit code 10 the next time the app or CLI runs.
5. A CI test on Windows, macOS and Linux installs vN, updates to a deliberately broken vN+1, and expects vN back. Stable auto-update does not ship until this test passes.

**Update check:**
- At most once a day, with no ID, cookie or query string.
- Never in `--json` or non-interactive CLI runs.
- Turned off with the setting, `pmc config set update.check off`, or `PMC_NO_UPDATE_CHECK=1`.
- Installs managed by a package manager (winget, Scoop, Homebrew, AUR) have self-update turned off and say "Update with <manager>".

### 3.7 Canonical tokens and glossary (`pmc.canon`)

**Sources:**
- `brand/tokens.json`, in W3C Design Tokens format 2025.10 (https://www.designtokens.org/tr/2025.10/), with light and dark modes. It holds colours, type stacks, spacing, radius, breakpoints, and wheel and art sizes.
- `brand/fonts/`: bundled woff2 files used by both the site and the app.
- `brand/glossary.json`: `term_id`, `display`, `plural`, `definition`, `forbidden_synonyms[]`.
- `brand/strings/en/*.ftl`: user-facing strings (Project Fluent) that refer to glossary ids.
- `site/data/hotspots.json`: real-photo hotspots in normalized 0 to 1 coordinates.
- `brand/art.json`: photo ids and source hashes.
- The tables exported from `pmc-core`: actions, wheel actions, pad labels, default binds.

**Generator:** `cargo xtask canon` writes:
- the shared CSS for site and app (one file);
- the Rust colour constants for the CLI;
- the README tables between `<!-- generated:NAME -->` markers;
- the banner SVGs;
- the photo derivatives.

**Drift check:** `cargo xtask canon --check` is the CI gate. It fails on any hand edit to a generated file, and on any forbidden synonym in the README, site, app strings or CLI strings.

**Art rule:** real photos plus hotspots, never drawn controllers (from `CONTRIBUTING.md`).

### 3.8 Identifiers that never change

- The app id `com.pokemmocontroller.app`.
- The product name.
- The data folder names and the login entry names.
- The record path.
- The update URL paths and channel names `stable` and `beta`.
- The sandbox test variables `POKEMMO_CONTROLLER_TEST` and `*_TEST_*`.

## 4. Built on top (FREE TO CHANGE)

These can change in any release without a decision record, as long as they keep to section 3:

- The look of the app: layout, screens, colours chosen from the tokens, motion, wording in line with `VOICE.md`.
- App features:
  - live view details;
  - the wheel editor;
  - presets and how they are listed;
  - undo and redo;
  - the first-run wizard steps;
  - controller focus navigation;
  - "couch mode" (larger type and focus rings when fullscreen or under gamescope).
- The website: content, pages and build steps, as long as it reads the canon.
- Which presets ship, and their names.
- Doctor checks: new checks may be added freely.
- CLI human wording and help text.
- Package manager listings, and adding new ones.
- Internal crate structure below the DTOs.
- The UI shell itself (Tauri 2.x to 3.x, or a native shell), because the frontend only talks to `bridge.ts`, which is generated from `spec/schema/`.
- An optional `pmc serve --open` support mode that shows the same UI in a browser. It is off by default, protected by a token, and never part of the locked API.

## 5. Platforms and distribution

Every artifact comes from one release workflow, triggered by a tag, on GitHub Actions. Each gets a SHA-256, a minisign signature and a GitHub build provenance attestation.

| Platform | Installer | Updater | Signing | Package managers |
|---|---|---|---|---|
| Windows x64, ARM64 | Tauri NSIS `setup.exe`, per-user, no admin, WebView2 fetched only if missing. Ships the app, `pmc.exe` and `SDL3.dll`; adds `pmc` to the user PATH. | Tauri updater in quiet or passive mode, wrapped by `pmc-update` (signed manifest, watchdog rollback). An NSIS pre-install hook stops the follower and any `pmc.exe` first. | Unsigned (Jordan, 2026-11-18). SmartScreen shows "Windows protected your PC" until reputation builds; the site and README show "More info, then Run anyway". Each release is submitted to Microsoft Defender to head off false positives. The update manifest stays minisign-signed. | winget, Scoop (self-update off) |
| macOS universal | Unsigned, not notarized DMG (Jordan, 2026-11-18). The app asks to live in `~/Applications` so updates stay one click; `/Applications` works but a standard user then gets an admin prompt on update. `pmc` is linked from inside the bundle to `~/.local/bin`. | Tauri updater (`.app.tar.gz` + `.sig`), wrapped by `pmc-update`. | Unsigned. First launch is approved once in System Settings, Privacy & Security, Open Anyway; the site shows illustrated steps. The update manifest stays minisign-signed. | Own Homebrew tap only (the official cask list requires notarization). |
| Linux x64, ARM64 | AppImage built natively on Ubuntu 22.04. "Install for me" puts it in `~/.local/share/pokemmo-controller/`, adds a `.desktop` entry, and writes `~/.local/bin/pmc` as a shim that runs the AppImage with `--pmc`, so the CLI updates with the app. Bundled libwayland, libEGL and mesa are removed; the launcher falls back to `GDK_BACKEND=x11` and `WEBKIT_DISABLE_DMABUF_RENDERER=1`. Plain `pmc` tarball for headless use. | Tauri updater replaces the AppImage in place, wrapped by `pmc-update`. | minisign + provenance. | AUR `pokemmo-controller-bin`, `pmc-bin` (self-update off). No deb/rpm at first: Tauri can update them since 2.10, but only through pkexec or sudo, which is not per-user. |
| Steam Deck, Desktop Mode | Same AppImage and "Install for me", into `/home/deck`, which survives SteamOS updates (https://help.steampowered.com/faqs/view/671A-4453-E8D2-323C). Offers "Add to Game Mode". | Same as Linux. | Same as Linux. | None at first |
| Steam Deck, Game Mode | The app runs as a non-Steam shortcut, fullscreen and driven by the controller. If the week-1 spike shows FUSE AppImages fail as non-Steam games, the shortcut points at an extracted copy instead and `pmc-update` swaps a `current` link. Binds, live view, remap and doctor work here. Steam-file changes (wheel, shortcuts) are queued and finished at the next Desktop Mode start by a named autostart entry. | Through Desktop Mode. | Same as Linux. | None |

`install.sh` and `install.ps1` keep their URLs. They download a pinned, signed release and check it against something not fetched alongside the download:
- Windows, macOS and Linux: the SHA-256 values are pinned inside the versioned script, and the minisign signature is checked against the public key in the script (the apps are not code-signed: Jordan, 2026-11-18).

`gh attestation verify` is also offered. The scripts state plainly that a pipe-to-shell one-liner trusts TLS and GitHub. Python and uv are no longer needed.

A Game Mode commit that is deferred runs through `systemd-run --user`, so Steam's reaper does not kill it when the app closes.

Flathub is deferred. A Flatpak would need to do four things:
- reach into `~/.var/app/com.pokemmo.PokeMMO`;
- reach the Steam root;
- use `--device=all` for hidraw;
- run `flatpak-spawn --host` to restart Steam, which the Flathub linter flags (https://docs.flathub.org/docs/for-app-authors/linter, https://docs.flatpak.org/en/latest/sandbox-permissions.html).

That breaks "safely restarts them" and Flathub's minimum-permission rule. If it is ever listed, it will be a viewer that hands setup to the host `pmc`.

## 6. Live adaptation to resolution, aspect ratio and DPI

There are two parts, handled differently.

### 6.1 The app (fully ours)

- **Sizes.** All sizes are CSS logical pixels from the token scale, using `clamp()`, container queries and aspect-ratio media queries. Breakpoints come from the tokens:
  - compact covers the Deck at 1280x800 and narrow windows;
  - regular puts content side by side;
  - wide caps the photo by height.
- **DPI.** The webview applies the device pixel ratio. Tauri emits scale-factor and resize events when a window moves between monitors or the OS scale changes, and the layout re-flows with no restart.
- **Controller photos.** They sit in an aspect-locked frame with hotspots in normalized 0 to 1 coordinates, so they line up at any size.
- **Text** never goes below the token minimum.
- **Couch mode** turns on when fullscreen or under gamescope.
- **Visual test matrix.** Playwright renders the screens at 1280x800 @1, 1920x1080 @1, 2560x1440 @1.5, 3840x2160 @2, 3440x1440 and a portrait size, in light and dark, using both the Chromium and WebKit engines. A test fails on overflow or clipped hotspots.
- **CLI output** follows the terminal width, and falls back to plain text when output is not a terminal, when `NO_COLOR` is set, or with `--json`.

### 6.2 The wheel (Steam's)

Steam draws the wheel. We control only `touch_menu_scale`, the position and the opacity in the layout files.

**The formula is locked:** `wheel_scale = clamp(60, 400, round(400 * min(w, h) / 2160))`.

**The follower:**
- `pmc-engine` ports `fit.py` exactly, frozen in a new `follower-parity` golden:
  - drop zero, negative and odd samples;
  - drop sizes outside 320 to 16384;
  - drop aspect ratios over 8:1 and the 640x480 login window;
  - wait for 3 equal samples before acting;
  - skip changes under 4 percent.
- It runs inside the app's background mode, started at login: a Startup shortcut on Windows, a LaunchAgent on macOS, an XDG autostart entry on Linux.
- No system Python is needed, which fixes today's silent skip.
- The follower never opens controller input.

**Measuring the game picture:**

| Where | How |
|---|---|
| Windows | `EnumWindows` matched on the process image name, with a DPI-aware client rect. |
| macOS | `CGWindowListCopyWindowInfo` bounds for the PokeMMO process: the window, not the display. Whether this needs no permission is to be confirmed on hardware. |
| Linux X11 and XWayland | `x11rb`. No `xwininfo` dependency. |
| Deck Game Mode | The gamescope output size. The game fills it. |
| Native Wayland | The output size, labelled as an estimate in doctor. |

**Not yet verified:** whether Steam reloads a rewritten layout while PokeMMO is running. No Valve document covers it. Week 1 tests it on hardware. If Steam does not reload, the wheel resizes before launch (`pmc follow --once` from the shortcut's launch options), and the Wheel tab says "Size updates the next time PokeMMO starts from Steam." The site makes no promise until this is tested.

## 7. Migration plan

Python 1.3.x stays the shipping product and the source of truth for behaviour until Rust matches it byte for byte. No user loses their setup at any step.

### 7.1 What is reused and what is ported

**Reused unchanged:**
- the 7 golden files and `binds-default.txt`;
- the layout format 1, the install record keys and the game and Steam file formats;
- the sandbox environment variables;
- `hotspots.json`, the real photos, `VOICE.md` and `DESIGN.md`;
- the CI matrix shape;
- `tests/ingame/checklist.json`.

**Ported:**
- From Go, line by line: layout, props, nativemap, plan, atomic, shortcuts, wheelvdf, layoutplan, and editor with its share code.
- From Python, which Go never had: `apply_native.plan`, `install_wheel` orchestration and keyboard binds, `uninstall.py`, `platforms.py`, the `setup.py` flow and messages, `fit.py`, the `app.py` login entries, and the `ui_page.html` screens.

**Retired:** the Go helper, the `fyne.io/systray` tray, the loopback remap server, `site/build.py`, `brand/build.py`, the Python and uv bootstrap, and installing from the main branch.

### 7.2 Milestones (in order)

Time estimates are rough and assume mostly agent work with Jordan available for hardware checks. They are recorded in decision 0001 and updated as each milestone closes.

**M0. Freeze contracts and close unknowns (about 1 to 2 weeks)**
- Write `docs/decisions/0001-rust-foundation.md`, which replaces `docs/helper-decision.md`. Create `spec/`.
- Generate the missing goldens from Python:
  - uninstall: exact restore, three-way merge, CRLF collapse, v1.0, the Focus Ring and Hotbar 5 swap, Nintendo face-only, pushed-trigger records;
  - follower sequences;
  - record migrations;
  - full sandbox before and after trees for install, rerun, update from each tag, and uninstall;
  - CLI transcripts;
  - share-code vectors from Go.
- Write JSON Schemas for profile, record, CLI and the update manifest.
- Convert `tokens.json` to the DTCG format with today's values.
- Write the illustrated first-run steps for unsigned Windows (SmartScreen) and macOS (Open Anyway).
- Run the hardware spikes:
  - Steam wheel hot-reload;
  - SDL3 pad names against PokeMMO's logged names on Windows, macOS and Deck;
  - which SDL build PokeMMO ships;
  - SDL on the main thread under Tauri on macOS;
  - a Tauri AppImage on a Deck in both modes, including as a non-Steam game.
- Where there is no Deck or Mac to test on, the platform stays labelled "unverified".

**M1. Python 1.3.1 bridge release (before any Rust beta)**
- It refuses to write when a record has `record_format` above 1 or a newer version, with the message "Made by a newer PokeMMO Controller. Use pmc."
- It can still uninstall such a record from the `files` data alone.
- `install.sh` and `install.ps1` are pinned to the v1.3.1 tag with a SHA-256 and a pinned uv version. They no longer pull the main branch or `uv latest`.
- 1.3.x gets fixes only from here on.

**M2. Pure core (about 2 to 3 weeks)**
- Port everything into `pmc-core` and `pmc-fs` against the goldens, plus proptest fuzzing (round trips and macro-sneaking).
- Gate: every golden passes in Rust. The Go helper and its CI job are then deleted.

**M3. Platform, engine and CLI (about 3 to 4 weeks)**
- Build `pmc-platform`, `pmc-engine` and `pmc`.
- Point the existing 36 Python test modules at the binary with `PMC_BIN`.
- Run the same scenarios through Python and Rust, and require byte-identical file trees.
- Test that each can uninstall the other: Rust removes a Python install, and Python 1.3.1 removes a Rust install.
- CI checks out with `fetch-depth: 0`. The upgrade tests from v1.0.0, v1.1.0, v1.2.0 and v1.3.x fail, not skip, when tags are missing.
- **Hard gate:** no Rust build writes to a real user file until all of this passes.
- Ship `2.0.0-beta.1` as the CLI and bare archives on the beta channel, opt-in through `PMC_CHANNEL=beta`.

**M4. Input and app (about 4 to 6 weeks)**
- `pmc-input` over `sdl3-sys`:
  - On macOS it runs on the main thread, pumped from a Tauri `run_on_main_thread` timer. If that fails, a `pmc input --json` child process is the documented path.
  - `gilrs` with the `xinput` feature is the fallback on Windows, macOS and desktop Linux only. It is not used for the Deck's built-in controls while Steam runs, because hid-steam removes their evdev node.
- The app:
  - first-run wizard;
  - live view;
  - remap by click then press;
  - presets, wheel, status/doctor, repair, reset, uninstall, settings;
  - controller focus navigation.
- The live view has two clearly labelled parts:
  - the input the app actually receives, with a badge: "Raw controller" or "Through Steam Input (this app's layout)";
  - "Simulated: PokeMMO via Steam", a pure `pmc-core` function (with its own golden) that maps a physical frame through the Steam layout and binds we write.
- When Steam is running and did not launch the app, the app offers "Open through Steam", because Steam's Desktop Layout would otherwise send every press twice. Until then, focus navigation ignores keyboard or mouse events that arrive within about 50 ms of a pad event, and doctor reports "Steam Desktop Layout active".
- Doctor reports:
  - the input path (HIDAPI, evdev or virtual);
  - PokeMMO's SDL version compared with ours, warning on a mismatch;
  - which `shortcuts.vdf` each Deck mode reads.

**M5. Release machinery (about 2 to 3 weeks)**
- Signing, minisign keys and the key ceremony.
- Signed manifests, channels, the watchdog rollback, and the broken-canary CI test on three OSes.
- Package manager manifests generated by CI.
- `install.sh` and `install.ps1` switch to the signed Rust release.
- On an existing install, the first Rust run prints "Updated from v1.3.x to v2.0.0", migrates the record to version 2, and keeps the custom layout (still format 1 inside the record).

**M6. 2.0.0 stable**
- Gate: the hardware matrix passes using `tests/ingame/checklist.json`. Each row must show the live view matching the simulated view and PokeMMO's in-game response:
  - Windows with Xbox, PS5 and Switch Pro, each with Steam running and closed;
  - macOS;
  - desktop Linux;
  - Deck in Desktop Mode and Game Mode.

**M7. Retire Python**
- After one stable 2.x release with no parity bugs, delete `tools/*.py`, the `gen_*_golden.py` scripts and the Python build scripts.
- The goldens become frozen fixtures, extended only by `cargo xtask golden` with review.
- The 1.x CLI flags stay as aliases through all of 2.x.

## 8. Changing the foundation

The foundation changes only through a decision record at `docs/decisions/NNNN-short-title.md` that Jordan approves. A record states:
- the problem;
- the options considered;
- the evidence with links;
- the migration;
- how old data keeps working;
- the undo.

A change is foundational, and needs a record, if it does any of these:
- Changes a product rule in 3.1.
- Removes or changes the meaning of anything under `spec/`: schemas, goldens, CLI commands, flags, exit codes, error codes, JSON shapes.
- Changes the engine language, the engine crate boundaries in 3.2, or lets a front end write files.
- Changes how user data is stored, migrated or restored, or lets an update lose a remap.
- Changes the update manifest, signing keys, key custody, channels or rollback rules.
- Changes the canon source format, or where tokens and the glossary live.
- Changes any identifier in 3.8.
- Adds a network call, a new kind of file the tool writes, or a new permission.
- Replaces SDL3 as the input source, or the per-user installer model.

These are not foundational and need no record:
- anything in section 4;
- new golden cases for new behaviour;
- new doctor checks;
- new optional fields in a new format number;
- dependency updates inside a pinned major;
- moving to Tauri 3, if the bridge and DTOs stay the same. This needs a note in `CHANGELOG.md`.

Agents follow `CONTRIBUTING.md` recipes ("add a pad name", "add a wheel action", "add a doctor check") and never edit `spec/` without the `spec-change` label.

## 9. Decisions (Jordan, 2026-11-18: "approve with defaults, no signing")

| Decision | Decided |
|---|---|
| Windows code signing | None. Ship unsigned; document the SmartScreen "More info, then Run anyway" step; submit releases to Microsoft Defender. |
| macOS signing and notarization | None. Ship unsigned; document "Open Anyway" in Privacy & Security; own Homebrew tap only. |
| Update signing (minisign, free) | Kept. Every update manifest and artifact is signed; the app refuses unverified updates. This is not OS code signing. |
| Offline root key | Hardware token held by Jordan plus a sealed backup; written break-glass step. |
| Steam layout for the app's own shortcut | Yes: a passthrough layout, removed on uninstall. |
| "Add to Game Mode" shortcut | Yes, as an opt-in button. |
| Test hardware | At least a Steam Deck and a PS5 pad before 2.0 stable; the rest labelled "unverified". |
| Flathub | Deferred. |
| Release approval | Betas publish automatically; stable needs Jordan's approval. |
| Primary colour | #F0EA6B (Jordan, earlier the same day). |

Code signing can be added later without changing the foundation: it is a release-pipeline step, not a locked layer.

## 10. Risks and mitigations

- **Primary colour #F0EA6B (decided by Jordan 2026-11-18).** It is PokeMMO's own logo yellow, so the tool could look official. Mitigation: keep the unofficial / not-affiliated note on every surface, never reproduce the PokeMMO logo or wordmark, and on light backgrounds use the yellow only as a fill behind dark text (it is 1.26:1 as text on white).


| Risk | Mitigation |
|---|---|
| Steam may not reload a rewritten wheel layout while the game runs. | Hardware test in M0. If it does not, resize before launch and show a plain hint. Make no promise until tested. |
| The uninstall merge and legacy detection are the riskiest code to rewrite. | New uninstall goldens in M0, byte-identical Python and Rust trees, cross-uninstall tests, and a hard gate before any real file is written. |
| Python 1.3 could overwrite a Rust install. | The 1.3.1 bridge release refuses newer records. The record's layout stays format 1. |
| SDL pad names could differ between our SDL and PokeMMO's, so binds miss. | Doctor compares against PokeMMO's logs and SDL version. Keep a golden of names per SDL version. Pin our SDL to PokeMMO's minor where possible. |
| SDL Rust bindings churn: the `sdl3` crate has had 18 breaking releases out of 93. | Bind `sdl3-sys` only, behind our own small wrapper. SDL's 3.x C ABI is stable. |
| Steam's Desktop Layout sends each press twice when the app runs outside Steam. | Offer "Open through Steam", filter echoes in focus navigation, and report it in doctor. |
| The "what PokeMMO sees" view could mislead. | It is a labelled simulation from the files we write, checked against in-game results in the hardware matrix. |
| SDL's HIDAPI drivers can change controller state (enhanced reports, Deck lizard mode). | Enhanced reports on `auto`, LED and rumble hints off, input open only while needed, never in the follower. |
| macOS input threading under Tauri is not yet tested. | SDL on the main thread through `run_on_main_thread`. A child-process fallback is documented. |
| WebKitGTK problems on Linux and Deck: 70 MB+ AppImage, blank windows, EGL crashes on Arch-based systems. | Strip bundled graphics libraries, use launcher environment fallbacks, test on a Deck before stable, and keep `pmc` (no webview) as the guaranteed install, repair and uninstall path. Refresh the bundled WebKitGTK with every release. |
| FUSE AppImages may fail as non-Steam games in Game Mode. | Test in M0. If they fail, launch an extracted copy and let `pmc-update` swap a `current` link. |
| Steam's reaper kills child processes in Game Mode. | Deferred commits run through `systemd-run --user`. An autostart entry finishes them in Desktop Mode. |
| Tauri's updater has no rollback or channels. Our rollback code is on the critical path. | Watchdog, file snapshot, local bad-version list, and a broken-canary CI test on three OSes before stable auto-update. |
| A stolen website or a replayed manifest could push a bad update. | Whole-manifest signature with `seq` and `expires`, no server-driven downgrade, two-key custody. |
| The follower or CLI locks files during a Windows update. | The follower runs inside the app, which Restart Manager covers. An NSIS pre-install hook stops it. The engine lock file blocks updates while a write is in progress. |
| Tauri 3 will arrive within five years. | The engine has no Tauri dependency, the bridge is generated from our schemas, and the manifest is our own. One planned shell migration. |
| Unsigned apps: SmartScreen and Gatekeeper warnings cost some installs, and antivirus false positives are likelier. | Clear illustrated first-run steps on the site and README, checksums and minisign signatures shown beside downloads, reproducible CI builds with provenance attestations, each release submitted to Microsoft Defender. Code signing can be added later as a pipeline step. |
| One person holds every signing identity. | Write the key ceremony and break-glass procedure, and name a backup holder for the offline key. |
| The Rust and full Tauri build is heavy on the 3-core, 4 GB agent box. | Core crates build and test without Tauri in seconds. Use `-j2`, mold and sccache locally. Full app builds and bundles run only on GitHub runners. |
| Rust raises the bar for casual contributors. | Small pure crates, `CONTRIBUTING.md` recipes, and UI work in TypeScript and CSS. |
| PlayStation, Switch Pro, macOS and Deck have never been played with this tool. | The hardware matrix gate before 2.0 stable. Platforms that are not tested stay labelled "unverified" on the site and in doctor. |
| PokeMMO or Steam could change their file formats. | Refuse anything that does not round-trip exactly, add doctor checks, and add new golden cases with a version note. |