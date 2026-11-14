# PokeMMO Xbox Controller Layout

![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d4)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776ab)
![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f)
![Macro policy: 1 input = 1 action](https://img.shields.io/badge/macro%20policy-1%20input%20%3D%201%20action-6b6b70)

Play [PokeMMO](https://pokemmo.com) on PC with an Xbox controller, using the
game's **own controller support**. All 9 hotbar slots, Bag, Party, Pokédex,
GTL, Friends, Team and the rest are on the controller, plus a labeled
right-stick wheel so you can see what each direction does.

![Button map](docs/button-map.svg)

## Contents

- [Quick start](#quick-start)
- [Controls](#controls)
- [How do I… with a controller](#how-do-i-with-a-controller)
- [Is this allowed?](#is-this-allowed)
- [Troubleshooting](#troubleshooting)
- [How it works](#how-it-works)
- [Compared with other setups](#compared-with-other-setups)
- [Roadmap](#roadmap)

## Quick start

You need Windows, PokeMMO, Python 3.9+ and (for the wheel) Steam.

1. Close PokeMMO **and** Steam. Both rewrite their config files when they exit.
2. Run:
   ```powershell
   git clone https://github.com/jordanallenlewis/pokemmo-controller
   cd pokemmo-controller
   py tools/apply_native.py      # PokeMMO's own controller binds
   py tools/install_wheel.py     # optional: right-stick wheel via Steam Input
   ```
3. Start Steam, then launch **PokeMMO from your Steam library** (the installer
   adds it as a non-Steam game). Skipped the wheel? Start PokeMMO as usual.

Installed somewhere else? Add `--pokemmo "D:\Games\PokeMMO"` and
`--steam "D:\Steam"`. To undo everything: `py tools/uninstall.py`.

## Controls

| Button | Action |
|---|---|
| Left stick | Move |
| A | Confirm / talk |
| B | Cancel / back |
| X / Y | The game's Key X / Key Y |
| **View** (⧉) | **Focus Ring:** select anything on screen |
| Menu (≡) | Game Menu (Party, Settings…) |
| RB | Bag |
| LB | Hotbar 5 |
| D-pad ↑ → ↓ ← | Hotbar 1 / 2 / 3 / 4 |
| RT / LT | Next / previous hotbar page |
| Right stick | **Wheel** (see below) |
| L3 (press left stick) | Team |
| R3 (press right stick) | Screenshot |

### The Focus Ring

Tap **View** and a highlight jumps onto the hotbar, your party or an open
window. Move it with the stick, press **A** to use what's highlighted, and press
**B** or **View** to leave. Every hotbar slot on every page can be reached this way,
not only the ones with their own button.

### The wheel

Tilt the right stick to open the wheel in the middle of the screen. Point at a
slice (its name shows above the wheel) and let go to use it. Let go in the
center to cancel.

| In game | Slices, clockwise from the top |
|---|---|
| <img src="docs/wheel-in-game.png" alt="The wheel in game, pointing at Egg Incubators" width="300"> | <img src="docs/wheel.svg" alt="Wheel slice map" width="300"> |

Each slice shows the key it presses (N = Pokédex, I = Egg Incubators,
C = Trainer Card, V = Friends, P = Global Trade Link, 6-9 = Hotbar 6-9,
F12 = Hide GUI) and sends exactly one key press when you let go.

## How do I… with a controller

| I want to… | Do this |
|---|---|
| Use any hotbar item (bike, rod, Sweet Scent…) | D-pad / LB for slots 1-5, wheel for 6-9, or **View** → pick → **A** |
| Switch hotbar page | RT / LT |
| Open my party / reorder it | Menu → Party, pick a Pokémon with the stick, **A** for its options |
| Open the bag / give an item | RB, pick the item, **A** → Give |
| Open the GTL | Wheel → Global Trade Link |
| Check the Pokédex / trainer card | Wheel → Pokédex / Trainer Card |
| Hatch eggs | Wheel → Egg Incubators |
| Type in chat or GTL search | Steam on-screen keyboard: **Steam button + X** (when launched from Steam), or a keyboard |
| Join a PvP queue, drag Pokémon in the PC | Still needs a mouse, see [Roadmap](#roadmap) |

## Is this allowed?

PokeMMO allows remapping as long as **one input from you produces no more than
one input to the game**, with no turbo, no sequences and no cursor jumps
([macro policy](https://support.pokemmo.com/knowledgebase/article/macroing-faq),
[setting up a controller](https://support.pokemmo.com/knowledgebase/article/setting-up-a-controller)).

This layout:
- uses **PokeMMO's own controller binds** for every button: the same thing you
  get by binding by hand in Settings → Xbox Controller;
- passes buttons through Steam **unchanged**;
- gives each wheel slice **one key press** on release;
- has **no turbo, no macros, no chained inputs**.

PokeMMO's support page also says it "cannot guarantee every remap software will
be accepted". Steam Input is the setup PokeMMO's own
[Steam Deck guide](https://support.pokemmo.com/knowledgebase/article/steam-deck-setup)
uses. Don't want any Steam involvement? Skip `install_wheel.py`; you lose only the wheel.

## Troubleshooting

**Controller not detected / buttons do nothing**
- Settings → Control → *Enable Controller Support* must be ticked (`apply_native.py` does this).
- Close DS4Windows, DSX, reWASD, Xpadder and similar tools. Two remappers fighting is the most common cause.
- Bluetooth: unpair and pair again, or try a USB cable before launching.
- The game names each controller. With Steam Input on, PokeMMO sees
  `#SettingsController_SteamController`, and the binds are written for that name too.
  A pad with an unusual name gets the game's defaults: bind it by hand in
  Settings, or add its name to `CONTROLLER_NAMES` in `tools/apply_native.py`.

**No wheel**
- Launch PokeMMO **from the Steam library**, not the desktop shortcut.
- Steam → Settings → Controller → *Enable Steam Input for Xbox controllers* must be on.

**A button fires twice**
- Another remapper is running, or a Steam layout other than this one is active
  for PokeMMO (Steam → PokeMMO → Controller Layout).

**Settings went back to default**
- PokeMMO was open while you ran a script. Close it and run the script again.
  The scripts refuse to run while PokeMMO or Steam is open.

**Undo**
- `py tools/uninstall.py` reverts only what these scripts changed. Other PokeMMO
  settings you changed since then are kept.

## How it works

- `tools/apply_native.py` writes the binds into PokeMMO's
  `config/main.properties`, key `client.controls.controller_input_maps_gdx_2`:
  ```
  Xbox One S Controller;KEY_A,BUTTON,0;KEY_B,BUTTON,1;KEY_RING_FOCUS,BUTTON,4;KEY_UP,AXIS,1,false;…|Xbox 360 Controller;…
  ```
  One entry per controller name; buttons and axes are SDL GameController
  numbers (table in the script). Action names include `KEY_HOTBAR_1`-`9`,
  `KEY_RING_FOCUS`, `KEY_GAMEMENU`, `KEY_INVENTORY`, `KEY_MONSTERDEX`,
  `KEY_TRAINER`, `KEY_FRIENDS_LIST`, `KEY_TEAM`, `KEY_TRADE_LINK`,
  `KEY_INCUBATOR`, `KEY_SCREENSHOT`, `KEY_HIDE_GUI`, `KEY_NEXT`, `KEY_PREVIOUS`.
- `tools/install_wheel.py` builds the Steam Input layout
  (`steam/controller_xboxone.vdf`, `steam/controller_xbox360.vdf`), adds a
  "PokeMMO" non-Steam shortcut and sets the keyboard keys the wheel presses.
  Edit `WHEEL` in the script to change the slices (slot 0 is the center and stays empty; position, size and opacity are in `build_layout`).
- Every file touched is backed up once as `*.bak-pokemmo-controller`.

## Compared with other setups

| | This project | PokeMMO defaults | [pokemmo-port](https://github.com/lowlevel-1989/pokemmo-port) | [SteamInputDB layout](https://www.steaminputdb.com/config/3690044714) | Xpadder / JoyToKey guides |
|---|---|---|---|---|---|
| Platform | Windows PC | All | Linux handhelds | Steam | Windows |
| Uses the game's own binds | ✅ | ✅ | ❌ (keyboard emulation) | ❌ | ❌ |
| All 9 hotbar slots | ✅ | 4 | ✅ | ? | partly |
| Labeled wheel for menus | ✅ | ❌ | ❌ | ❌ | ❌ |
| Mouse cursor | ❌ (roadmap) | ❌ | ✅ | ✅ | ✅ |
| Installer + uninstaller | ✅ | n/a | ✅ | Steam UI | manual |
| Documented | ✅ | partly | ✅ | ❌ | old |

## Roadmap

- **Cursor mode** for mouse-only screens (PvP queue, PC box drag, some popups):
  a hold-to-aim right-stick mouse that still sends one click per press.
- PlayStation / Switch Pro button art and Steam Deck back-button variant.
- Publish the wheel as a Steam community layout.
- Linux / Steam Deck support for `apply_native.py`.

Ideas and controller reports welcome: [open an issue](https://github.com/jordanallenlewis/pokemmo-controller/issues).

## Tested with

- Xbox Wireless Controller (Bluetooth), Windows 11, 4K display, PokeMMO 2026-11 client.

Other XInput pads should work. Please report results in an issue.

---

Not affiliated with or endorsed by PokeMMO. No game files or ROMs are included.
Released under the [MIT License](LICENSE).
