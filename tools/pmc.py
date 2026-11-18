"""pmc: the PokeMMO controller layout from a terminal (PowerShell, bash, zsh, cmd).

    python tools/pmc.py status            what is installed, and does it still match
    python tools/pmc.py doctor            every check, and the command that fixes each problem
    python tools/pmc.py install           install, or update an earlier install
    python tools/pmc.py uninstall         put everything back as it was
    python tools/pmc.py app               open the remap screen
    python tools/pmc.py version

Everything the remap screen does, this does, with the same code: this file only reads
options, asks, and hands the work to setup.py (the installer) and status.py. It writes
nothing itself. Standard library only; no admin rights.

Global flags: --json, --yes, --dry-run, --pokemmo PATH, --steam PATH, --quiet, --no-color.
--dry-run shows every file it would change and changes nothing. --yes skips the question
(implied when there is no terminal). --json prints one pmc.cli/1 envelope on stdout:
{"schema", "command", "ok", "data", "warnings", "error": {"code", "message"}}; the lines a person
would have read go in data.log. The shapes and codes are locked in spec/schema/cli.schema.json.

Exit codes:
  0  done, or nothing to do        5  not found (PokeMMO or Steam)
  1  failed                        6  data made by a newer version
  2  bad usage                     7  update verification failed, nothing changed
  3  blocked, needs you to act     10 update failed and was rolled back
  4  refused by product policy
"""
import argparse, contextlib, io, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup as setup_mod  # noqa: E402
import status  # noqa: E402
from common import VERSION  # noqa: E402

SCHEMA = "pmc.cli/1"
OK, FAILED, USAGE, BLOCKED, REFUSED, NOT_FOUND, NEWER = 0, 1, 2, 3, 4, 5, 6
ERROR_CODES = {"POKEMMO_NOT_FOUND": 5, "STEAM_NOT_FOUND": 5, "POKEMMO_RUNNING": 3, "STEAM_GAME_RUNNING": 3,
               "GAME_MODE_DEFERRED": 3, "POLICY_MACRO": 4, "POLICY_SHARED_INPUT": 4, "DATA_NEWER": 6,
               "UPDATE_VERIFY_FAILED": 7, "UPDATE_ROLLED_BACK": 10, "USAGE": 2, "FAILED": 1}

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


def _where(p):
    """Options every command takes: where PokeMMO and Steam are, and the output form."""
    p.add_argument("--pokemmo", help="PokeMMO data folder (holds config/main.properties)")
    p.add_argument("--steam", help="Steam folder")
    p.add_argument("--no-wheel", action="store_true", help="leave the Steam right-stick wheel out")
    p.add_argument("--json", action="store_true", help="print one pmc.cli/1 JSON envelope instead of text")
    p.add_argument("--quiet", "-q", action="store_true", help="print only problems")
    p.add_argument("--no-color", action="store_true", help="plain text (there is no colour today; accepted for scripts)")


def _changing(p):
    p.add_argument("--yes", "-y", action="store_true", help="do not ask first (implied without a terminal)")
    p.add_argument("--dry-run", action="store_true", help="show every file it would change; change nothing")
    p.add_argument("--no-follow", action="store_true", help="do not start the wheel follower at login")
    p.add_argument("--follow-at-login", action="store_true", help="start the wheel follower at login again")
    p.add_argument("--resolution", metavar="WxH", help="the size of the game picture, like 1920x1080")
    p.add_argument("--name", action="append", default=[], help="extra controller name to bind; repeatable")
    p.add_argument("--switch-positional", action="store_true", default=None,
                   help="Nintendo pads: confirm on the bottom button like Xbox")


def parser():
    ap = argparse.ArgumentParser(prog="pmc", description=__doc__.split("\n\n")[0],
                                 epilog="Exit codes: 0 ok, 1 failed, 2 usage, 3 blocked, 4 refused by policy, "
                                        "5 not found, 6 data from a newer version, 7 update check failed, 10 rolled back.")
    ap.add_argument("--version", action="version", version=f"pokemmo-controller {VERSION}")
    sub = ap.add_subparsers(dest="command", metavar="command", required=True)
    for name, text in (("status", "what is installed and whether it still matches"),
                       ("doctor", "every check, and the command that fixes each problem"),
                       ("version", "print the version")):
        _where(sub.add_parser(name, help=text, description=text))
    ins = sub.add_parser("install", help="install, or update an earlier install", description="Install or update.")
    _where(ins)
    _changing(ins)
    ins.add_argument("--layout", metavar="FILE", help="install your own layout (a file made by the remap screen)")
    ins.add_argument("--reset-layout", action="store_true", help="go back to the default layout")
    ins.add_argument("--install-ui", action="store_true", help="also keep the remap screen on this computer")
    un = sub.add_parser("uninstall", help="put everything back as it was", description="Undo everything.")
    _where(un)
    _changing(un)
    app = sub.add_parser("app", help="open the remap screen in your browser", description="Open the remap screen.")
    _where(app)
    app.add_argument("--no-browser", action="store_true", help="print the address instead of opening it")
    app.add_argument("--tab", action="store_true", help="open a browser tab instead of an app window")
    return ap


