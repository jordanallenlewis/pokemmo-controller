"""Every Python file in the project runs on Python 3.9, the oldest version it supports.

Some calls only fail on 3.9 when a rarely used branch runs (a script's write step, for
example), and CI's 3.9 legs never reach it. This reads every Python file and refuses the
calls that need a newer Python, so the check fails on every leg, not only on 3.9.
"""
import ast, subprocess, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# method name -> {keyword argument: the Python version that added it}
NEWER_KEYWORDS = {
    "write_text": {"newline": "3.10"},
    "read_text": {"newline": "3.13"},
}


def python_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z", "*.py"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                             check=True, stdin=subprocess.DEVNULL).stdout.split("\0")
        files = [ROOT / f for f in out if f]
    except (OSError, subprocess.CalledProcessError):
        files = [p for p in ROOT.rglob("*.py") if ".git" not in p.parts and "node_modules" not in p.parts]
    return [f for f in files if f.is_file()]


def newer_calls(source, name="<source>"):
    """(line, method, keyword, version) for each call that needs a Python newer than 3.9."""
    found = []
    for node in ast.walk(ast.parse(source, name)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            for kw in node.keywords:
                version = NEWER_KEYWORDS.get(node.func.attr, {}).get(kw.arg)
                if version:
                    found.append((node.lineno, node.func.attr, kw.arg, version))
    return found


class Python39(unittest.TestCase):
    def test_the_check_sees_a_newer_call(self):
        self.assertEqual(newer_calls('p.write_text(s, encoding="utf-8", newline="\\n")'),
                         [(1, "write_text", "newline", "3.10")])
        self.assertEqual(newer_calls('p.write_bytes(s.encode("utf-8"))'), [])

    def test_no_file_needs_a_newer_python(self):
        files = python_files()
        self.assertGreater(len(files), 20)
        problems = []
        for f in files:
            for line, method, kw, version in newer_calls(f.read_text(encoding="utf-8"), str(f)):
                problems.append(f"{f.relative_to(ROOT).as_posix()}:{line} {method}({kw}=) needs Python {version}")
        self.assertEqual(problems, [], "these calls fail on Python 3.9:\n" + "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
