"""Ed25519 signatures (RFC 8032) in plain Python, so updates can be checked on any
computer with nothing installed. Slow (tens of milliseconds) and not hardened
against timing attacks: it is only used to verify a public signature on a
release file, and to sign one in the release workflow, where the key never
leaves the runner. The RFC's test vectors are in tests/test_ed25519.py.
"""
import hashlib

_P = 2 ** 255 - 19
_Q = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _inv(x):
    return pow(x, _P - 2, _P)


def _x_from_y(y, sign):
    xx = (y * y - 1) * _inv(_D * y * y + 1) % _P
    x = pow(xx, (_P + 3) // 8, _P)
    if (x * x - xx) % _P:
        x = x * _I % _P
    if (x * x - xx) % _P:
        raise ValueError("not a point")
    if x & 1 != sign:
        x = _P - x
    return x


_BY = 4 * _inv(5) % _P
_B = (_x_from_y(_BY, 0), _BY, 1, _x_from_y(_BY, 0) * _BY % _P)
_ZERO = (0, 1, 1, 0)


def _add(a, b):
    A, B = (a[1] - a[0]) * (b[1] - b[0]) % _P, (a[1] + a[0]) * (b[1] + b[0]) % _P
    C, D = 2 * a[3] * b[3] * _D % _P, 2 * a[2] * b[2] % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _mul(s, pt):
    r = _ZERO
    while s:
        if s & 1:
            r = _add(r, pt)
        pt = _add(pt, pt)
        s >>= 1
    return r


def _eq(a, b):
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _enc(pt):
    zi = _inv(pt[2])
    x, y = pt[0] * zi % _P, pt[1] * zi % _P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _dec(s):
    if len(s) != 32:
        raise ValueError("bad length")
    y = int.from_bytes(s, "little")
    sign, y = y >> 255, y & ((1 << 255) - 1)
    if y >= _P:
        raise ValueError("not a point")
    x = _x_from_y(y, sign)
    return (x, y, 1, x * y % _P)


def _h(m):
    return int.from_bytes(hashlib.sha512(m).digest(), "little")


def _expand(seed):
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(seed: bytes) -> bytes:
    """The 32-byte public key for a 32-byte secret seed."""
    return _enc(_mul(_expand(seed)[0], _B))


def sign(seed: bytes, msg: bytes) -> bytes:
    a, prefix = _expand(seed)
    pub = _enc(_mul(a, _B))
    r = _h(prefix + msg) % _Q
    R = _enc(_mul(r, _B))
    s = (r + _h(R + pub + msg) * a) % _Q
    return R + s.to_bytes(32, "little")


def verify(pub: bytes, msg: bytes, sig: bytes) -> bool:
    """True only for a valid signature; any malformed input is simply False."""
    try:
        if len(sig) != 64 or len(pub) != 32:
            return False
        A, R = _dec(pub), _dec(sig[:32])
        s = int.from_bytes(sig[32:], "little")
        if s >= _Q:
            return False
        k = _h(sig[:32] + pub + msg) % _Q
        return _eq(_mul(s, _B), _add(R, _mul(k, A)))
    except (ValueError, TypeError):
        return False
