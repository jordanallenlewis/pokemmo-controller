"""Keep the wheel the right size while the game's resolution changes (setup.py --follow).

Steam draws the wheel in screen pixels and reads its size from a layout file. This watches
the size of the game picture and, when it settles on a new size, rewrites only the wheel
layout files (the same writer the installer uses). Rules, all in this one place:

  - a sample that is zero, negative, tiny, huge, not whole numbers or half a number
    (windows briefly report these mid-switch) is ignored and the last good size stays;
  - a new size must be seen several times in a row before it is used (debounce), so a
    fast 4K -> 1080p -> 1440p -> 4K never leaves a stale size behind;
  - a change that gives the same wheel size (a move to another monitor at the same
    resolution, a window nudged a few pixels) writes nothing;
  - the size is never above the 4K wheel's share of the picture, so it fits at any size.
It sends no input to anything and never touches the game.
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as L  # noqa: E402

SETTLE = 3            # equal samples in a row before a new size counts
MAX_ASPECT = 8        # wider or taller than 8:1 is a half-finished resize, not a picture


def sanitize(sample):
    """(w, h) of a usable sample, else None."""
    try:
        w, h = sample
        if isinstance(w, bool) or isinstance(h, bool):
            return None
        if isinstance(w, float) and w == int(w):
            w = int(w)
        if isinstance(h, float) and h == int(h):
            h = int(h)
        w, h = L.check_resolution(w, h)
    except (TypeError, ValueError, L.LayoutError, OverflowError):
        return None
    return (w, h) if max(w, h) <= MAX_ASPECT * min(w, h) else None


def fits(scale, w, h):
    """True when a wheel of this Steam size is no bigger, against the short side of w x h, than
    the 4K wheel is against 2160 (the size known to fit), or it is already at the readable floor."""
    return scale <= L.MIN_WHEEL_SCALE or scale / min(w, h) <= L.WHEEL_SCALE_AT_4K / L.REFERENCE_HEIGHT + 0.001


class Follower:
    """Feed it samples; it says when the wheel must change and to which game size."""

    def __init__(self, applied=None, settle=SETTLE):
        self.settle = max(1, settle)
        self.size = applied                       # the size the wheel files were last written for
        self.scale = L.wheel_scale(*applied) if applied else L.WHEEL_SCALE_AT_4K
        self._cand, self._n = None, 0

    def feed(self, sample):
        """A (w, h) to write the wheel for, or None for nothing to do."""
        s = sanitize(sample)
        if s is None:
            return None               # junk: keep the streak and the last good size
        if s != self._cand:
            self._cand, self._n = s, 0
        self._n += 1
        if self._n < self.settle:
            return None
        scale = L.wheel_scale(*s)
        if scale == self.scale:
            self.size = s
            return None
        self.size, self.scale = s, scale
        return s


def follow(read, apply, settle=SETTLE, interval=1.0, sleep=time.sleep, applied=None, limit=None, say=print):
    """Poll read() (see platforms.game_size) and call apply((w, h)) when the size settles.
    apply failing (Steam busy, folder read-only) is reported and retried at the next change.
    limit: stop after that many polls (tests). Returns the list of sizes applied."""
    f, done, n = Follower(applied, settle), [], 0
    while limit is None or n < limit:
        n += 1
        try:
            sample = read()
        except Exception:  # noqa: BLE001
            sample = None
        size = f.feed(sample)
        if size:
            try:
                apply(size)
                done.append(size)
                say(f"Game picture {size[0]}x{size[1]}: wheel size {L.wheel_scale(*size)} written.")
            except (OSError, SystemExit) as e:
                f.scale = None        # not written: try again when the size next settles
                f._cand, f._n = None, 0
                say(f"Could not resize the wheel for {size[0]}x{size[1]}: {e}")
        if limit is None or n < limit:
            sleep(interval)
    return done
