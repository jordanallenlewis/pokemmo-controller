# In-game test run (Linux)

Draft: written before the first run; nothing here has been run against a real client yet.

CI proves the installers and layout files on Windows, macOS and Linux. It cannot
play the game. This page is the maintainer's real in-game check on Linux, run for a
change before it merges. It does not replace CI and says nothing about Windows or macOS.

## What a run does

The steps and expected results are in [`tests/ingame/checklist.json`](../tests/ingame/checklist.json).
In order:

1. **Install** the layout from the branch with `install.sh`, as a normal user. Run it twice (second run must say "Already up to date").
2. **Start the client and log in** with the test account, and check by screenshot that the game world is drawn.
3. **Drive a virtual gamepad** through the checklist: every bound input does its one action; the Focus Ring reaches all 9 hotbar slots; Bag, Game Menu, Party and (if one starts by itself) battle navigation; the remap screen round trip (change a bind, apply, see it in game, restore, byte-for-byte check).
4. **Finish clean**: the client is still running and the picture still changes, log out, stop the client, uninstall.
5. **Report**: `python tests/ingame/report.py results.json` makes the pass/fail table; attach it and the screenshots to the PR. A missing result counts as a failure, and a failure blocks the merge.

## Rules of the run

- **One input, one action.** Each step presses one input once and checks one result. The run never holds, repeats, chains or times inputs, and never plays for the account: it walks, opens windows and closes them.
- **One test account, never a main account.** The login comes from the machine's own secret store. The password is never in this repo, a log, a screenshot or a command line; screenshots are taken after login and must not show the login form.
- **Short, quiet sessions** in a safe spot (a town or route). No trading, no market, no chat, no grinding, no seeking battles.
- If the game's staff contact the project, the run stops until the maintainer decides.

## What this run does not cover

- The Steam wheel: it needs Steam, so hotbar slots 6-9 and the other wheel keys are not driven here.
- Windows and macOS (CI matrix), PlayStation and Switch Pro pads, ARM, Steam Deck Game Mode: unverified until a person tests them.
- Whether Steam reloads a rewritten wheel layout with the game open.

## Running it

The run is started against a branch by the maintainer's test rig (container, virtual display, virtual gamepad). The rig is not part of this repo.
