# 0002: Cursor mode

Status: approved under the 2026-11-17 standing rule that UX decisions on this project ship once CI is green and the in-game rig check passes (ops-desk resolution 2026-11-26). Nothing ships until both hold. It amends `docs/FOUNDATION.md` 3.1 rule 4 in the same change.

## Problem
Some PokeMMO screens answer only to a mouse. Examples: route details in the Pokédex (#125), a window after focus moves (#126), refocusing a shop window (a request on r/pokemmo), PvP queue, PC box drag, some popups. The Focus Ring cannot reach them. Today the README says to click once with a mouse.

## Decision
Add a cursor driven by Steam Input, in two phases.

1. **Trackpads and touchpads (no locked layer changes).** On the Steam Deck the right trackpad becomes a mouse, and pressing it sends a left click. On the DualSense and DualShock 4 the touchpad becomes a mouse, and pressing it sends a left click. Every layout leaves these sources unbound today.
2. **Xbox and Switch Pro.** The wheel's empty top slice becomes "Cursor". Picking it switches to a cursor layer: right stick = mouse (relative), RT = left click, LT = right click, R3 or B = back to normal. Everything else stays the same in the layer. "Cursor" is a mode switch drawn in the wheel template. It is not a wheel id, so the 10 locked wheel ids and the share code stay as they are.

`docs/FOUNDATION.md` 3.1 rule 4 now reads "The right stick is reserved for the wheel and the cursor layer".

## Macro policy (why it is allowed)
- Movement comes only from the player's hand and is relative: no jumps, no snapping to targets, no automatic movement.
- One press of a click input sends one click on press. Turbo, repeat, long press, double press and chords are all off.
- Switching the layer sends nothing to the game.
- Steam Input moves the pointer, as Steam's own trackpad templates do. Nothing touches the game process, and there is no virtual-gamepad driver of ours.

## Enforced by
- `tests/test_cursor_policy.py` runs over every generated layout. It fails on turbo, repeat, long or double press activators, chords, absolute or jump mouse modes, or more than one click binding per press, and checks that the wheel's top slice still sends no key.
- The existing macro tests stay as they are.
- Every pad stays "unverified" until a person plays with it. Steam's layer and mouse-mode syntax is checked on hardware before the README claims it.

## Migration and old data
Layouts are regenerated on install and update. Remaps in `pmc.profile` are unchanged: the cursor is not a profile field in phase 1.

## Not decided here
- A hold-to-aim variant: every button already has an action, so it would need a default to move.
- Gyro aim.

## Undo
Revert the change. The next install or update rewrites the previous layout.
