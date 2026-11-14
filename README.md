# PokeMMO controller layout (Xbox, PC)

A Steam Input layout that gives an Xbox controller everything a keyboard and
mouse can do in PokeMMO: movement, A/B, all 9 hotbar slots, hotbar pages, bag,
party (via Game Menu or cursor), Pokédex, trainer card, friends, team, egg
incubators, screenshot, hide GUI, chat, and a mouse cursor for screens that
only take clicks.

Every binding sends exactly one key or mouse button, so it follows PokeMMO's
macro policy ("1 input from a player must generate no more than 1 resulting
input"). No turbo, no macros, no buttons that jump the cursor.

## Layout

**Normal play**

| Controller | Does | Key sent |
|---|---|---|
| Left stick / D-pad | Move | W A S D |
| A | Confirm / talk | E |
| B | Cancel / back / run | B |
| X | Bag | Q |
| Y | Hotbar 1 | 1 |
| Start (≡) | Game Menu (Party, Pokédex, Settings…) | M |
| LB / RB | Hotbar page previous / next | Page Up / Page Down |
| Right stick | Mouse cursor | mouse |
| RT / LT | Left click / right click (right-click a party Pokémon for its menu) | mouse |
| R3 (press right stick) | Open chat / send | Enter |
| L3 (press left stick) | Steam on-screen keyboard (type in chat) | — |

**Hold View (⧉) for shortcuts**

| While holding View | Does | Key sent |
|---|---|---|
| D-pad ↑ → ↓ ← | Hotbar 2 / 3 / 4 / 5 | 2 3 4 5 |
| A / B / X / Y | Hotbar 6 / 7 / 8 / 9 | 6 7 8 9 |
| Right stick ↑ → ↓ ← | Pokédex / Egg incubators / Team / Trainer card | N I G C |
| Start | Global Trade Link window | P |
| LB | Screenshot | F11 |
| L3 | Friends list | V |
| R3 | Hide GUI | F12 |
| LT / RT | Game's Key X / Key Y | X Y |

Holding View sends nothing by itself; it only switches what the other buttons do.

## Why this design

- **PokeMMO's own controller support** (Settings → Xbox Controller) allows one
  binding per action and has no cursor, no layers and no chat typing. Out of the
  box: left stick moves, D-pad = hotbar 1-4, RB = bag, Start = game menu, View =
  focus ring, triggers = hotbar pages; LB, L3, R3 and hotbar 5-9 are unbound.
  The official support page says it doesn't cover every UI element. That rules
  out full parity on native support alone.
- **Steam Input** adds a hold layer and a stick-driven cursor. Players report
  Steam Input and native support fighting (B stops working), so this setup
  turns PokeMMO's native support **off** and has Steam send keyboard and mouse
  only.
- PokeMMO staff say remapping is allowed if it stays 1:1 ([setting up a
  controller](https://support.pokemmo.com/knowledgebase/article/setting-up-a-controller),
  [macro policy](https://support.pokemmo.com/knowledgebase/article/macroing-faq)).
  Steam Input is the most widely used remapper and is what the official Steam
  Deck guide uses.

## Install (Windows PC)

1. Close PokeMMO and Steam.
2. `python tools/install_windows.py` (options: `--pokemmo <dir> --steam <dir>`).
   It backs up every file it touches (`*.bak-pokemmo-controller`), then:
   - sets the game's keyboard binds listed above (adds Bag = Q and Game Menu = M,
     which ship unbound) and turns native controller support off;
   - adds a non-Steam shortcut named **PokeMMO**;
   - installs the layout for Xbox One/Series and Xbox 360 controllers.
3. Start Steam and launch PokeMMO **from the Steam library** (Steam Input only
   applies to games Steam launched).

To undo: restore the `.bak-pokemmo-controller` copies, or turn "Enable
Controller Support" back on in PokeMMO and disable Steam Input for the
shortcut.

## Other devices

- **Steam Deck / Legion Go S / other Steam handhelds:** add PokeMMO as a
  non-Steam game named `PokeMMO`, copy the game keybinds above, and import the
  matching `.vdf`. `steam/legion-go-s/` holds the earlier Legion Go S layout
  (hybrid: uses PokeMMO's native support for A/B/Start/View, trackpad mouse).
- **Rebuild the layout:** edit `tools/build_layout.py`, run it, re-run the
  installer.

## Status

- Installed on Jordan's gaming PC 2026-11-14 (Xbox Wireless Controller, Bluetooth).
- Verified by test pad: Steam loads the layout for the PokeMMO shortcut with
  keyboard/mouse output only; X opened the Bag, B closed it.
- Needs a hands-on pass with the real controller: hold-View layer, right-stick
  cursor, Start → Game Menu (M), GTL (P), friends (V). Some of these keys did
  not open their windows when sent from the test rig; the cause is unconfirmed.

## Prior art

No public, documented, full-parity Xbox-on-PC layout was found (2026-11-14 survey):
- [lowlevel-1989/pokemmo-port](https://github.com/lowlevel-1989/pokemmo-port):
  PortMaster gptokeyb mapping for Linux handhelds, the best documented one.
- [SteamInputDB layout by senor_alikz](https://www.steaminputdb.com/config/3690044714):
  Xbox One, beta, undocumented.
- [reWASD config](https://www.rewasd.com/community/config/pokemon-mmo-controller-support/7cf96f5b5b59959b1509d1fa802d7495) (2021).
- Steam Deck community layouts (in-client only).
