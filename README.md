# PokeMMO controller layout (Xbox, PC)

An Xbox controller layout for PokeMMO built on **the game's own controller
support**, plus one optional extra: a labeled right-stick wheel from Steam Input.
Every button passes straight through to PokeMMO's own binds; only the right
stick goes through Steam. Each input sends one game action, so it stays inside
PokeMMO's macro policy.

The key to full reach is the **Focus Ring** (View button): it moves focus onto
the hotbar, the party and any open window, so you can select and use anything
on screen — every hotbar slot on every page — with the stick/D-pad and A.

## Layout

| Controller | Action |
|---|---|
| Left stick | Move |
| A / B | Confirm / cancel |
| X / Y | Game Key X / Key Y |
| View (⧉) | **Focus Ring** — select anything: hotbar slots, party, windows |
| Menu (≡) | Game Menu (Party, Pokédex, Settings…) |
| RB | Bag |
| LB | Hotbar 5 |
| D-pad ↑ → ↓ ← | Hotbar 1 / 2 / 3 / 4 |
| RT / LT | Next / previous hotbar page |
| Right stick (tilt) | **Wheel** with labels; release on a slice to use it: Pokédex, Egg Incubators, Trainer Card, Friends, Global Trade Link, Hotbar 6-9, Hide GUI |
| L3 | Team |
| R3 | Screenshot |

**Using any hotbar slot:** tap View until the hotbar is highlighted, move along
it with the stick, press A. RT/LT flip hotbar pages. B or View leaves the ring.

Without the wheel (pure native), the right stick does nothing; use the Focus
Ring or Game Menu for those windows.

## Why native only

- PokeMMO supports controllers itself (Settings → Control → Enable controller
  support, then Settings → Xbox Controller for binds).
- Players report Steam Input fighting the native support (B stops working).
  Remapping is allowed but "we cannot guarantee every remap software will be
  accepted" ([setting up a controller](https://support.pokemmo.com/knowledgebase/article/setting-up-a-controller),
  [macro policy](https://support.pokemmo.com/knowledgebase/article/macroing-faq)).
  Native avoids that risk entirely.
- Native limits: one button per action, no layers, no mouse cursor, no chat
  typing with the pad. The Focus Ring covers most of what a cursor would.

## Install

1. Close PokeMMO and Steam (PokeMMO rewrites its config on exit).
2. `python tools/apply_native.py` (option `--pokemmo <install dir>`).
   Backs up `config/main.properties` once, turns controller support on, writes
   the map for the Xbox controller names and for Steam's virtual pad
   (`#SettingsController_SteamController`, how PokeMMO names it under Steam Input).
3. For the wheel: `python tools/install_wheel.py`. Adds keyboard binds the wheel
   uses, a non-Steam shortcut "PokeMMO", and the layout for Xbox One/Series/360.
   Then always launch PokeMMO **from the Steam library**.
4. Without the wheel: start PokeMMO normally.

Or bind by hand in Settings → Xbox Controller using the table above.

### Config format (for other devices)

`client.controls.controller_input_maps_gdx_2` in `config/main.properties`:
`<controller name>;<ACTION>,BUTTON,<n>;<ACTION>,AXIS,<n>,<true=positive>|<next controller>…`
Button/axis numbers are SDL GameController indices, listed in
`tools/apply_native.py`. Action names: KEY_UP/DOWN/LEFT/RIGHT, KEY_A/B/X/Y,
KEY_NEXT, KEY_PREVIOUS, KEY_HOTBAR_1-9, KEY_RING_FOCUS, KEY_GAMEMENU,
KEY_INVENTORY, KEY_MONSTERDEX, KEY_TRAINER, KEY_FRIENDS_LIST, KEY_TEAM,
KEY_TRADE_LINK, KEY_INCUBATOR, KEY_SCREENSHOT, KEY_HIDE_GUI.

## Status

- Applied on Jordan's PC 2026-11-14 with the wheel; PokeMMO's settings show the
  map on Steam's virtual pad.
- Needs a hands-on check with the real pad (Focus Ring on hotbar, wheel).
- `steam/` holds the generated wheel layouts, plus the Legion Go S layout
  (`steam/legion-go-s/`) where the wheel idea came from.

## Prior art

No public, documented full-parity Xbox-on-PC layout found (survey 2026-11-14):
[lowlevel-1989/pokemmo-port](https://github.com/lowlevel-1989/pokemmo-port) (Linux handhelds),
[SteamInputDB layout](https://www.steaminputdb.com/config/3690044714) (undocumented),
[reWASD config](https://www.rewasd.com/community/config/pokemon-mmo-controller-support/7cf96f5b5b59959b1509d1fa802d7495) (2021).
