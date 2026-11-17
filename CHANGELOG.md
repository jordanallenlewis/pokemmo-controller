# Changelog

## Unreleased

- Changed: the installers print, and the remap screen shows, one plain line: PokeMMO Controller is an unofficial, fan-made tool, not made, endorsed or supported by the PokeMMO team.
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
