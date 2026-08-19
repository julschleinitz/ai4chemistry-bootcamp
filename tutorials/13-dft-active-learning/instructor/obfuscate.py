"""
Label obfuscation for the pool.

WHAT THIS IS: an HMAC-SHA256 keystream XOR over the serialised label array,
using only the Python standard library. It stops a student from opening
`pool_labels.enc` in Excel and reading the answers.

WHAT THIS IS NOT: security. The key ships with the student toolkit, because the
oracle has to be able to decrypt. Anyone determined can recover the labels in
about ten lines of code.

That is deliberate and it should be said out loud in the tutorial:

    The budget is a rule, not a lock. We audit submissions
    (`score_submissions.py --audit`), and the interesting part of the exercise
    is the acquisition function, not the file format.

An identical copy of `keystream`, `seal` and `unseal` lives in
`student/al_toolkit.py` so that students need no instructor imports. If you
change one, change both -- `tests/test_roundtrip.py` checks they agree.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json

MAGIC = b"AL4CHEM1"


def keystream(key: bytes, n: int) -> bytes:
    """n bytes of HMAC-SHA256 counter-mode keystream."""
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:n])


def _xor(data: bytes, key: bytes) -> bytes:
    ks = keystream(key, len(data))
    return bytes(a ^ b for a, b in zip(data, ks))


def seal(payload: bytes, key: bytes) -> bytes:
    """MAGIC || sha256(payload)[:8] || xor(payload)."""
    digest = hashlib.sha256(payload).digest()[:8]
    return MAGIC + digest + _xor(payload, key)


def unseal(blob: bytes, key: bytes) -> bytes:
    if blob[: len(MAGIC)] != MAGIC:
        raise ValueError("not a sealed label file")
    digest = blob[len(MAGIC) : len(MAGIC) + 8]
    payload = _xor(blob[len(MAGIC) + 8 :], key)
    if hashlib.sha256(payload).digest()[:8] != digest:
        raise ValueError("sealed label file is corrupt or the key is wrong")
    return payload


def seal_labels(acid_ids: list[str], target_columns: list[str], values, key: bytes) -> bytes:
    """Serialise (ids, columns, float64 matrix) to a sealed blob."""
    import numpy as np

    buf = io.BytesIO()
    np.savez_compressed(
        buf,
        acid_ids=np.array(acid_ids, dtype=object),
        target_columns=np.array(target_columns, dtype=object),
        values=np.asarray(values, dtype=np.float64),
        meta=np.array([json.dumps({"n": len(acid_ids), "t": len(target_columns)})],
                      dtype=object),
    )
    return seal(buf.getvalue(), key)


def unseal_labels(blob: bytes, key: bytes):
    """Return (acid_ids list, target_columns list, values ndarray)."""
    import numpy as np

    with io.BytesIO(unseal(blob, key)) as buf:
        z = np.load(buf, allow_pickle=True)
        return (
            [str(v) for v in z["acid_ids"]],
            [str(v) for v in z["target_columns"]],
            z["values"],
        )
