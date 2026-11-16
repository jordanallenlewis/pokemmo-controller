"""A custom layout goes through the same writers and the same safety as the default:
one backup, exact uninstall, rerun is a no-op, and the rules refuse a macro."""
import json, unittest

from helpers import Sandbox
import layout as L
import apply_native, install_wheel
from test_setup import Base, diff


def custom():
    lay = L.default_layout()
    lay["binds"]["KEY_INVENTORY"] = {"button": 9}   # Bag on LB
    lay["binds"]["KEY_HOTBAR_5"] = {"button": 10}   # Hotbar 5 on RB
    lay["wheel"][0], lay["wheel"][1] = lay["wheel"][1], lay["wheel"][0]
    return lay


class CustomLayout(Base):
    def write(self, sb, lay, name="mine.json"):
        f = sb.root / name
        f.write_text(json.dumps(lay), encoding="utf-8")
        return str(f)

    def test_install_rerun_uninstall(self):
        sb = self.make()
        before = sb.snapshot()
        r = sb.setup("--layout", self.write(sb, custom()))
        self.assertIn("Installed", r.stdout)
        text = sb.props.read_text(encoding="utf-8")
        self.assertIn("Xbox Series X Controller;", text)
        entry = [e for e in text.split("|") if e.startswith("Xbox Series X Controller;")][0]
        self.assertIn("KEY_INVENTORY,BUTTON,9", entry)
        self.assertIn("KEY_HOTBAR_5,BUTTON,10", entry)
        vdf = (sb.cfg / "pokemmo" / "controller_xboxone.vdf").read_text()
        self.assertLess(vdf.index("key_press I, Egg Incubators"), vdf.index("key_press N, Pokedex"))  # slices swapped
        installed = sb.snapshot()
        # run again with no flag: the player's layout is kept, nothing changes
        r = sb.setup()
        self.assertIn("Already up to date", r.stdout)
        self.assertEqual(diff(installed, sb.snapshot()), [])
        # same layout again by file: also a no-op
        r = sb.setup("--layout", self.write(sb, custom(), "again.json"))
        self.assertEqual(diff({k: v for k, v in installed.items()},
                              {k: v for k, v in sb.snapshot().items() if not k.endswith("again.json")}), [])
        sb.setup("--uninstall")
        snap = {k: v for k, v in sb.snapshot().items() if not k.endswith(".json") or k in before}
        self.assertEqual(diff(before, snap), [])

    def test_reset_goes_back_to_the_default(self):
        sb = self.make()
        sb.setup()
        default_state = sb.snapshot()
        sb.setup("--layout", self.write(sb, custom()))
        sb.setup("--reset-layout")
        snap = {k: v for k, v in sb.snapshot().items() if not k.endswith("mine.json")}
        self.assertEqual(diff(default_state, snap), [])

    def test_default_layout_file_equals_no_layout(self):
        a, b = self.make(), self.make()
        a.setup()
        b.setup("--layout", self.write(b, L.default_layout()))
        for f in ("props", ):
            self.assertEqual(getattr(a, f).read_bytes(), getattr(b, f).read_bytes())
        self.assertEqual((a.cfg / "pokemmo" / "controller_ps5.vdf").read_bytes(),
                         (b.cfg / "pokemmo" / "controller_ps5.vdf").read_bytes())

    def test_macro_layouts_are_refused_and_nothing_changes(self):
        sb = self.make()
        before = sb.snapshot()
        bad = custom()
        bad["binds"]["KEY_A"] = {"button": 0, "turbo": True}
        f = self.write(sb, bad)
        r = sb.setup("--layout", f, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("one input", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        bad2 = custom()
        bad2["binds"]["KEY_SCREENSHOT"] = {"button": 0}
        f2 = self.write(sb, bad2, "b.json")
        self.assertNotEqual(sb.setup("--layout", f2, check=False).returncode, 0)
        self.assertEqual(diff(before, {k: v for k, v in sb.snapshot().items() if not k.endswith(".json")}), [])

    def test_nintendo_face_buttons_follow_the_printed_label(self):
        lay = custom()
        binds = L.native_binds(lay)
        entry = apply_native.encode_one("Nintendo Switch Pro Controller", True, binds)
        self.assertIn("KEY_A,BUTTON,1", entry)
        self.assertIn("KEY_INVENTORY,BUTTON,9", entry)   # not a face button: unchanged
        self.assertEqual(apply_native.encode_one("Xbox One Controller", True, binds).count("KEY_A,BUTTON,0"), 1)

    def test_uninstall_after_the_player_edited_the_file(self):
        sb = self.make()
        sb.setup("--layout", self.write(sb, custom()))
        with open(sb.props, "ab") as f:
            f.write(b"client.ui.theme=light\r\n")
        sb.setup("--uninstall")
        text = sb.props.read_text(encoding="utf-8")
        self.assertNotIn("KEY_RING_FOCUS", text)
        self.assertIn("client.ui.theme=light", text)

    def test_keyboard_binds_match_the_wheel_table(self):
        self.assertEqual(install_wheel.KEYBOARD_BINDS, L.keyboard_binds())

    def test_golden_vdfs_match_the_shipped_files(self):
        for t in install_wheel.CONTROLLER_TYPES:
            # git may check the files out with CRLF line endings on Windows
            shipped = (install_wheel.OUT_DIR / f"{t}.vdf").read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(install_wheel.encode(install_wheel.build_layout(t)), shipped, t)


if __name__ == "__main__":
    unittest.main()
