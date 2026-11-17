"""The layout core: the model, the default, and the macro policy (1 input = 1 action).

Every forbidden thing is tried here and must be refused. Run:
    python -m unittest discover -s tests -v
"""
import copy, json, unittest

import helpers  # noqa: F401  (puts tools/ on the path, test mode on)
import layout as L


def default():
    return L.default_layout()


class Model(unittest.TestCase):
    def test_default_is_valid(self):
        L.validate(default())

    def test_default_matches_the_shipped_binds(self):
        import apply_native
        got = L.native_binds(default())
        self.assertEqual(got, apply_native.LAYOUT)

    def test_default_wheel_is_the_shipped_wheel(self):
        import install_wheel
        self.assertEqual(L.wheel_slices(default()), install_wheel.WHEEL)

    def test_round_trip_through_json(self):
        text = L.dumps(default())
        self.assertEqual(L.loads(text), default())
        self.assertTrue(text.endswith("\n"))

    def test_move_a_button(self):
        lay = default()
        lay["binds"]["KEY_INVENTORY"] = {"button": 9}   # LB; was RB
        lay["binds"]["KEY_HOTBAR_5"] = {"button": 10}   # swap
        L.validate(lay)
        self.assertEqual(L.native_binds(lay)["KEY_INVENTORY"], ("BUTTON", 9))

    def test_reorder_wheel(self):
        lay = default()
        lay["wheel"] = list(reversed(lay["wheel"]))
        L.validate(lay)
        self.assertEqual(L.wheel_slices(lay)[0], ("F12", "Hide GUI"))

    def test_unbound_action_is_allowed(self):
        lay = default()
        del lay["binds"]["KEY_SCREENSHOT"]
        L.validate(lay)
        self.assertNotIn("KEY_SCREENSHOT", L.native_binds(lay))


