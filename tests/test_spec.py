"""The frozen contracts under spec/ (FOUNDATION section 3): schemas accept what the Python tools write
and refuse what the product rules refuse; the behaviour goldens are exactly what Python does today."""
import copy, json, unittest

import helpers
from helpers import ROOT
import gen_spec_golden as G
import jsonschema_lite as J
import layout as L

SCHEMA = ROOT / "spec" / "schema"


def schema(name):
    return json.loads((SCHEMA / name).read_text(encoding="utf-8"))


def check(value, name):
    return J.errors(value, schema(name), SCHEMA)


class Profile(unittest.TestCase):
    def test_default_layout_is_a_valid_format_1_profile(self):
        self.assertEqual(check(json.loads(L.dumps(L.default_layout())), "profile-1.schema.json"), [])

    def test_unknown_fields_and_macro_shapes_are_refused(self):
        for field in ({"turbo": True}, {"repeat": 50}, {"macro": "x"}):
            lay = L.default_layout()
            lay["binds"]["KEY_A"] = dict(lay["binds"]["KEY_A"], **field)
            self.assertTrue(check(lay, "profile-1.schema.json"), field)
        lay = L.default_layout()
        lay["binds"]["KEY_A"] = [{"button": 0}, {"button": 1}]
        self.assertTrue(check(lay, "profile-1.schema.json"))

    def test_wheel_needs_ten_unique_ids(self):
        lay = L.default_layout()
        lay["wheel"] = lay["wheel"][:9]
        self.assertTrue(check(lay, "profile-1.schema.json"))
        lay["wheel"] = lay["wheel"] + [lay["wheel"][0]]
        self.assertTrue(check(lay, "profile-1.schema.json"))

    def test_format_2_adds_metadata_only(self):
        lay = json.loads(L.dumps(L.default_layout()))
        lay.update({"format": 2, "$schema": "x", "id": "a", "created_by": "2.0.0", "pad_hint": "xbox"})
        self.assertEqual(check(lay, "profile-2.schema.json"), [])
        self.assertTrue(check(dict(lay, turbo=True), "profile-2.schema.json"))
        self.assertTrue(check(dict(lay, format=1), "profile-2.schema.json"))

    def test_every_action_id_and_wheel_id_is_in_the_schema(self):
        p = schema("profile-1.schema.json")
        self.assertEqual(list(p["properties"]["binds"]["properties"]), list(L.ACTIONS))
        self.assertEqual(p["properties"]["wheel"]["items"]["enum"], list(L.WHEEL_ACTIONS))


class Record(unittest.TestCase):
    def test_records_written_today_fit(self):
        for name, steps in G.scenarios().items():
            for s in steps:
                if s.get("record"):
                    rec = dict(s["record"])
                    # files{} hashes were dropped for path-dependent files in the golden
                    for v in rec.get("files", {}).values():
                        v.setdefault("sha", "0" * 64)
                    self.assertEqual(check(rec, "record.schema.json"), [], f"{name}: {s['step']}")

    def test_locked_keys_are_in_the_golden(self):
        rec = json.loads((ROOT / "spec" / "golden" / "records.json").read_text(encoding="utf-8"))
        cur = rec["current_python_record"]
        for k in ("version", "files", "names", "extra_names", "switch_positional", "created_dirs"):
            self.assertIn(k, cur)


class CliAndUpdate(unittest.TestCase):
    def test_examples_fit_their_schemas(self):
        for f in sorted((ROOT / "spec" / "cli").glob("*.json")):
            self.assertEqual(check(json.loads(f.read_text(encoding="utf-8")), "cli.schema.json"), [], f.name)
        ex = json.loads((ROOT / "spec" / "fixtures" / "update-manifest.example.json").read_text(encoding="utf-8"))
        self.assertEqual(check(ex, "update-1.schema.json"), [])

    def test_a_manifest_cannot_carry_a_downgrade_or_http(self):
        ex = json.loads((ROOT / "spec" / "fixtures" / "update-manifest.example.json").read_text(encoding="utf-8"))
        bad = copy.deepcopy(ex)
        bad["seq"] = 0
        self.assertTrue(check(bad, "update-1.schema.json"))
        bad = copy.deepcopy(ex)
        bad["artifacts"]["windows-x64"]["url"] = "http://example.com/x"
        self.assertTrue(check(bad, "update-1.schema.json"))
        bad = copy.deepcopy(ex)
        bad["channel"] = "nightly"
        self.assertTrue(check(bad, "update-1.schema.json"))

    def test_exit_codes_are_the_locked_list(self):
        self.assertEqual(sorted(schema("cli.schema.json")["x-exit-codes"], key=int),
                         ["0", "1", "2", "3", "4", "5", "6", "7", "10"])


def _first_difference(a, b, path=""):
    """Where two decoded documents first differ, so a failure on one system says what to look at."""
    if type(a) is not type(b):
        return f"{path or '/'}: {a!r} vs {b!r}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return f"{path}/{k}: only in {'golden' if k in a else 'this run'}"
            d = _first_difference(a[k], b[k], f"{path}/{k}")
            if d:
                return d
    elif isinstance(a, list):
        for i, (x, y) in enumerate(zip(a, b)):
            d = _first_difference(x, y, f"{path}[{i}]")
            if d:
                return d
        if len(a) != len(b):
            return f"{path}: {len(a)} items vs {len(b)}"
    elif a != b:
        return f"{path}: {str(a)[:200]!r} vs {str(b)[:200]!r}"
    return ""


class GoldensAreCurrent(unittest.TestCase):
    def test_files_match_python(self):
        for name, doc in G.build().items():
            have = (G.OUT_DIR / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
            want = G.dump(doc)
            self.assertEqual(have, want, f"run: python tests/gen_spec_golden.py --write ({name}); "
                             f"first difference: {_first_difference(json.loads(have), json.loads(want))}")

    def test_uninstall_restores_exact_bytes(self):
        trees = json.loads((G.OUT_DIR / "sandbox-trees.json").read_text(encoding="utf-8"))["scenarios"]
        for name in ("install-rerun-uninstall", "lf-line-endings", "no-wheel", "switch-positional", "no-steam",
                     "update-from-v1.1.0", "update-from-v1.2.0"):
            steps = trees[name]
            self.assertEqual(steps[-1]["tree"], steps[0]["tree"], name)
            self.assertIsNone(steps[-1]["record"], name)

    def test_follower_never_writes_for_junk_or_the_login_window(self):
        seqs = json.loads((G.OUT_DIR / "follower-sequences.json").read_text(encoding="utf-8"))["sequences"]
        by = {s["label"]: s for s in seqs}
        for label in ("the 640x480 login window is skipped", "a half-finished resize (wider than 8 to 1) is skipped",
                      "fast flap 4K 1080p 1440p 4K leaves no stale size"):
            self.assertEqual([w for w in by[label]["writes"] if w], [], label)
        self.assertEqual([w for w in by["settles after three equal samples"]["writes"] if w], [[1920, 1080]])

    def test_rerun_changes_nothing(self):
        steps = G.json.loads((G.OUT_DIR / "sandbox-trees.json").read_text(encoding="utf-8"))["scenarios"]["install-rerun-uninstall"]
        self.assertEqual(steps[1]["tree"], steps[2]["tree"])
        self.assertTrue(any("Already up to date" in l for l in steps[2]["output"]))


if __name__ == "__main__":
    unittest.main()