# ---------------------------------------------------------------- output
def _name(a):
    return " ".join(x for x in (a.command, getattr(a, "sub", None)) if x)


def _done(a, text, data=None, warnings=()):
    """Success: the text for people, or the envelope with --json."""
    if a.json:
        print(json.dumps({"schema": SCHEMA, "command": _name(a), "ok": True, "data": data,
                          "warnings": list(warnings)}, sort_keys=True))
    elif text and not a.quiet:
        print(text)
    return OK


def _fail(a, error, message, text=None, data=None):
    """A refusal or failure: error is a key of ERROR_CODES, the exit code comes from it."""
    code = ERROR_CODES[error]
    if a.json:
        print(json.dumps({"schema": SCHEMA, "command": _name(a), "ok": False, "data": data, "warnings": [],
                          "error": {"code": error, "message": message}}, sort_keys=True))
    else:
        print(text if text is not None else message, file=sys.stderr if code != OK else sys.stdout)
    return code


def _say(a, line):
    """A line for people: stderr in --json mode, so stdout stays one envelope."""
    if not a.quiet:
        print(line, file=sys.stderr if a.json else sys.stdout)


# ---------------------------------------------------------------- status and doctor
def _health(a):
    found, reason = status.find(a.pokemmo)
    s, checks = status.doctor(found, a.steam, a.no_wheel, reason)
    problems = [c for c in checks if not c["ok"]]
    s.update(problems=[{"id": c["id"], "detail": c["detail"], "fix": c["fix"]} for c in problems])
    return s, checks, problems, found


def cmd_status(a):
    s, checks, problems, found = _health(a)
    if not found:
        return _fail(a, "POKEMMO_NOT_FOUND", problems[0]["detail"],
                     f"PokeMMO was not found.\n  {problems[0]['detail']}\n  Fix: {problems[0]['fix']}")
    lines = [f"PokeMMO controller layout v{VERSION}", f"  PokeMMO folder  {found}",
             f"  Installed       " + ("no: not installed" if not s["installed"] else f"yes (v{s['installed_version']})")]
    if s["installed"]:
        lines += [f"  Binds           {'current' if s['binds_current'] else 'out of date'}",
                  f"  Steam wheel     " + ("current" if s["steam_current"] else "out of date" if s["steam"] else "not installed"),
                  f"  Layout          {'your own' if s['custom'] else 'default'}"]
    lines.append("PokeMMO is open: close it before you change anything." if s["pokemmo_open"] else "")
    for c in problems:
        lines.append(f"Problem: {c['detail']}\n  Fix: {c['fix']}")
    lines.append("Everything is in place." if not problems else "Run `pmc doctor` for every check.")
    return _done(a, "\n".join(l for l in lines if l), s)


def cmd_doctor(a):
    s, checks, problems, found = _health(a)
    s["checks"] = checks
    if not found:
        return _fail(a, "POKEMMO_NOT_FOUND", problems[0]["detail"], data=s)
    lines = [f"PokeMMO controller layout v{VERSION}"]
    for c in checks:
        lines.append(f"  [{'ok' if c['ok'] else '!!'}] {c['detail']}" + (f"\n       Fix: {c['fix']}" if c["fix"] else ""))
    if problems:
        print("\n".join(lines), file=sys.stderr if a.json else sys.stdout)
        return _fail(a, "FAILED", f"{len(problems)} problem(s) found.", f"{len(problems)} problem(s) found.", data=s)
    lines.append("All checks passed.")
    return _done(a, "\n".join(lines), s)


def cmd_version(a):
    return _done(a, f"pokemmo-controller {VERSION}", {"version": VERSION})


