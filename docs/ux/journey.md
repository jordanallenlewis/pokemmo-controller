# First-run journey, per system

Last updated 2026-11-18. This is the path from "I saw a post" to "I'm in a
battle with my controller": every step, every choice the player has to make, and
every place a player who isn't technical could stall or get worried. Steps were
counted from the README and the installers as they are today (`v1.3.0-beta.1`).
"Tested" says how each path was tried; nothing here is claimed beyond that.

Target for every system: at most **4 steps** and **1 choice** before the first
battle, and a clear answer if something goes wrong.

Legend: **Step** = something the player does. **Choice** = something they have
to decide. ⚠ **Stall** = a likely place to get stuck. ⚠ **Worry** = a likely
place to get nervous and stop.

## Windows

| # | What happens | Kind |
|---|---|---|
| 1 | Click through from the post to pokemmocontroller.com or the GitHub page | Step |
| 2 | Find the Windows command (the README's first screen has three install buttons) | Step, Choice (which system) |
| 3 | Open PowerShell from the Start menu | Step. ⚠ Stall: some players have never opened it, and some wonder whether they need "Run as administrator" (they don't; the README says so only further down) |
| 4 | Paste `irm … \| iex` | Step. ⚠ Worry: running a script straight from the internet, with nothing beside it that says what it does or how to undo it. Some security tools warn about this pattern |
| 5 | The installer closes Steam, writes the binds and the wheel, and opens Steam again | Wait. ⚠ Worry: Steam closing on its own looks like a crash unless you read step 1 of the Quick start first |
| 6 | Launch **PokeMMO from the Steam library**, not from the usual shortcut | Step, Choice (Steam shortcut or the usual one; only the Steam one has the wheel). ⚠ Stall: many players keep launching the way they always have, and then the wheel does nothing |
| 7 | First battle | Nothing confirms the pad worked before this point |

Count: 6 steps, 2 choices, 4 stall or worry points.
Tested: CI (Windows x64 and ARM, PowerShell 5.1 and 7) runs sandbox round trips.
In game: Xbox Wireless Controller on Windows 11, 2026-11. A fresh-PC run of
this journey is still to do.

## macOS

| # | What happens | Kind |
|---|---|---|
| 1-2 | Same as Windows, pick macOS | Step, Choice |
| 3 | Open Terminal | Step. ⚠ Stall: for many Mac players this is their first time in Terminal |
| 4 | Paste `curl … \| sh` | Step. ⚠ Worry: same as Windows. If the Mac has no developer tools, a private Python is downloaded for that one run (the installer says so) |
| 5 | Steam closes and opens again | Wait. ⚠ Worry: same as Windows |
| 6 | Launch PokeMMO from the Steam library | Step, Choice. ⚠ Stall: same as Windows |
| 7 | First battle | Not played on a Mac yet |

Count: 6 steps, 2 choices, 4 stall or worry points.
Tested: CI (Apple silicon and Intel) runs sandbox round trips. Not played on
real hardware: help wanted.

## Linux

Same as macOS, with one more thing to know: the installer finds the zip,
Flatpak and Snap installs of PokeMMO. Count: 6 steps, 2 choices, 3 stall or
worry points (most Linux players already know the terminal).
Tested: a Linux sandbox install and uninstall on 2026-11-18 restored every byte.
CI (x64, ARM and an Arch Linux image standing in for SteamOS) runs sandbox
round trips. Not played on real hardware.

## Steam Deck

| # | What happens | Kind |
|---|---|---|
| 1 | Hold the power button → **Switch to Desktop** | Step. ⚠ Stall: players who have never left Game Mode don't know this exists |
| 2 | Open Konsole from the app menu | Step. ⚠ Stall: hard to find without knowing its name |
| 3 | Type or paste the long `curl … \| sh` address | Step. ⚠ Stall: the on-screen keyboard (Steam + X) and a 100-character command. The worst step in any journey |
| 4 | The installer closes Steam and opens it again | Wait. ⚠ Worry: in Desktop Mode this looks like the whole screen restarting |
| 5 | Return to Game Mode | Step |
| 6 | Launch PokeMMO from the library | Step |
| 7 | First battle | Not played on a Deck yet |

Count: 6 steps, 1 choice, 5 stall or worry points.
Tested: CI's Arch Linux image only. Real Deck hardware and Game Mode are
**not tested**.

## Changing a button, updating, uninstalling

- **Change a button:** run the install command again with `-Ui` / `--ui` added.
  On Windows that is a 120-character line. ⚠ Stall: there's no short way to
  reopen the app unless you used `--install-ui` at install time.
- **Update:** run the same install command again (good: one thing to remember).
- **Uninstall:** another long line. ⚠ Worry: players want to know they can undo
  it *before* they install. Today the undo command sits far below the install
  command.

## What the fixes aim for

| | Today | Goal |
|---|---|---|
| Steps to the first battle | 6 | 4 |
| Choices | 1-2 | 1 (which system) |
| What it does / how to undo it | Collapsed, ~200 lines below the command | Next to the command |
| Pad confirmed working | In game only | At the end of the install ("press A") |
| Reopen the remap app | A 120-character command | A short command the installer prints, or a menu entry |
| Version a new player gets | The beta (`main`) | The latest release, checksum shown |

See [feedback.md](feedback.md) for the ranked list these come from.
