"""Pads that are plugged in are found by name, so their binds are written without a flag."""
import subprocess, sys, unittest

from helpers import Sandbox, TOOLS

sys.path.insert(0, str(TOOLS))
import platforms as P  # noqa: E402

PROC = """I: Bus=0003 Vendor=045e Product=028e Version=0110
N: Name="Microsoft X-Box 360 pad"
H: Handlers=js0 event5

I: Bus=0003 Vendor=046d Product=c52b Version=0111
N: Name="Logitech USB Receiver"
H: Handlers=sysrq kbd event3 leds

I: Bus=0005 Vendor=057e Product=2009 Version=8111
N: Name="Nintendo Switch Pro Controller"
H: Handlers=event9 js1
"""

WIN = "Xbox Wireless Controller\r\nHID-compliant mouse\r\nPS4 Controller\r\n\r\nXbox Wireless Controller\r\n"
MAC = '''|   "Product" = "DualSense Wireless Controller"
|   "Product" = "Apple Internal Keyboard / Trackpad"
|   "Product" = "Xbox Wireless Controller"
'''


class Parsers(unittest.TestCase):
    def test_linux_proc_lists_only_pads(self):
        self.assertEqual(P.parse_proc_input(PROC), ["Microsoft X-Box 360 pad", "Nintendo Switch Pro Controller"])

    def test_windows_names_are_deduped_and_filtered(self):
        self.assertEqual(P.parse_pad_lines(WIN), ["Xbox Wireless Controller", "PS4 Controller"])

    def test_mac_ioreg(self):
        self.assertEqual(P.parse_ioreg(MAC), ["DualSense Wireless Controller", "Xbox Wireless Controller"])

    def test_garbage_gives_nothing(self):
        for f in (P.parse_proc_input, P.parse_pad_lines, P.parse_ioreg):
            self.assertEqual(f(""), [])
            self.assertEqual(f("\x00\xff nonsense"), [])


class Install(unittest.TestCase):
    def test_connected_pad_is_bound_by_name(self):
        sb = Sandbox()
        try:
            sb.setup(env={"POKEMMO_CONTROLLER_TEST_PADS": "Acme Racing Wheel Controller"})
            self.assertIn("Acme Racing Wheel Controller", sb.props.read_text(encoding="utf-8"))
        finally:
            sb.cleanup()

    def test_no_pad_found_changes_nothing_in_tests(self):
        sb = Sandbox()
        try:
            sb.setup()
            self.assertNotIn("Acme", sb.props.read_text(encoding="utf-8"))
        finally:
            sb.cleanup()

    def test_real_detection_never_raises(self):
        code = "import sys; sys.path.insert(0, r'%s'); import platforms as P; print(len(P.connected_pad_names()))" % TOOLS
        sb = Sandbox()
        self.addCleanup(sb.cleanup)
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env=sb.env())
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
