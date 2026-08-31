"""
Pure-Python UUIDv7 (RFC 9562) -- the one function langsmith actually
imports from the real `uuid_utils` package (`from uuid_utils.compat
import uuid7`). See __init__.py for why this shim package exists at all.

This doesn't need to be blazing fast (that's the whole point of the real
compiled package) -- it's only ever used by langsmith internally to tag
trace/run objects with an ID, not by any of NOMAD's own code.
"""

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    # 48-bit big-endian Unix timestamp in milliseconds.
    unix_ts_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rand = os.urandom(10)

    b = bytearray(16)
    b[0:6] = unix_ts_ms.to_bytes(6, "big")
    b[6] = 0x70 | (rand[0] & 0x0F)  # version 7, high nibble of byte 6
    b[7] = rand[1]
    b[8] = 0x80 | (rand[2] & 0x3F)  # variant 10xxxxxx
    b[9:16] = rand[3:10]

    return uuid.UUID(bytes=bytes(b))
