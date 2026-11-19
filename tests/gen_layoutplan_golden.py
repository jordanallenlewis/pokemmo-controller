"""Writes tests/golden/layoutplan-parity.json: which files the Python tool (tools/install_wheel.py
layout_plan) plans for one Steam account (the wheel layout per pad type and the configset entry that
picks it), with each file's bytes and whether a backup of the original may be kept; and which
Steam account folders userdirs() picks. The Go helper must plan the same (helper/layoutplan_test.go).
Run with --write after a deliberate change to install_wheel.py; test_layoutplan_golden fails when the
file is stale."""
import base64, json, sys, tempfile
from pathlib import Path

import helpers  # noqa: F401
import install_wheel as W

OUT = Path(__file__).resolve().parent / "golden" / "layoutplan-parity.json"
STEAM = Path("STEAM")
ACCOUNT = "12345"
CFG = "steamapps/common/Steam Controller Configs/" + ACCOUNT + "/config/"
LAYOUTS = {t: f"layout for {t}\n" for t in W.CONTROLLER_TYPES}   # layout_plan writes whatever text it gets

OTHER_SET = '"controller_config"\n{\n\t"220"\n\t{\n\t\t"workshop"\t\t"964711347"\n\t}\n}\n'
OURS_SET = '"controller_config"\n{\n' + W.OUR_BLOCK + '}\n'
OLD_OURS_SET = '"controller_config"\n{\n\t"pokemmo"\n\t{\n\t\t"autosave"\t\t"0"\n\t}\n}\n'


def cs(t):
    return CFG + f"configset_{t}.vdf"


def lay(t):
    return CFG + f"{W.CONFIG_DIR_NAME}/{t}.vdf"


SCENARIOS = [
    {"label": "fresh account, nothing there", "files": {}},
    {"label": "configsets with other games, LF and CRLF", "files": {
        cs("controller_xboxone"): OTHER_SET.encode(),
        cs("controller_ps4"): OTHER_SET.replace("\n", "\r\n").encode()}},
    {"label": "our block already there, or an older one", "files": {
        cs("controller_xboxone"): OURS_SET.encode(),
        cs("controller_ps5"): OLD_OURS_SET.encode(),
        cs("controller_neptune"): OURS_SET.replace("\n", "\r\n").encode()}},
    {"label": "configsets Steam could not have written", "files": {
        cs("controller_xboxone"): b"",
        cs("controller_xbox360"): b'"controller_config"\n{\n',
        cs("controller_ps5"): b"garbage"}},
    {"label": "a layout of the player's own, and one of ours", "files": {
        lay("controller_xboxone"): b'"controller_mappings"\n{\n\t"title"\t\t"My own layout"\n}\n',
        lay("controller_ps4"): ('"controller_mappings"\n{\n\t"title"\t\t"' + W.LAYOUT_TITLE + '"\n}\n').encode(),
        lay("controller_switch_pro"): b"layout for controller_switch_pro\n"}},
    {"label": "a configset that is not UTF-8", "files": {
        cs("controller_legion_go_s"): b'"controller_config"\n{\n\t"caf\xe9"\n\t{\n\t}\n}\n'}},
]

USERDATA = ["0", "12345", "67890", "abc", "00", "123x", "9"]
USERDATA_FILES = ["42"]


class FakePlan:
    def __init__(self, files):
        self.files, self.puts, self.notes = dict(files), [], []

    def current(self, p):
        return self.files.get(rel(p))

    def put(self, p, data, backup_ok=True):
        r = rel(p)
        prev = next((x for x in self.puts if x["path"] == r), None)
        if prev is None:
            prev = {"path": r}
            self.puts.append(prev)
        prev["backup_ok"] = backup_ok and prev.get("backup_ok", True)
        prev["data"] = base64.b64encode(data).decode("ascii")
        self.files[r] = data


def rel(p):
    return str(p).replace(str(STEAM), "$S", 1).replace("\\", "/")


def run(sc):
    p = FakePlan({"$S/" + k: v for k, v in sc["files"].items()})
    W.layout_plan(p, STEAM, ACCOUNT, LAYOUTS)
    return {"label": sc["label"],
            "files": {k: base64.b64encode(v).decode("ascii") for k, v in sc["files"].items()},
            "puts": p.puts, "notes": [rel(n) for n in p.notes]}


def userdirs():
    with tempfile.TemporaryDirectory() as td:
        steam = Path(td)
        ud = steam / "userdata"
        for d in USERDATA:
            (ud / d).mkdir(parents=True)
        for f in USERDATA_FILES:
            (ud / f).write_text("")
        picked = [u.name for u in W.userdirs(steam)]
        none = [u.name for u in W.userdirs(steam / "nothing")]
    return {"dirs": USERDATA, "files": USERDATA_FILES, "picked": picked, "no_userdata": none}


def build():
    return {"types": list(W.CONTROLLER_TYPES), "layouts": LAYOUTS, "account": ACCOUNT,
            "plans": [run(sc) for sc in SCENARIOS], "userdirs": userdirs()}


def dump():
    return json.dumps(build(), indent=1, ensure_ascii=True) + "\n"


if __name__ == "__main__":
    if "--write" in sys.argv:
        OUT.write_bytes(dump().encode("utf-8"))
        print("wrote", OUT)
    else:
        sys.stdout.write(dump())
