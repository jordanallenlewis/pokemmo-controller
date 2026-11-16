# Changelog

## Unreleased

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
