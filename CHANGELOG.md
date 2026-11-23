# Changelog

## Unreleased

- README: Troubleshooting says what to do when a window loses focus or the stick cannot reach a
  button (the Focus Ring first; the two reported screens that still need a mouse click until cursor mode).
- Fixed: the installer now finds PokeMMO unzipped from its portable ZIP in Downloads, Desktop or
  Documents (the `PokeMMO-Client` folder "Extract All" makes, translated folder names on Linux, OneDrive
  on Windows) and the Debian/Ubuntu installer's `~/.local/share/pokemmo`. A real install or a Steam copy
  still comes first.

## 1.2.1 - 2026-11-19

This release carries the update files the app needs: from here on the app can tell you a new version is out and install it for you.

- New: the app tells you when a new version is out, with a short "what's new" and one button,
  Update now. It checks when it opens and about once a day; nothing about you is sent, and you
  can turn it off in Settings. A beta channel is there if you want new versions early.
- New: the update is checked against a signature before anything is installed, keeps your own
  remaps and layout, and puts the old version back by itself if anything goes wrong.
- New: from a terminal, `setup.py --update --check` says whether there is one and `--update --yes` installs it.
- New: `pmc`, the command line for people who prefer a terminal: `pmc status`, `pmc doctor`,
  `pmc install` and `pmc uninstall` (with `--dry-run`, `--yes` and `--json`; `--json` prints the one fixed envelope, and the exit codes are fixed too), and
  `pmc app` to open the remap screen. It runs the same code as the remap screen and the installers.
- Safety for 2.0: if a newer PokeMMO Controller made your install, this version no longer
  writes over it. Installing, updating, the remap screen and the helper at login stop with
  "Made by a newer PokeMMO Controller. Use pmc." and change nothing. Uninstall still puts
  back every file that nothing else changed since, and names any it leaves.
- README: Troubleshooting says to put a pad back on its default profile if buttons were swapped
  in the maker's app, and "Is this allowed?" says to keep a pad's turbo button off.

## 1.3.0-beta.1 - 2026-11-17 (pre-release)

A beta of the zero-touch install work. The one-line installers fetch from `main`, so they already
install this. Tell us what breaks.

- New: the installer finds PokeMMO in any Steam library folder and on other Windows drives
  (D: to H:), as well as the Flatpak, snap and macOS places it already knew.
- New: the installer binds the controllers that are plugged in, found by name on Linux, macOS
  and Windows (Xbox, PlayStation, Switch Pro), instead of asking you which one you have. If it
  cannot tell, it keeps the default and says so.
- Tested: a computer with PokeMMO but no Steam gets the native binds only and no Steam folder;
  your own pad map is kept; installing twice changes nothing; install then uninstall restores
  every byte, with and without Steam. If you never started the game, the installer says
  "start PokeMMO once, close it, try again" and writes nothing.
- Changed: the README's button maps are now the website's own maps on the real controller photos
  (Xbox, PlayStation, Switch Pro, Steam Deck), in light and dark, with a table under each. The
  drawn outlines are gone. The Legion Go S has no map picture because there is no photo of it we
  may use.
- Fixed: the website's Switch Pro map showed B as the confirm button; the printed A confirms.
  The website's wheel now shows the empty top slice, like the game.

## 1.2.0 - 2026-11-17

- New: the wheel now follows the game's resolution by itself. The installer sets up a small
  background helper that starts when you log in (a Startup entry on Windows, a LaunchAgent on
  macOS, an autostart entry on Linux and Steam Deck), runs `--follow` quietly, runs once at a
  time, and ends on its own when you uninstall. It needs Python 3.9 or newer on the computer:
  the installer says so when there is none and the wheel then keeps the size it was made for.
  `--no-follow` skips it (remembered), `--follow-at-login` turns it back on. It sends no input.
- Changed: the remap screen is now an app-style screen in the project's own look (dark ink, one
  yellow accent; light theme follows your system). Click a button on the picture of your
  controller to change what it does, instead of choosing from a list of dropdowns; the wheel
  is drawn in the same style. Tabs for Layout, Wheel, Status and Settings; a setup checklist
  (PokeMMO found, controller detected, buttons applied, Steam wheel installed) with a
  one-click fix on each open step; a live status bar along the bottom. Press a button on your
  controller and it is picked on the screen (your browser reports the controller; nothing is
  installed). Each button still does one thing: giving a button an action another button has
  swaps the two, and Apply still backs up first and refuses anything else. New `brand/` folder
  holds the colours, mark, voice and design rules as one source.
- Fixed: the installer never looked at your screen, so unless you knew about `--resolution`
  the wheel came out at the 4K size and ran off a smaller screen. A plain install now
  measures the game picture (the PokeMMO window if it is open, otherwise your main screen)
  and sizes the wheel to it; running the installer again measures again. A size you gave
  with `--resolution` is kept until `--reset-resolution`. A 4K screen is unchanged.
- Changed: the top slice of the right-stick wheel now does nothing, so letting go of the
  stick while it points straight up presses no key. The other ten slices follow it
  clockwise, starting with the Pokedex, and still press one key each. (The empty slice
  has not been checked on a real Steam yet: tell us if the wheel looks wrong.)