# ---------------------------------------------------------------- install and uninstall
def _setup_argv(a):
    argv = []
    for flag, val in (("--pokemmo", a.pokemmo), ("--steam", a.steam), ("--resolution", a.resolution),
                      ("--layout", getattr(a, "layout", None))):
        if val:
            argv += [flag, val]
    for n in a.name:
        argv += ["--name", n]
    for flag, on in (("--no-wheel", a.no_wheel), ("--no-follow", a.no_follow),
                     ("--follow-at-login", a.follow_at_login), ("--switch-positional", a.switch_positional),
                     ("--reset-layout", getattr(a, "reset_layout", False)),
                     ("--install-ui", getattr(a, "install_ui", False)), ("--uninstall", a.command == "uninstall")):
        if on:
            argv.append(flag)
    return argv


def _error_for(message):
    """The stable error key for an installer refusal, from its message."""
    m = message.lower()
    if "pokemmo is open" in m:
        return "POKEMMO_RUNNING"
    if "a steam game is running" in m:
        return "STEAM_GAME_RUNNING"
    if "main.properties" in m and ("could not find" in m or "no config" in m):
        return "POKEMMO_NOT_FOUND"
    if "steam" in m and "not found" in m:
        return "STEAM_NOT_FOUND"
    if "newer" in m and "made by" in m:
        return "DATA_NEWER"
    if "was not used" in m or ("nothing was changed" in m and "layout" in m):
        return "POLICY_SHARED_INPUT" if "share" in m else "POLICY_MACRO"
    return "FAILED"


def _run_setup(argv):
    """Run setup.py's code in-process. Returns (exit code, text it printed, error text)."""
    out, err = io.StringIO(), io.StringIO()
    code = OK
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            setup_mod.main(argv)
        except SystemExit as e:
            if e.code in (None, 0):
                code = OK
            elif isinstance(e.code, int):
                code = e.code
            else:
                print(e.code, file=sys.stderr)
                code = ERROR_CODES[_error_for(str(e.code))]
    return code, out.getvalue(), err.getvalue()


def _preview(a, argv):
    """The change set (what setup.py would do), or (None, error key, message) when it cannot."""
    try:
        sa = setup_mod.parse(argv)
    except SystemExit as e:
        msg = str(e.code) if not isinstance(e.code, int) else ""
        return None, (_error_for(msg) if msg else "USAGE"), msg
    sa.dry_run = True
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return setup_mod.changes(sa), "", ""
    except SystemExit as e:
        msg = str(e.code)
        return None, _error_for(msg), msg


def cmd_change(a, interactive, ask):
    argv = _setup_argv(a)
    if a.dry_run or (interactive and not a.yes and not a.json):
        plan, error, msg = _preview(a, argv)
        if plan is None:
            return _fail(a, error, msg)
        for c in plan["changes"]:
            _say(a, f"  would {c['action']}: {c['path']}")
        if plan["steam_restart"]:
            _say(a, "  Steam would be closed and started again.")
        if not plan["changes"]:
            _say(a, "Nothing would change.")
        if a.dry_run:
            return _done(a, "Dry run: nothing was written.", {"dry_run": True, "changes": plan["changes"],
                         "steam_restart": plan["steam_restart"], "pokemmo": plan["pokemmo"], "steam": plan["steam"]})
        if plan["changes"] and ask("Make these changes? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Nothing was changed.")
            return OK
    code, out, err = _run_setup(argv)
    log = [l for l in (out + err).splitlines() if l.strip()]
    if code == OK:
        if a.json:
            return _done(a, "", {"log": log})
        sys.stdout.write(out)
        sys.stderr.write(err)
        return OK
    if a.json:
        error = _error_for(err) if code == FAILED else next((k for k, v in ERROR_CODES.items() if v == code), "FAILED")
        return _fail(a, error, (err.strip().splitlines() or ["Failed."])[0], data={"log": log})
    sys.stdout.write(out)
    sys.stderr.write(err)
    return code


def cmd_app(a):
    import ui
    ui.serve(a.pokemmo, a.steam, a.no_wheel, not a.no_browser, tab=a.tab)
    return OK


def main(argv=None, interactive=None, ask=input):
    """Run one command. interactive and ask are for tests: whether a person is at the keyboard
    (default: stdin is a terminal) and how to ask them."""
    try:
        a = parser().parse_args(argv)
    except SystemExit as e:
        return USAGE if e.code not in (0, None) else OK
    if interactive is None:
        interactive = bool(getattr(sys.stdin, "isatty", lambda: False)())
    try:
        if a.command in ("install", "uninstall"):
            return cmd_change(a, interactive, ask)
        return {"status": cmd_status, "doctor": cmd_doctor, "version": cmd_version, "app": cmd_app}[a.command](a)
    except KeyboardInterrupt:
        print("\nStopped. Every file is either fully updated or untouched; run the command again to finish.",
              file=sys.stderr)
        return FAILED


if __name__ == "__main__":
    sys.exit(main())
