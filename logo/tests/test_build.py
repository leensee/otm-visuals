"""Tests for the logo build. The render-dependent test needs `npm ci` and a
Chromium Playwright can launch (set CHROMIUM_PATH if it is not the default)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from otmlogo import assets, pixel  # noqa: E402
from otmlogo.geometry import Font, FontHashError  # noqa: E402
import build  # noqa: E402

FONT = build.DEFAULT_FONT
needs_font = pytest.mark.skipif(not FONT.is_file(), reason="run `npm ci` in logo/ first")


# --- pixel designs ---------------------------------------------------------

@pytest.mark.parametrize("n", pixel.SIZES)
def test_pixel_design_fits_live_area(n):
    g = pixel.build(n)
    pad = n // 12
    on = [(r, c) for r in range(n) for c in range(n) if g[r][c]]
    assert on, "empty design"
    assert min(r for r, _ in on) >= pad and max(r for r, _ in on) < n - pad
    assert min(c for _, c in on) >= pad and max(c for _, c in on) < n - pad


@pytest.mark.parametrize("n", pixel.SIZES)
def test_rails_are_separate(n):
    """Both rails exist and a clear row separates them — the failure the hinting fixes."""
    g = pixel.build(n)
    full = [r for r in range(n) if sum(g[r]) == max(sum(row) for row in g)]
    groups = [[full[0]]]
    for r in full[1:]:
        (groups[-1].append(r) if r == groups[-1][-1] + 1 else groups.append([r]))
    assert len(groups) == 2, f"expected two rails at {n}px, found {len(groups)}"


def test_malformed_art_is_rejected(monkeypatch):
    bad = dict(pixel.M_ART); bad[24] = pixel.M_ART[24][:-1]
    monkeypatch.setattr(pixel, "M_ART", bad)
    with pytest.raises(pixel.GridError):
        pixel.build(24)


def test_unknown_size_is_rejected():
    with pytest.raises(pixel.GridError):
        pixel.build(20)


# --- font pinning ----------------------------------------------------------

def test_wrong_font_is_rejected(tmp_path):
    f = tmp_path / "not-oxanium.woff2"; f.write_bytes(b"\x00" * 64)
    with pytest.raises(FontHashError):
        Font(f)


# --- determinism -----------------------------------------------------------

@needs_font
def test_svg_output_is_deterministic():
    a = assets.build_svgs(Font(FONT)); b = assets.build_svgs(Font(FONT))
    assert a == b


@needs_font
def test_published_names_are_complete():
    pub, _ = assets.build_svgs(Font(FONT))
    renders = {j["out"] for j in assets.render_jobs() if not j["out"].startswith("_")}
    exports = {j["out"] for j in assets.export_jobs({k: 1.0 for k in [*pub, "otm-wordmark-on-dark.svg",
               "otm-compact-on-dark.svg"]})}
    names = set(pub) | renders | exports | {f"otm-android-notif-{n}.png" for n in pixel.SIZES} | {"otm-web-favicon.ico"}
    assert len(names) == 50


# --- full build ------------------------------------------------------------

def _can_render():
    return FONT.is_file() and shutil.which("node") and (HERE / "node_modules/playwright").is_dir()


@pytest.mark.skipif(not _can_render(), reason="needs npm ci and node")
def test_full_build(tmp_path):
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(HERE / "build.py"), "--out", str(out)], cwd=HERE)
    assert r.returncode == 0
    files = [p for p in out.iterdir() if p.is_file()]
    assert len(files) == 50
    for name in ["otm-icon-flat-1024.png", "otm-web-apple-touch-icon.png", "otm-web-icon-192.png",
                 "otm-web-icon-512.png", "otm-web-icon-mask.png"]:
        assert Image.open(out / name).mode == "RGB", f"{name} must have no alpha channel"
    # a second build into a non-empty folder is refused without --force
    r2 = subprocess.run([sys.executable, str(HERE / "build.py"), "--out", str(out)], cwd=HERE)
    assert r2.returncode != 0
