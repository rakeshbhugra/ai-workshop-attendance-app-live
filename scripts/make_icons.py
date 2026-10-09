"""Write the placeholder PWA icons (stdlib only). Replace them with real art.

    python scripts/make_icons.py
"""

import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public"
BG, FG = (15, 23, 42), (248, 250, 252)  # slate-900, slate-50


def png(size: int) -> bytes:
    # A light square in the middle 40%, inside the maskable safe zone.
    lo, hi = int(size * 0.3), int(size * 0.7)
    rows = b"".join(
        b"\x00" + b"".join(bytes(FG if lo <= x < hi and lo <= y < hi else BG) for x in range(size))
        for y in range(size)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    for size, name in [(192, "pwa-192.png"), (512, "pwa-512.png"), (180, "apple-touch-icon.png")]:
        (OUT / name).write_bytes(png(size))
        print("wrote", OUT / name)
