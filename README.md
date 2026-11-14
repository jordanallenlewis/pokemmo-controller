# PokeMMO controller layout (Xbox, PC)

An Xbox controller layout for PokeMMO built **only on the game's own controller
support**: no Steam Input, no virtual controller, no remapping software. Every
button sends one game action, so it stays inside PokeMMO's macro policy.

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
| Right stick ↑ / ↓ | Pokédex / Egg incubators |
| Right stick ← / → | Trainer card / Friends list |
| L3 | Team |
| R3 | Screenshot |

**Using any hotbar slot:** tap View until the hotbar is highlighted, move along
it with the stick, press A. RT/LT flip hotbar pages. B or View leaves the ring.

Unbound (open via Game Menu or the Focus Ring): Global Trade Link, Hide GUI,
hotbar 6-9 direct presses.

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

1. Close PokeMMO (it rewrites its config on exit).
2. `python tools/apply_native.py` (option `--pokemmo <install dir>`).
   Backs up `config/main.properties` once, turns controller support on, writes
   the map for Xbox One S / Series / 360 / Wireless controller names.
3. Start PokeMMO normally. Check Settings → Xbox Controller.

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

- Applied on Jordan's PC 2026-11-14; Settings → Xbox Controller shows every bind.
- Needs a hands-on check with the real pad (Focus Ring on hotbar, stick flicks).
- `steam/` holds the earlier Steam Input experiment (not used; kept for reference),
  including the Legion Go S layout.

## Prior art

No public, documented full-parity Xbox-on-PC layout found (survey 2026-11-14):
[lowlevel-1989/pokemmo-port](https://github.com/lowlevel-1989/pokemmo-port) (Linux handhelds),
[SteamInputDB layout](https://www.steaminputdb.com/config/3690044714) (undocumented),
[reWASD config](https://www.rewasd.com/community/config/pokemon-mmo-controller-support/7cf96f5b5b59959b1509d1fa802d7495) (2021).
