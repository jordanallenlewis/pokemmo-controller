"""Release files for the updater: the archive, SHA256SUMS, update.json and its signature.

  python .github/release_meta.py build  --tag v1.4.0 --out dist     archive + SHA256SUMS + update.json
  python .github/release_meta.py sign   --out dist                  update.json.sig (key: env UPDATE_SIGNING_KEY)
  python .github/release_meta.py verify --out dist --tag v1.4.0     fails unless everything checks out

The release workflow runs all three on every version tag; a tag whose files do not verify
publishes nothing. The signing key is a base64 32-byte seed held in the repository's
Actions secrets; the matching public key is tools/update_key.py.
"""
import argparse, base64, gzip, hashlib, io, json, os, re, sys, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import ed25519, updater  # noqa: E402

FILES = ["install.sh", "install.ps1", "LICENSE"]
TOOL_SUFFIXES = (".py", ".html", ".json", ".css")


def version_of(tag):
    v = tag[1:] if tag.startswith("v") else tag
    updater.parse_version(v)
    return v


def release_files(root=ROOT):
    out = [f for f in FILES if (root / f).is_file()]
    for d in ("tools", "steam"):
        out += sorted(p.relative_to(root).as_posix() for p in (root / d).iterdir()
                      if p.is_file() and (d == "steam" or p.suffix in TOOL_SUFFIXES))
    return out


def notes_for(version, root=ROOT):
    """Up to three bullets from this version's CHANGELOG section, as plain lines."""
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"^## %s\b.*?$(.*?)(?=^## |\Z)" % re.escape(version), text, re.M | re.S)
    if not m:
        raise SystemExit(f"CHANGELOG.md has no section for {version}: write what changed for players first.")
    bullets, cur = [], None
    for line in m.group(1).splitlines():
        if line.startswith("- "):
            cur = [line[2:].strip()]
            bullets.append(cur)
        elif line.startswith("  ") and cur is not None and line.strip():
            cur.append(line.strip())
        elif not line.strip():
            cur = None
    notes = [" ".join(b) for b in bullets][:3]
    if not notes:
        raise SystemExit(f"CHANGELOG.md section {version} has no bullet points.")
    return notes


def build(tag, out, root=ROOT):
    version = version_of(tag)
    if updater.tools_version(root) != version:
        raise SystemExit(f"tools/common.py says {updater.tools_version(root)} but the tag is {version}. "
                         "Bump VERSION first.")
    out.mkdir(parents=True, exist_ok=True)
    name = f"pokemmo-controller-{version}.tar.gz"
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as t:
            for rel in release_files(root):
                data = (root / rel).read_bytes()
                ti = tarfile.TarInfo(f"pokemmo-controller-{version}/{rel}")
                ti.size, ti.mtime, ti.mode = len(data), 0, 0o644
                t.addfile(ti, io.BytesIO(data))
    blob = raw.getvalue()
    (out / name).write_bytes(blob)
    sha = hashlib.sha256(blob).hexdigest()
    (out / "SHA256SUMS").write_text(f"{sha}  {name}\n")
    manifest = {"schema": 1, "version": version, "channel": "beta" if "-" in version else "stable",
                "url": f"{updater.ASSET_PREFIX}v{version}/{name}", "sha256": sha, "size": len(blob),
                "notes": notes_for(version, root)}
    (out / updater.MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def sign(out):
    key = os.environ.get("UPDATE_SIGNING_KEY", "").strip()
    if not key:
        raise SystemExit("UPDATE_SIGNING_KEY is not set: a release without a signed update.json is not published.")
    seed = base64.b64decode(key, validate=True)
    if len(seed) != 32:
        raise SystemExit("UPDATE_SIGNING_KEY must be a base64 32-byte seed.")
    raw = (out / updater.MANIFEST).read_bytes()
    (out / updater.SIGNATURE).write_text(base64.b64encode(ed25519.sign(seed, raw)).decode() + "\n")


def verify(out, tag=None):
    """The same checks a player's computer makes, plus: the archive is the one the manifest names."""
    m = updater.verify_manifest((out / updater.MANIFEST).read_bytes(), (out / updater.SIGNATURE).read_text())
    if tag and m["version"] != version_of(tag):
        raise SystemExit(f"update.json says {m['version']} but the tag is {tag}.")
    asset = out / m["url"].rsplit("/", 1)[1]
    blob = asset.read_bytes()
    if hashlib.sha256(blob).hexdigest() != m["sha256"] or len(blob) != m["size"]:
        raise SystemExit("The archive does not match update.json.")
    if f"{m['sha256']}  {asset.name}" not in (out / "SHA256SUMS").read_text():
        raise SystemExit("SHA256SUMS does not list the archive.")
    if not m["notes"]:
        raise SystemExit("update.json has no notes.")
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("build", "sign", "verify"))
    ap.add_argument("--tag")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if a.cmd == "build":
        if not a.tag:
            sys.exit("--tag is required")
        print(json.dumps(build(a.tag, out), indent=2))
    elif a.cmd == "sign":
        sign(out)
        print("signed", out / updater.SIGNATURE)
    else:
        m = verify(out, a.tag)
        print(f"ok: v{m['version']} ({m['channel']}) signed and consistent")


if __name__ == "__main__":
    main()
