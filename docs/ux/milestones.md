# Plan: from one-line installers to a signed 2.0

Each milestone ships as reviewable PRs. A milestone ends with a beta
pre-release, tested in CI on every system and run on the in-game test rig.

| | Milestone | Done when |
|---|---|---|
| A0 | **Plan** (this folder) | Decision, plan and friction list merged |
| A1 | **Installer MVP** | Finish the Go installer core (install, update, uninstall, same safety as today: one backup per file, atomic writes, byte-for-byte restore). One download per system (Windows `.exe`, macOS `.dmg`, Linux `AppImage`) with checksums, built in CI. It finds PokeMMO and Steam, closes and restarts them safely, writes binds for every controller name the game uses, sets up the wheel, verifies the result and opens the app on its test screen. Per-user, no admin. Fresh-machine tests on every leg. Beta 1. |
| A2 | **App with live input** | New interface (React, brand tokens). Auto-detected controller with the right art (Xbox, PlayStation, Switch Pro, Deck), several pads handled. Buttons light up, sticks and triggers move, and each press shows the game action it triggers. Beta 2. |
| A3 | **Remap** | Click an action, press the button, see conflict warnings. Presets, reset to default, apply and save, a "test in game" checklist, uninstall and repair inside the app, opt-in update check. Macro refusal enforced and tested. Beta 3. |
| A4 | **Polish** | Keyboard and controller navigation, readable sizes, cold start under 1 second, Steam Deck add-as-non-Steam-app flow, Flatpak, visual checks at every width in light and dark, in-game rig run. |
| A5 | **Signed 2.0** | Windows and macOS builds signed and notarised once Jordan has chosen (see the card), updater verifies signatures, release notes list the CI legs that passed. Release is announced only with real-device results. |

Order inside A1: (1) finish the Go core (install_wheel plan, props, shortcut
target per system, uninstall side) with the existing golden parity tests;
(2) `setup` command that does detection, close and restart, verify; (3) packaging
jobs per system; (4) fresh-machine and failure-injection tests; (5) README says
"download" first and keeps the one-liners under Advanced.

Needs Jordan: code signing (cost and identity), a Steam Deck or Windows PC
session for the "unverified" claims. Everything else is decided.
