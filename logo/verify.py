#!/usr/bin/env python3
"""Compare a build against the published Logos set.

    python verify.py <built dir> <reference dir>

SVG: compared as parsed XML (element, attributes, text), because the design
system's asset store re-serializes SVG markup (expands self-closing tags, drops
the trailing newline) without changing content. PNG: decoded and compared pixel
for pixel. ICO: each entry decoded and compared at each size. Missing or extra
files are failures. Exits non-zero with a list of differences.
"""
from __future__ import annotations

import io
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageChops


def svg_tree(p):
    def norm(e):
        return (e.tag, tuple(sorted(e.attrib.items())), (e.text or "").strip(),
                tuple(norm(c) for c in e))
    return norm(ET.parse(p).getroot())


def pixels(data_or_path):
    im = Image.open(io.BytesIO(data_or_path) if isinstance(data_or_path, bytes) else data_or_path)
    return im.convert("RGBA")


def same_pixels(a, b):
    if a.size != b.size:
        return f"size {a.size} vs {b.size}"
    diff = ImageChops.difference(a, b).getbbox()
    return None if diff is None else f"pixels differ in box {diff}"


def ico_entries(path):
    data = Path(path).read_bytes()
    _, _, n = struct.unpack("<HHH", data[:6]); out = {}
    for i in range(n):
        w, h, _, _, _, _, size, off = struct.unpack("<BBBBHHII", data[6 + 16 * i: 22 + 16 * i])
        out[w or 256] = pixels(data[off:off + size])
    return out


def compare(built: Path, ref: Path) -> list[str]:
    errs = []
    b = {p.name for p in built.iterdir() if p.is_file()}
    r = {p.name for p in ref.iterdir() if p.is_file()}
    errs += [f"missing: {n}" for n in sorted(r - b)]
    errs += [f"extra: {n}" for n in sorted(b - r)]
    for n in sorted(b & r):
        x, y = built / n, ref / n
        if n.endswith(".svg"):
            if svg_tree(x) != svg_tree(y):
                errs.append(f"{n}: SVG content differs")
        elif n.endswith(".png"):
            e = same_pixels(pixels(x), pixels(y))
            if e:
                errs.append(f"{n}: {e}")
        elif n.endswith(".ico"):
            ex, ey = ico_entries(x), ico_entries(y)
            if sorted(ex) != sorted(ey):
                errs.append(f"{n}: sizes {sorted(ex)} vs {sorted(ey)}")
            else:
                for s in ex:
                    e = same_pixels(ex[s], ey[s])
                    if e:
                        errs.append(f"{n} @{s}: {e}")
        elif x.read_bytes() != y.read_bytes():
            errs.append(f"{n}: bytes differ")
    return errs


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr); return 2
    built, ref = map(Path, argv)
    errs = compare(built, ref)
    n = len({p.name for p in ref.iterdir() if p.is_file()})
    if errs:
        print(f"{len(errs)} difference(s) against {n} reference files:")
        print("\n".join("  " + e for e in errs)); return 1
    print(f"OK: all {n} files match"); return 0


if __name__ == "__main__":
    sys.exit(main())
