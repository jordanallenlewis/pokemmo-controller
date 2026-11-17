"""The View button opens the map (it presses Hotbar 5, where the player keeps the Town Map);
the Focus Ring sits on LB. An install written by an earlier version, with the Focus Ring on
View, is replaced on update and removed on uninstall like any other of this project's maps.
"""
import json, unittest

from test_setup import Base, diff
import common, apply_native, layout as L

VIEW, LB = 4, 9


class MapButton(Base):
    def test_default_view_is_the_map_slot_and_lb_is_the_focus_ring(self):
        binds = L.default_layout()["binds"]
        self.assertEqual(binds["KEY_HOTBAR_5"], {"button": VIEW})
        self.assertEqual(binds["KEY_RING_FOCUS"], {"button": LB})
        # the shipped native layout and the layout model agree
        self.assertEqual(apply_native.LAYOUT["KEY_HOTBAR_5"], ("BUTTON", VIEW))
        self.assertEqual(apply_native.LAYOUT["KEY_RING_FOCUS"], ("BUTTON", LB))

    def test_every_pad_name_gets_it_and_no_input_is_shared(self):
        sb = self.make()
        sb.setup()
        text = sb.props.read_text(encoding="utf-8")
        for entry in apply_native.split_entries(
                next(l for l in text.splitlines() if l.startswith(common.MAP_KEY + "=")).split("=", 1)[1]).values():
            if not apply_native.is_ours(entry):
                continue
            parts = [p for p in entry.split(";")[1:] if p]
            self.assertIn("KEY_HOTBAR_5,BUTTON,4", parts)
            self.assertIn("KEY_RING_FOCUS,BUTTON,9", parts)
            inputs = [p.split(",", 1)[1] for p in parts]
            self.assertEqual(len(inputs), len(set(inputs)), "one input does one action")

    def test_an_install_from_before_is_updated_and_uninstall_is_exact(self):
        sb = self.make()
        before = sb.snapshot()
        sb.setup()
        # make the file look like v1.1: Focus Ring on View, Hotbar 5 on LB, an older version
        old = apply_native.LEGACY_LAYOUT
        text = sb.props.read_text(encoding="utf-8")
        new_entries = apply_native.split_entries(
            next(l for l in text.splitlines() if l.startswith(common.MAP_KEY + "=")).split("=", 1)[1])
        for name, entry in new_entries.items():
            if apply_native.is_ours(entry):
                text = text.replace(entry, entry.replace("KEY_HOTBAR_5,BUTTON,4", "KEY_HOTBAR_5,BUTTON,9")
                                    .replace("KEY_RING_FOCUS,BUTTON,9", "KEY_RING_FOCUS,BUTTON,4"))
        sb.props.write_text(text, encoding="utf-8")
        st_file = sb.pokemmo / "config" / common.STATE_NAME
        st = json.loads(st_file.read_text())
        st["version"] = "1.0.5"
        st_file.write_text(json.dumps(st))
        self.assertIn("KEY_RING_FOCUS,BUTTON,4", sb.props.read_text(encoding="utf-8"))
        r = sb.setup()
        self.assertIn("Updated from v1.0.5", r.stdout)
        out = sb.props.read_text(encoding="utf-8")
        self.assertNotIn("KEY_RING_FOCUS,BUTTON,4", out)
        self.assertIn("KEY_HOTBAR_5,BUTTON,4", out)
        sb.setup("--uninstall")
        self.assertEqual(diff(before, sb.snapshot()), [])

    def test_uninstall_removes_the_old_layout_even_after_the_file_was_edited(self):
        sb = self.make()
        before = sb.snapshot()
        sb.setup()
        text = sb.props.read_text(encoding="utf-8")
        entries = apply_native.split_entries(
            next(l for l in text.splitlines() if l.startswith(common.MAP_KEY + "=")).split("=", 1)[1])
        for entry in entries.values():
            if apply_native.is_ours(entry):
                text = text.replace(entry, entry.replace("KEY_HOTBAR_5,BUTTON,4", "KEY_HOTBAR_5,BUTTON,9")
                                    .replace("KEY_RING_FOCUS,BUTTON,9", "KEY_RING_FOCUS,BUTTON,4"))
        sb.props.write_text(text + "client.ui.theme=dark\n", encoding="utf-8")   # the player changed another line too
        sb.setup("--uninstall")
        self.assertNotIn("KEY_RING_FOCUS", sb.props.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