- Changed: the installers print, and the remap screen shows, one plain line: PokeMMO Controller is an unofficial, fan-made tool, not made, endorsed or supported by the PokeMMO team.
- Fixed (Windows): `--follow` took the first window whose title began with "PokeMMO", so a
  browser tab or folder called "PokeMMO Forums" on top of the game made the wheel follow
  that window's size instead. It now reads the window of the PokeMMO program itself
  (the largest, if there are several), in fullscreen, borderless and windowed alike.
- Changed: **View** (Create on PlayStation, − on Switch Pro) now opens the map. PokeMMO has
  no controller action for the map, so View presses Hotbar 5: put the Town Map in
  hotbar slot 5 (of each page you use) once and View always opens it. The Focus Ring
  moved to **LB** (L1, L), which used to be Hotbar 5, so nothing else is lost. A rerun
  of the installer moves your binds; a layout you made in the remap screen is left as it is.
  The button maps in `docs/` and the remap screen show the new default.
- Fixed: a run stopped while it waited for a busy file (Windows cannot let it clean up)
  left a `name.XXXX.tmp` file in the Steam or PokeMMO folder. The next write clears old
  ones, and uninstall removes any next to the files it removes.

- New: `--follow` keeps the wheel sized while the game's resolution changes mid-play
  (4K, 1080p, 1440p and back, in any order; fullscreen, borderless or windowed;
  other monitor or display scaling). It rewrites only the wheel layout files once a
  new size has held for a moment, ignores a window that briefly reports 0x0 or half
  a size, and ends on the last size that held after a rapid string of changes. It
  sends no input. Whether Steam reloads the file with the game already running is
  not verified on real hardware; restart the game from Steam if the wheel keeps its old size.
- Fixed: the wheel was always drawn at the 4K size, so at a lower game
  resolution it grew until it ran off the screen. Add `--resolution 1920x1080`
  (the size of the game picture) and the wheel is sized to fit: the shorter side
  sets it, so ultrawide, 4:3, 720p and 4K all fit, and it never goes above the 4K
  size. It is remembered; `--reset-resolution` goes back. Steam reads the layout
  when the game starts, so run it again after you change the game's resolution.
  Without the flag, nothing changes from before.
- Remap screen: pick your controller (Xbox, PlayStation or Switch Pro) and
  every input shows that pad's own button names (on Switch Pro, following the
  installed A-confirms setting). It starts from a pad PokeMMO has logged on
  this computer. A button map of your layout on that pad sits below and
  updates as you pick; it is drawn by the same code as the pictures in `docs/`.
- Fixed: on Switch Pro pads, a layout made in the remap screen could put two
  actions on one button (for example Confirm and Bag both on the printed A).
  The swap that makes the printed A confirm now swaps whole buttons, so every
  button still does exactly one thing; a rerun repairs an earlier layout and
  uninstall still removes it. The default layout was never affected. A test now
  writes hundreds of random layouts for every pad name and fails if any input
  does two things.
- Fixed: the Switch Pro button map showed B as Confirm; it now matches what is
  installed (the printed A confirms, as on a Switch). `python tools/pads.py
  switch --switch-positional` prints the other setting. Actions left unbound in
  a layout are listed as "Not bound" instead of stopping the tool.
- More tests, nothing changes for players: a golden file of the exact binds
  PokeMMO reads for each pad family, a seeded fuzz that tries to sneak macros,
  repeats and shared inputs into a layout (every attempt is refused, never a
  crash), random valid layouts through install and uninstall byte for byte, and
  static checks of the remap page (no outside files or hosts, labels, text that
  scales, no macro controls). They run on every system in the CI matrix.
- Button maps for PlayStation and Switch Pro pads (`docs/button-map-*.svg`) and
  `python tools/pads.py [xbox|playstation|switch]`, which prints the default
  layout with that pad's button names. Made from the layout itself, so a test
  fails if the pictures drift from it. They are drawn outlines, and these names
  are the printed labels only: nothing about what is written to the game changed.
- README: an at-a-glance answer to "does it work with my pad and system, how long
  does it take, is it allowed", a picture of the remap screen, remap-screen
  troubleshooting and every option explained. A test now fails if a link or
  picture is missing or an option is left undocumented.
- Remap screen: change what each controller input does in your browser
  (`--ui`). It runs on your computer only, needs nothing installed, and applies
  through the same installer as everything else, so the backup and exact
  uninstall work the same.
- `--install-ui` (`-InstallUi`) keeps the remap screen on your computer with a
  launcher, so it opens with one short command. Uninstall removes it.
- Your own layout: `--layout FILE` installs a layout file, `--reset-layout`
  goes back to the default. Updates keep your layout.
- One input does one action, checked in code: a layout with a shared input, a
  repeat, a sequence, a delay or any extra field is refused, including a file
  edited by hand.
- CI runs every change on Windows (x64, ARM), macOS (Apple silicon, Intel),
  Linux (x64, ARM) and an Arch Linux image standing in for SteamOS.
