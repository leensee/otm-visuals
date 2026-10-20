#!/usr/bin/env python3
"""Build every OTM logo file.

    python build.py --out out/            # font from node_modules (npm ci)
    python build.py --font path/to.woff2 --out out/

Writes the published set (names match the design system's Logos group) to
<out>/, and intermediates plus the web manifest and <head> snippet to
<out>/_extra/. Stops with a non-zero exit at the first failure.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image

from otmlogo import assets, pixel
from otmlogo.geometry import Font, FontHashError, compact

HERE = Path(__file__).resolve().parent
DEFAULT_FONT = HERE / "node_modules/@fontsource/oxanium/files/oxanium-latin-800-normal.woff2"


def fail(step, msg):
    print(f"build failed at {step}: {msg}", file=sys.stderr)
    sys.exit(1)


def aspect_of(svg_text):
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg_text)
    return float(m.group(2)) / float(m.group(1))


def write_ico(pngs: dict[int, bytes], path: Path):
    """ICO with PNG-encoded entries, smallest first."""
    sizes = sorted(pngs)
    hdr = struct.pack("<HHH", 0, 1, len(sizes)); off = 6 + 16 * len(sizes); ent = b""
    for n in sizes:
        ent += struct.pack("<BBBBHHII", n, n, 0, 0, 1, 32, len(pngs[n]), off); off += len(pngs[n])
    path.write_bytes(hdr + ent + b"".join(pngs[n] for n in sizes))


def maskable_ok(fn) -> tuple[float, float]:
    _, W0, _ = compact(fn, 100); S = 100 * 1024 * 0.62 / W0
    _, W, H = compact(fn, S)
    return (W ** 2 + H ** 2) ** 0.5, 0.8 * 1024


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font", type=Path, default=DEFAULT_FONT)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--force", action="store_true", help="allow writing into a non-empty directory")
    a = ap.parse_args(argv)

    out = a.out.resolve(); extra = out / "_extra"
    if out.exists() and any(out.iterdir()) and not a.force:
        fail("setup", f"{out} is not empty (use --force)")
    if not a.font.is_file():
        fail("setup", f"font not found: {a.font} (run `npm ci` in logo/ or pass --font)")
    try:
        fn = Font(a.font)
    except FontHashError as e:
        fail("font", str(e))

    out.mkdir(parents=True, exist_ok=True); extra.mkdir(exist_ok=True)

    print("1/4 svg")
    published, inter = assets.build_svgs(fn)
    for name, text in published.items():
        (out / name).write_text(text)
    for name, text in inter.items():
        (extra / name).write_text(text)
    (extra / "manifest.webmanifest").write_text(assets.manifest_json())
    (extra / "head-snippet.html").write_text(assets.HEAD_SNIPPET)

    print("2/4 pixel icons")
    for n in pixel.SIZES:
        pixel.to_png(pixel.build(n), out / f"otm-android-notif-{n}.png")

    print("3/4 render")
    allsvg = {**published, **inter}
    jobs = assets.render_jobs() + assets.export_jobs({k: aspect_of(v) for k, v in allsvg.items()})
    svgdir = extra / "_svg"; svgdir.mkdir(exist_ok=True)
    for name, text in allsvg.items():
        (svgdir / name).write_text(text)
    jobs_path = extra / "render-jobs.json"; jobs_path.write_text(json.dumps(jobs, indent=1))
    r = subprocess.run(["node", str(HERE / "render.mjs"), str(jobs_path), str(svgdir), str(out)])
    if r.returncode != 0:
        fail("render", f"render.mjs exited {r.returncode}")
    shutil.rmtree(svgdir)

    print("4/4 finish")
    for j in jobs:
        if j["opaque"]:
            p = out / j["out"]; Image.open(p).convert("RGB").save(p, optimize=True)
    ico = out / "_ico"
    write_ico({n: (ico / f"fav{n}.png").read_bytes() for n in (16, 32, 48)}, out / "otm-web-favicon.ico")
    shutil.rmtree(ico)
    diag, circle = maskable_ok(fn)
    if diag > circle:
        fail("finish", f"maskable icon: mark diagonal {diag:.0f}px exceeds safe circle {circle:.0f}px")
    n = len([p for p in out.iterdir() if p.is_file()])
    print(f"done: {n} files in {out} (maskable {diag:.0f}/{circle:.0f}px)")


if __name__ == "__main__":
    main()