class MacroPolicy(unittest.TestCase):
    """1 input = 1 action. Each way of breaking it is refused with a clear reason."""

    def refused(self, lay, *words):
        with self.assertRaises(L.LayoutError) as cm:
            L.validate(lay)
        msg = str(cm.exception).lower()
        for w in words:
            self.assertIn(w.lower(), msg)
        return msg

    def test_one_input_for_two_actions(self):
        lay = default()
        lay["binds"]["KEY_SCREENSHOT"] = {"button": 0}  # same as KEY_A
        self.refused(lay, "one input", "KEY_A")

    def test_one_axis_direction_for_two_actions(self):
        lay = default()
        lay["binds"]["KEY_SCREENSHOT"] = {"axis": 5, "positive": True}  # same as KEY_NEXT
        self.refused(lay, "one input")

    def test_two_actions_for_one_input_as_a_list(self):
        lay = default()
        lay["binds"]["KEY_A"] = [{"button": 0}, {"button": 1}]
        self.refused(lay, "exactly one")

    def test_action_list_on_one_input(self):
        lay = default()
        lay["binds"]["KEY_A"] = {"button": 0, "actions": ["KEY_B"]}
        self.refused(lay, "unknown field")

    def test_forbidden_fields(self):
        for field in ("turbo", "repeat", "auto_repeat", "rapid_fire", "sequence", "combo", "macro",
                      "delay", "hold", "interval", "chain", "toggle", "cursor", "click", "script"):
            with self.subTest(field=field):
                lay = default()
                lay["binds"]["KEY_A"] = {"button": 0, field: True}
                self.refused(lay, "unknown field", field)

    def test_forbidden_top_level(self):
        for field in ("macros", "turbo", "sequences", "layers", "delay"):
            with self.subTest(field=field):
                lay = default()
                lay[field] = []
                self.refused(lay, "unknown field", field)

    def test_unknown_action(self):
        lay = default()
        lay["binds"]["KEY_MACRO_1"] = {"button": 3}
        self.refused(lay, "unknown action")

    def test_input_out_of_range(self):
        for spec in ({"button": 15}, {"button": -1}, {"axis": 6, "positive": True},
                     {"button": True}, {"button": "1"}, {"button": 1.0}):
            with self.subTest(spec=spec):
                lay = default()
                lay["binds"]["KEY_SCREENSHOT"] = spec
                with self.assertRaises(L.LayoutError):
                    L.validate(lay)

    def test_axis_needs_a_direction(self):
        lay = default()
        lay["binds"]["KEY_SCREENSHOT"] = {"axis": 4}
        self.refused(lay, "positive")

    def test_trigger_only_works_pulled(self):
        # SDL3 reports a trigger from 0 (released) to its maximum (pulled): the other
        # direction never happens, so such a bind would be a dead button. Refuse it.
        for axis in (4, 5):
            with self.subTest(axis=axis):
                lay = default()
                lay["binds"]["KEY_SCREENSHOT"] = {"axis": axis, "positive": False}
                self.refused(lay, "KEY_SCREENSHOT", "trigger", "pulled")

    def test_trigger_pulled_still_works(self):
        lay = default()
        lay["binds"]["KEY_NEXT"] = {"button": 8}
        lay["binds"]["KEY_SCREENSHOT"] = {"axis": 5, "positive": True}
        L.validate(lay)
        self.assertEqual(L.native_binds(lay)["KEY_SCREENSHOT"], ("AXIS", 5, True))

    def test_hand_edited_file_with_a_pushed_trigger_is_refused(self):
        lay = default()
        lay["binds"]["KEY_PREVIOUS"] = {"axis": 4, "positive": False}
        with self.assertRaises(L.LayoutError) as cm:
            L.loads(json.dumps(lay))
        self.assertIn("trigger", str(cm.exception))

    def test_inputs_lists_exactly_what_a_bind_may_use(self):
        ok = []
        for spec in ([{"button": n} for n in range(-1, L.BUTTONS + 1)]
                     + [{"axis": a, "positive": p} for a in range(-1, L.AXES + 1) for p in (False, True)]):
            lay = default()
            lay["binds"] = {"KEY_A": spec}
            try:
                L.validate(lay)
                ok.append(spec)
            except L.LayoutError:
                pass
        self.assertEqual(ok, L.inputs())
        self.assertGreaterEqual(len(L.inputs()), len(L.ACTIONS))

    def test_a_record_with_a_pushed_trigger_keeps_the_rest_and_names_what_was_dropped(self):
        old = default()
        old["binds"]["KEY_SCREENSHOT"] = {"axis": 4, "positive": False}
        fixed, dropped = L.recorded(old)
        self.assertEqual(dropped, ["KEY_SCREENSHOT"])
        self.assertNotIn("KEY_SCREENSHOT", fixed["binds"])
        self.assertEqual(old["binds"]["KEY_SCREENSHOT"], {"axis": 4, "positive": False})  # not changed in place
        L.validate(fixed)
        self.assertEqual(L.recorded_binds(old)["KEY_SCREENSHOT"], ("AXIS", 4, False))
        self.assertEqual(L.recorded(default()), (default(), []))

    def test_a_record_is_still_refused_for_everything_else(self):
        bad = []
        lay = default(); lay["binds"]["KEY_SCREENSHOT"] = {"axis": 4, "positive": False, "turbo": True}; bad.append(lay)
        lay = default(); lay["binds"]["KEY_SCREENSHOT"] = {"axis": 5, "positive": True}; bad.append(lay)  # = KEY_NEXT
        lay = default(); lay["binds"]["KEY_SCREENSHOT"] = {"axis": 4, "positive": False}
        lay["binds"]["KEY_TEAM"] = {"axis": 4, "positive": False}; bad.append(lay)                     # shared
        lay = default(); lay["macro"] = ["KEY_A", "KEY_A"]; bad.append(lay)
        for lay in bad:
            with self.subTest(lay=lay):
                with self.assertRaises(L.LayoutError):
                    L.recorded(lay)
                with self.assertRaises(L.LayoutError):
                    L.recorded_binds(lay)

    def test_sticks_still_work_both_ways(self):
        lay = default()
        lay["binds"]["KEY_UP"], lay["binds"]["KEY_DOWN"] = lay["binds"]["KEY_DOWN"], lay["binds"]["KEY_UP"]
        L.validate(lay)

    def test_button_and_axis_together(self):
        lay = default()
        lay["binds"]["KEY_SCREENSHOT"] = {"button": 8, "axis": 4, "positive": True}
        self.refused(lay, "exactly one")

    def test_right_stick_is_the_wheel(self):
        lay = default()
        lay["binds"]["KEY_SCREENSHOT"] = {"axis": 2, "positive": True}
        self.refused(lay, "wheel")

    def test_wheel_slice_is_one_action(self):
        lay = default()
        lay["wheel"][0] = ["codex", "incubator"]
        self.refused(lay, "one action")

    def test_wheel_slice_repeated(self):
        lay = default()
        lay["wheel"][1] = lay["wheel"][0]
        self.refused(lay, "once")

    def test_wheel_slice_unknown_action(self):
        lay = default()
        lay["wheel"][0] = "run_script"
        self.refused(lay, "unknown")

    def test_wheel_slice_with_key_sequence(self):
        lay = default()
        lay["wheel"][0] = {"action": "codex", "then": "bag"}
        with self.assertRaises(L.LayoutError):
            L.validate(lay)

    def test_wheel_size_is_fixed(self):
        for n in (9, 11, 0):
            with self.subTest(n=n):
                lay = default()
                lay["wheel"] = (lay["wheel"] + ["x"] * 3)[:n]
                with self.assertRaises(L.LayoutError):
                    L.validate(lay)

    def test_wrong_types(self):
        for bad in ([], "x", 3, None):
            with self.assertRaises(L.LayoutError):
                L.validate(bad)
        lay = default()
        lay["binds"] = []
        with self.assertRaises(L.LayoutError):
            L.validate(lay)

    def test_hand_edited_file_is_refused_on_load(self):
        lay = default()
        lay["binds"]["KEY_A"] = {"button": 0, "turbo": True}
        with self.assertRaises(L.LayoutError):
            L.loads(json.dumps(lay))

    def test_garbage_file(self):
        for text in ("", "{", "[1]", "null", "\x00\x01", '{"format": 99}'):
            with self.subTest(text=text):
                with self.assertRaises(L.LayoutError):
                    L.loads(text)

    def test_duplicate_json_keys_refused(self):
        text = L.dumps(default()).replace('"KEY_A":', '"KEY_A": {"button": 3}, "KEY_A":', 1)
        with self.assertRaises(L.LayoutError):
            L.loads(text)

    def test_oversized_file(self):
        with self.assertRaises(L.LayoutError):
            L.loads(" " * (L.MAX_BYTES + 1))

    def test_validate_does_not_mutate(self):
        lay = default()
        before = copy.deepcopy(lay)
        L.validate(lay)
        self.assertEqual(lay, before)


if __name__ == "__main__":
    unittest.main()
