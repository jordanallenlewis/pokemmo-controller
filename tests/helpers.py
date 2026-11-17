"""Sandbox builders shared by the tests: a fake PokeMMO folder and a fake Steam."""
import os, struct, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
# Before any tool module is imported: never look at the real PokeMMO, Steam or registry.
os.environ["POKEMMO_CONTROLLER_TEST"] = "1"

USER_PAD = "Logitech Dual Action;KEY_A,BUTTON,1;KEY_B,BUTTON,2"  # a map the player made by hand

MAIN_PROPERTIES = "\n".join([
    "#Sat Nov 14 05:44:28 PST 2026",
    "client.android.foreground_service.enable=true",
    "client.controls.controller_input_maps=",
    "client.controls.controller_input_maps_gdx_2=Xbox One S Controller;KEY_Y,BUTTON,3;KEY_A,BUTTON,0|" + USER_PAD,
    "client.controls.gdx.bag=0",
    "client.controls.gdx.codex=0",
    "client.controls.gdx.gamemenu=0",
    "client.controls.gdx.hotbar6=13",
    "client.graphics.language=en",
    "client.ui.theme=dark",
]) + "\n"

CONFIGSET = '"controller_config"\n{\n\t"220"\n\t{\n\t\t"workshop"\t\t"964711347"\n\t}\n}\n'


def bvdf(d):
    out = b""
    for k, v in d.items():
        kb = k.encode() + b"\0"
        if isinstance(v, dict):
            out += b"\0" + kb + bvdf(v)
        elif isinstance(v, int):
            out += b"\2" + kb + struct.pack("<i", v)
        else:
            out += b"\1" + kb + str(v).encode() + b"\0"
    return out + b"\x08"


def shortcuts(entries):
    return b"\0shortcuts\0" + bvdf(entries) + b"\x08"


GAME = {"appid": -123456, "AppName": "Some Emulator", "Exe": '"C:\\emu\\emu.exe"', "StartDir": '"C:\\emu\\"',
        "LastPlayTime": 1700000000, "tags": {"0": "favorite"}}


class Sandbox:
    """A temp folder with PokeMMO data, a Steam folder and a fake home."""

    def __init__(self, name="sandbox", crlf=True, props=MAIN_PROPERTIES, steam=True):
        self._td = tempfile.TemporaryDirectory(prefix="pmc-")
        self.root = Path(self._td.name) / name
        self.home = self.root / "home"
        self.pokemmo = self.root / "Poke MMO"
        self.steam = self.root / "Steam"
        (self.pokemmo / "config").mkdir(parents=True)
        (self.pokemmo / "log").mkdir()
        self.home.mkdir()
        nl = b"\r\n" if crlf else b"\n"
        if props is not None:
            self.props.write_bytes(props.encode("utf-8").replace(b"\n", nl) if isinstance(props, str) else props)
        (self.pokemmo / "log" / "client.log").write_text(
            "[INFO] Controller 8BitDo Pro 2 ( ax 6 btn 15) id 3 attached\n", encoding="utf-8")
        if steam:
            (self.steam / "userdata" / "0").mkdir(parents=True)
            u = self.steam / "userdata" / "12345" / "config"
            u.mkdir(parents=True)
            (u / "shortcuts.vdf").write_bytes(shortcuts({"0": GAME, "2": dict(GAME, AppName="Other", appid=-654321)}))
            (self.steam / "userdata" / "67890").mkdir()  # second account: nothing yet
            cfg = self.steam / "steamapps" / "common" / "Steam Controller Configs" / "12345" / "config"
            cfg.mkdir(parents=True)
            (cfg / "configset_controller_xboxone.vdf").write_bytes(CONFIGSET.encode())
            (cfg / "configset_controller_ps4.vdf").write_bytes(CONFIGSET.encode().replace(b"\n", b"\r\n"))

    @property
    def props(self):
        return self.pokemmo / "config" / "main.properties"

    @property
    def cfg(self):
        return self.steam / "steamapps" / "common" / "Steam Controller Configs" / "12345" / "config"

    def env(self, **extra):
        e = dict(os.environ)
        for k in list(e):
            if k.startswith("POKEMMO_CONTROLLER_"):
                del e[k]
        e.update(POKEMMO_CONTROLLER_TEST="1", HOME=str(self.home), USERPROFILE=str(self.home),
                 LOCALAPPDATA=str(self.home / "AppData" / "Local"), APPDATA=str(self.home / "AppData" / "Roaming"),
                 XDG_DATA_HOME=str(self.home / ".local" / "share"),
                 XDG_CONFIG_HOME=str(self.home / ".config"), PYTHONIOENCODING="utf-8")
        e.update(extra)
        return e

    def setup(self, *args, steam=True, check=True, login=False, env=None):
        """login=True: leave the login helper at its default (on). Otherwise installs here pass
        --no-follow, so the older tests keep checking the same files; test_login_helper.py
        covers the default."""
        cmd = [sys.executable, str(TOOLS / "setup.py"), "--pokemmo", str(self.pokemmo)]
        if not login and "--follow" not in args and "--follow-at-login" not in args:
            cmd.append("--no-follow")
        if steam:
            cmd += ["--steam", str(self.steam)]
        r = subprocess.run(cmd + list(args), env=self.env(**(env or {})), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if check and r.returncode:
            raise AssertionError(f"setup failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return r

    def snapshot(self):
        """{relative path: bytes} of every file, plus empty folders."""
        out = {}
        for p in sorted(self.root.rglob("*")):
            rel = p.relative_to(self.root).as_posix()
            if p.is_file():
                out[rel] = p.read_bytes()
            elif not any(p.iterdir()):
                out[rel + "/"] = None
        return out

    def cleanup(self):
        for p in self.root.rglob("*"):
            try:
                os.chmod(p, 0o777)
            except OSError:
                pass
        self._td.cleanup()
