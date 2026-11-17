"""Which window is "the game": the PokeMMO program's window, not a browser tab or folder with
PokeMMO in its name (a wrong pick sizes the wheel for the wrong picture)."""
import unittest

import helpers  # noqa: F401
import platforms as P

pick = P.pick_game_window


class Pick(unittest.TestCase):
    def test_game_beats_a_browser_tab_on_top_of_it(self):
        wins = [("PokeMMO Forums - Google Chrome", "chrome.exe", 1280, 720, False),
                ("PokeMMO", "PokeMMO.exe", 3840, 2160, False)]
        self.assertEqual(pick(wins), ("size", (3840, 2160)))

    def test_explorer_folder_and_terminal_are_not_the_game(self):
        wins = [("PokeMMO", "explorer.exe", 900, 600, False),
                ("PokeMMO controller install", "WindowsTerminal.exe", 800, 500, False)]
        self.assertEqual(pick(wins), (None, None))

    def test_borderless_windowed_and_fullscreen_all_read_the_client_area(self):
        for size in ((3840, 2160), (2560, 1440), (1920, 1080), (1896, 1016), (1280, 720)):
            self.assertEqual(pick([("PokeMMO", "PokeMMO.exe", *size, False)]), ("size", size))

    def test_minimized_game_is_not_the_main_screen(self):
        self.assertEqual(pick([("PokeMMO", "PokeMMO.exe", 0, 0, True)]), ("minimized", None))
        # a minimized game and a shown launcher: the shown one is read
        self.assertEqual(pick([("PokeMMO", "PokeMMO.exe", 0, 0, True), ("PokeMMO", "PokeMMO.exe", 640, 480, False)]),
                         ("size", (640, 480)))

    def test_largest_game_window_wins_and_unknown_program_falls_back_to_the_exact_title(self):
        self.assertEqual(pick([("PokeMMO", "PokeMMO.exe", 640, 480, False),
                               ("PokeMMO", "PokeMMO.exe", 1920, 1080, False)]), ("size", (1920, 1080)))
        self.assertEqual(pick([("PokeMMO", "", 1920, 1080, False)]), ("size", (1920, 1080)))
        self.assertEqual(pick([("PokeMMO Forums", "", 1920, 1080, False)]), (None, None))

    def test_nothing_open(self):
        self.assertEqual(pick([]), (None, None))


if __name__ == "__main__":
    unittest.main()
