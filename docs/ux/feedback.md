# What gets in a player's way: ranked friction list

Last updated 2026-11-18. This list decides what gets fixed first. Each item names
its source. **Player** means a player said it. **Measured** means a number or a
test run on our side shows it. **Review** means it came from walking the first-run
journey ([journey.md](journey.md)), and no player has said it yet. When a player
report confirms or contradicts an item, it moves.

Rank = how many players it stops × how early in the journey it stops them.

## The list

1. **New installs get a beta, not the release.** Both one-line installers fetch
   the `main` branch. Today that installs `v1.3.0-beta.1`, while the Releases page
   calls `v1.2.0` the latest. A player who came from a launch post should get the
   stable build.
   Source: Measured. Sandbox install on 2026-11-18 printed `Installed v1.3.0-beta.1`.
   See the [releases](https://github.com/jordanallenlewis/pokemmo-controller/releases).
   Fix: installers fetch the latest release, check its SHA-256 and print it. The
   beta is opt-in.

2. **Interest does not turn into installs or reports.** The launch post on
   r/pokemmo had about 27,000 views. In the same 14 days the repo had 24 unique
   visitors, 8 of them from Reddit. After four days there are no issues from
   players. Nobody has said "it worked" or "this was awkward", so we can't tell
   whether people install it.
   Source: Measured. GitHub traffic, 2026-11-18 (views 117 total, 24 unique;
   referrers reddit.com and the Reddit app 8 unique, pokemmocontroller.com 2
   unique). Issues: [all issues](https://github.com/jordanallenlewis/pokemmo-controller/issues?q=is%3Aissue).
   Fix: an honest install count (release download numbers, no tracking), a
   two-field "this felt awkward" issue form, and a clear next step after the
   install.

3. **Pasting a command from the internet is a trust hurdle, and nothing next to
   it says what the command does.** The command is `irm … | iex` on Windows and
   `curl … | sh` elsewhere. The README answers "what does it do" and "how do I
   undo it" under a collapsed heading, about 200 lines further down. No checksum
   is shown.
   Source: Review of the [Quick start](../../README.md#quick-start).
   Fix: a short "what this does / how to undo it" box right next to each
   command, a link to read the script first, and the release checksum.

4. **The README is long, and the extra commands are hard to type.** It has 646
   lines and 15 sections. Opening the remap screen on Windows takes
   `& ([scriptblock]::Create((irm …))) -Ui`, and uninstall takes the same
   construction. On a Steam Deck in Desktop Mode, typing either one on the
   on-screen keyboard is a real stall.
   Source: Review of the [README](../../README.md) and the
   [journey](journey.md#steam-deck).
   Fix: a 30-second quick start at the top and details below it. Short commands
   printed by the installer. A short install address on the project's own domain.

5. **Nothing confirms the pad works.** The install ends with "Start PokeMMO and
   play." It doesn't name the pad it found and offers no "press A" check. A
   player whose pad shows up under another name finds out only in game. One
   r/pokemmo player with an 8BitDo pad got only A and the bumpers to work.
   Source: Measured (the installer's last line in a sandbox run, 2026-11-18).
   Player: [Help mapping 8bitdo](https://www.reddit.com/r/pokemmo/comments/1jt6zql/help_mapping_8bitdo/)
   (search summary; the thread itself was not readable from here).
   Fix: name the pads found, then open a "test your pad" page in the app (press a
   button, see it light up), with what to do if nothing lights.

6. **The pad maker's app, or the pad's turbo button, can quietly break the
   layout.** In the 8BitDo thread, players told the poster to bind in the game
   and not in 8BitDo's software.
   Source: Player: [Help mapping 8bitdo](https://www.reddit.com/r/pokemmo/comments/1jt6zql/help_mapping_8bitdo/).
   Tracked in [#82](https://github.com/jordanallenlewis/pokemmo-controller/issues/82).

7. **Most pads and systems are not confirmed on real hardware.** The only real
   play test so far: an Xbox pad on Windows 11. PlayStation, Switch Pro, macOS
   and Steam Deck are built from SDL3's pad names and pass CI, but nobody has
   played on them. A player on one of them can't tell whether it will work.
   Source: Review of [Tested with](../../README.md#tested-with).
   Fix: a call-for-testers issue per pad and system. Every report added to
   "Tested with" with its date.

8. **Some screens still need a mouse.** Joining the PvP queue and dragging
   Pokémon in the PC are mouse-only today.
   Source: Review of the [README](../../README.md#how-do-i-with-a-controller)
   (the "How do I…" table and the Roadmap). No player has reported it yet.
   Fix: a cursor mode that keeps 1 press = 1 click (design first).

9. **On a Steam Deck the first step is the hardest.** You have to switch to
   Desktop Mode, find a terminal, and type or paste a long address with no
   keyboard. A 2022 thread also found that the game's install type (Flatpak or
   zip) matters on the Deck.
   Source: Review ([journey](journey.md#steam-deck)). Player (2022, before the
   game had controller support):
   [Anyone gotten this running on Steam Deck?](https://www.reddit.com/r/pokemmo/comments/ticcx8/anyone_gotten_this_running_on_steam_deck/).
   Fix: the short install address (item 4), Deck steps with pictures, and a
   check that names which PokeMMO install was found.

10. **PlayStation and Switch players may think it's Xbox only.** The repo's
    one-line description says "Xbox controller layout". Search on GitHub does
    not find the repo for "pokemmo steam deck".
    Source: Measured. Tracked in [#81](https://github.com/jordanallenlewis/pokemmo-controller/issues/81).

11. **The wheel needs Steam, which surprises players who don't use it.** Every
    button works without Steam. Only the right-stick wheel needs it. The README
    says so in step 3 of the Quick start.
    Source: Review of the [Quick start](../../README.md#quick-start).
    Fix: name both setups up front ("with Steam" and "without Steam") and say
    what each one gets.

## What players liked

- "i'd just been playing in android mode on PC ... looks fantastic" (r/pokemmo
  launch post, November 2026, as the author quoted it)
- "I hope u get a lot of supports to keep the project maintained" (same thread)

## Not read yet

The launch thread's other comments, PokeMMO forum threads and Discord can't be
read from where this list was made (Reddit and the forum answer 403). Paste or
link a comment in an issue and it gets ranked here.
