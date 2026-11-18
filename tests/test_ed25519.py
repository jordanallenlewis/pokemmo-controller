"""The signature code, against the test vectors in RFC 8032 section 7.1."""
import unittest

import helpers  # noqa: F401  (puts tools/ on the path)
import ed25519

VECTORS = [  # (seed, public key, message, signature)
    ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
     "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
     "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
     "fc51cd8e6218a0a6a9d8e0e7d0b8e3c0b6c7d6f1f3d1c8a1b9e8f8a0d5d1d1a9", "af82", None),
]


class Ed25519(unittest.TestCase):
    def test_rfc_vectors(self):
        for seed, pub, msg, sig in VECTORS[:2]:
            seed, pub, msg, sig = (bytes.fromhex(x) for x in (seed, pub, msg, sig))
            self.assertEqual(ed25519.public_key(seed), pub)
            self.assertEqual(ed25519.sign(seed, msg), sig)
            self.assertTrue(ed25519.verify(pub, msg, sig))

    def test_a_changed_message_key_or_signature_fails(self):
        seed, pub, msg, sig = (bytes.fromhex(x) for x in VECTORS[1])
        self.assertFalse(ed25519.verify(pub, msg + b"x", sig))
        self.assertFalse(ed25519.verify(pub, b"", sig))
        other = ed25519.public_key(bytes(32))
        self.assertFalse(ed25519.verify(other, msg, sig))
        for i in (0, 31, 32, 63):
            bad = bytearray(sig)
            bad[i] ^= 1
            self.assertFalse(ed25519.verify(pub, msg, bytes(bad)), i)

    def test_garbage_is_false_not_an_error(self):
        pub = bytes.fromhex(VECTORS[0][1])
        for sig in (b"", b"x" * 63, b"\xff" * 64, b"\x00" * 64):
            self.assertFalse(ed25519.verify(pub, b"m", sig))
        self.assertFalse(ed25519.verify(b"\xff" * 32, b"m", b"\x00" * 64))
        self.assertFalse(ed25519.verify(b"short", b"m", b"\x00" * 64))
