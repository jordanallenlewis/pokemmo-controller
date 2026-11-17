"""A custom layout goes through the same writers and the same safety as the default:
one backup, exact uninstall, rerun is a no-op, and the rules refuse a macro."""
import hashlib, json, unittest
from pathlib import Path

from helpers import Sandbox
import layout as L
import apply_native, install_wheel
from test_setup import Base, diff


def legacy_switch_entry(binds):
    """The Switch entry the code before the fix wrote: only the four face actions moved."""
    old = dict(binds)
    for a in ("KEY_A", "KEY_B", "KEY_X", "KEY_Y"):
        if a in old and old[a][0] == "BUTTON" and old[a][1] in (0, 1, 2, 3):
            old[a] = ("BUTTON", {0: 1, 1: 0, 2: 3, 3: 2}[old[a][1]])
    return "Nintendo Switch Pro Controller;" + ";".join(apply_native._parts(old))


def clash():
    """Confirm on the right button, Bag on the bottom one, Cancel on RB."""
    lay = L.default_layout()
    lay["binds"]["KEY_A"] = {"button": 1}
    lay["binds"]["KEY_INVENTORY"] = {"button": 0}
    lay["binds"]["KEY_B"] = {"button": 10}
    return lay


def custom():
    lay = L.default_layout()
    lay["binds"]["KEY_INVENTORY"] = {"button": 9}   # Bag on LB
    lay["binds"]["KEY_RING_FOCUS"] = {"button": 10}   # Focus Ring on RB
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
        self.assertIn("KEY_RING_FOCUS,BUTTON,10", entry)
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

    def test_nintendo_swap_moves_buttons_not_actions(self):
        # On a Switch pad (printed A on the right) they become the bottom and right
        # buttons, never the same one.
        entry = apply_native.encode_one("Nintendo Switch Pro Controller", True, L.native_binds(clash()))
        self.assertIn("KEY_A,BUTTON,0", entry)
        self.assertIn("KEY_INVENTORY,BUTTON,1", entry)
        self.assertIn("KEY_B,BUTTON,10", entry)

    def test_entries_written_by_the_older_swap_are_still_ours(self):
        # a custom layout applied before the fix: update and uninstall must still know
        # that entry as this project's and replace or remove it
        binds = L.native_binds(clash())
        self.assertTrue(apply_native.is_ours(legacy_switch_entry(binds), apply_native.layout_sets(binds)))

    def test_rerun_and_uninstall_after_the_older_swap_wrote_a_custom_layout(self):
        sb = self.make()
        f = self.write(sb, clash())
        before = sb.snapshot()
        sb.setup("--layout", f)
        binds = L.native_binds(clash())
        text = sb.props.read_bytes().decode("utf-8")
        new_entry = apply_native.encode_one("Nintendo Switch Pro Controller", True, binds)
        self.assertIn(new_entry, text)
        sb.props.write_bytes(text.replace(new_entry, legacy_switch_entry(binds)).encode("utf-8"))
        sb.setup()                                   # rerun: the fixed entry is written back
        self.assertIn(new_entry, sb.props.read_bytes().decode("utf-8"))
        sb.props.write_bytes(sb.props.read_bytes().decode("utf-8")
                             .replace(new_entry, legacy_switch_entry(binds)).encode("utf-8"))
        sb.setup("--uninstall")
        self.assertNotIn("KEY_RING_FOCUS", sb.props.read_text(encoding="utf-8"))
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_uninstall_after_the_player_edited_the_file(self):
        sb = self.make()
        sb.setup("--layout", self.write(sb, custom()))
        with open(sb.props, "ab") as f:
            f.write(b"client.ui.theme=light\r\n")
        sb.setup("--uninstall")
        text = sb.props.read_text(encoding="utf-8")
        self.assertNotIn("KEY_RING_FOCUS", text)
        self.assertIn("client.ui.theme=light", text)

    def pushed_trigger_install(self, sb):
        """What the code before the trigger rule wrote for a layout with Screenshot on LT
        pushed away (a bind that never fires): the map entries and the install record."""
        lay = custom()
        f = self.write(sb, lay)
        sb.setup("--layout", f)
        Path(f).unlink()
        old = json.loads(json.dumps(lay))
        old["binds"]["KEY_SCREENSHOT"] = {"axis": 4, "positive": False}
        now, then = L.native_binds(lay), dict(L.native_binds(lay), KEY_SCREENSHOT=("AXIS", 4, False))
        rec_path = sb.pokemmo / "config" / "pokemmo-controller.json"
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        swap = {apply_native.encode_one(n, True, now): apply_native.encode_one(n, True, then) for n in rec["names"]}
        lines = sb.props.read_bytes().decode("utf-8").split("\r\n")
        key = apply_native.MAP_KEY + "="
        i = [j for j, ln in enumerate(lines) if ln.startswith(key)][0]
        entries = lines[i][len(key):].split("|")
        self.assertEqual(len(set(swap) & set(entries)), len(rec["names"]))
        lines[i] = key + "|".join(swap.get(e, e) for e in entries)
        text = "\r\n".join(lines)
        sb.props.write_bytes(text.encode("utf-8"))
        rec["layout"] = old
        key = [k for k in rec["files"] if k.endswith("main.properties")][0]
        rec["files"][key]["sha"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        rec_path.write_text(json.dumps(rec), encoding="utf-8")
        return rec_path

    def test_update_keeps_a_layout_saved_with_a_pushed_trigger_and_says_what_changed(self):
        sb = self.make()
        rec_path = self.pushed_trigger_install(sb)
        r = sb.setup()
        self.assertIn("Screenshot", r.stdout)
        self.assertIn("not bound", r.stdout)
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        expected = custom()
        del expected["binds"]["KEY_SCREENSHOT"]
        self.assertEqual(rec["layout"], expected)        # the rest of the player's layout is kept
        text = sb.props.read_text(encoding="utf-8")
        self.assertNotIn("KEY_SCREENSHOT,AXIS", text)
        self.assertIn("KEY_INVENTORY,BUTTON,9", text)
        vdf = (sb.cfg / "pokemmo" / "controller_xboxone.vdf").read_text()
        self.assertLess(vdf.index("key_press I, Egg Incubators"), vdf.index("key_press N, Pokedex"))

    def test_uninstall_removes_a_layout_saved_with_a_pushed_trigger(self):
        for edited in (False, True):
            with self.subTest(edited=edited):
                sb = self.make()
                before = sb.snapshot()
                self.pushed_trigger_install(sb)
                if edited:   # something else changed the file, so the exact restore cannot run
                    with open(sb.props, "ab") as f:
                        f.write(b"client.ui.theme=light\r\n")
                sb.setup("--uninstall")
                text = sb.props.read_text(encoding="utf-8")
                self.assertNotIn("KEY_RING_FOCUS", text)
                self.assertNotIn("KEY_SCREENSHOT", text)
                if edited:
                    self.assertIn("client.ui.theme=light", text)
                else:
                    self.assertEqual(diff(before, sb.snapshot()), [])

    def test_keyboard_binds_match_the_wheel_table(self):
        self.assertEqual(install_wheel.KEYBOARD_BINDS, L.keyboard_binds())

    def test_golden_vdfs_match_the_shipped_files(self):
        for t in install_wheel.CONTROLLER_TYPES:
            # git may check the files out with CRLF line endings on Windows
            shipped = (install_wheel.OUT_DIR / f"{t}.vdf").read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(install_wheel.encode(install_wheel.build_layout(t)), shipped, t)


if __name__ == "__main__":
    unittest.main()
