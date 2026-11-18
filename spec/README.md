# spec/: the locked contracts

These files are the contracts from `docs/FOUNDATION.md` section 3. Within a major version they may only grow. Removing or renaming anything needs a decision record under `docs/decisions/`, a migration that still reads the old form, and a new golden file. A change here needs the `spec-change` label and Jordan's approval.

| Folder | What it holds | Made by |
|---|---|---|
| `schema/` | JSON Schemas: profile format 1 and 2, install record, `pmc.cli/1` envelope, `pmc.update/1` manifest | by hand, checked by `tests/test_spec.py` |
| `golden/sandbox-trees.json` | The file tree after each step (install, rerun, update, uninstall...) of ten sandbox scenarios | `python tests/gen_spec_golden.py --write` |
| `golden/records.json` | The install record written today and the rules for reading older and newer ones | the same script |
| `golden/share-code.json` | `PMC1-` share codes made by the Go helper, with the layout each reads back to | `PMC_WRITE_SPEC=1 go test -run ShareCodeVectors` in `helper/` |
| `cli/` | Example `--json` envelopes (transcripts come with the Rust `pmc` binary) | by hand |
| `fixtures/` | An example update manifest | by hand |

How a tree is normalised so it is the same on every machine: the sandbox folder becomes `<ROOT>`, the tool version `<VERSION>`, the Steam appid `<APPID>`, and line endings are compared as LF. A file whose bytes hold the sandbox path (the Steam shortcut list and the install record, because the shortcut's appid comes from its path) is listed as `{"path": true}` with no hash; the record is stored parsed, without those hashes.

The goldens from `tests/golden/` (layout, props, native map, plan, shortcuts, wheel VDF, layout plan) stay where they are until M2 moves them here, so the Go helper and the Python tests keep working.

Python 1.x is the source of truth for behaviour until the Rust port matches these files byte for byte.
