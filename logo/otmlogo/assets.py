"""Every published logo file, by its name in the design system's Logos group."""
from __future__ import annotations

import json
import re

from .geometry import (BG, BLU, COMP_UNITS, COMP_WORDMARK_PX, ORA, OFF, WHITE, BLACK,
                       Font, compact, svg, wordmark)

# Sentinel colours let parts be found again after generation.
SI, SA, SF = "#010101", "#020202", "#030303"


def _paint(body, ink, acc, foot, comp=None):
    s = f' stroke="{ink}" stroke-width="{comp}" stroke-linejoin="miter"' if comp else ""
    body = body.replace(f'fill="{SI}"', f'fill="{ink}"{s}')
    return body.replace(f'fill="{SA}"', f'fill="{acc}"').replace(f'fill="{SF}"', f'fill="{foot}"')


def _keep_only(body, colour):
    for c in (SI, SA, SF):
        if c != colour:
            body = re.sub(rf'<(path|rect)[^>]*fill="{c}"[^>]*/>', "", body)
    return body


def build_svgs(fn: Font) -> tuple[dict[str, str], dict[str, str]]:
    """Return (published SVGs by design-system name, intermediate SVGs)."""
    out, extra = {}, {}
    # Core wordmark
    b, w, h = wordmark(fn)
    out["otm-wordmark.svg"] = svg(w, h, b)
    extra["otm-wordmark-on-dark.svg"] = svg(w, h, b, BG)
    b, w, h = wordmark(fn, ink=BG, comp=COMP_WORDMARK_PX)
    out["otm-wordmark-on-light.svg"] = svg(w, h, b, WHITE)
    # Core compact mark
    place, W, H = compact(fn, 300); pad = 0.35 * fn.cap * 300 / fn.upm
    out["otm-compact.svg"] = svg(W + 2 * pad, H + 2 * pad, place(pad, pad))
    extra["otm-compact-on-dark.svg"] = svg(W + 2 * pad, H + 2 * pad, place(pad, pad), BG)
    place, W, H = compact(fn, 300, ink=BG, comp=COMP_UNITS)
    out["otm-compact-on-light.svg"] = svg(W + 2 * pad, H + 2 * pad, place(pad, pad), WHITE)
    # App icon: full-bleed 1024, mark at 62% width
    _, W0, _ = compact(fn, 100); S = 100 * 1024 * 0.62 / W0; place, W, H = compact(fn, S)
    out["otm-app-icon.svg"] = svg(1024, 1024, place((1024 - W) / 2, (1024 - H) / 2), BG)
    # Favicons: pixel-snapped placement, keyline at least 1px
    for N, blue, frac in [(48, True, 0.88), (32, True, 0.88), (16, False, 0.94)]:
        _, W0, _ = compact(fn, 100, blue=blue); S = 100 * N * frac / W0; sc = S / fn.upm
        place, W, H = compact(fn, S, blue=blue, k_units=max(1.0 / sc, 0.035 * fn.upm))
        out[f"otm-favicon-{N}.svg"] = svg(N, N, place(round((N - W) / 2), round((N - H) / 2)), BG)
    # iOS: Icon Composer layers on the app icon's placement
    _, W0, _ = compact(fn, 100); S = 100 * 1024 * 0.62 / W0
    place, W, H = compact(fn, S, ink=SI, accent=SA, foot=SF)
    mark = place((1024 - W) / 2, (1024 - H) / 2)
    for name, sent in [("1-letters", SI), ("2-accent", SA), ("3-rail", SF)]:
        out[f"otm-icon-layer-{name}.svg"] = svg(
            1024, 1024, _paint(_keep_only(mark, sent), OFF, ORA, BLU), title=f"OTM icon layer {name}")
    out["otm-icon-mono-reference.svg"] = svg(1024, 1024, _paint(mark, WHITE, WHITE, WHITE), BLACK,
                                             "OTM icon mono reference")
    out["otm-icon-flat.svg"] = svg(1024, 1024, _paint(mark, OFF, ORA, BLU), BG)
    # Web tab icon: letters follow the browser theme
    _, Wc, Hc = compact(fn, 100); side = max(Wc, Hc) * 1.06; S = 100 * 512 / side
    place, W, H = compact(fn, S, ink=SI, accent=SA, foot=SF)
    body = place((512 - W) / 2, (512 - H) / 2)
    body = (body.replace(f'fill="{SI}"', 'class="ink"').replace(f'fill="{SA}"', f'fill="{ORA}"')
            .replace(f'fill="{SF}"', f'fill="{BLU}"'))
    style = (f'<style>.ink{{fill:{BG};stroke:{BG};stroke-width:{COMP_UNITS};stroke-linejoin:miter}}'
             f'@media (prefers-color-scheme: dark){{.ink{{fill:{OFF};stroke:none}}}}</style>')
    out["otm-web-icon.svg"] = svg(512, 512, style + body)
    # One-colour
    place, W, H = compact(fn, 300, ink=SI, accent=SA, foot=SF); pad = 0.35 * fn.cap * 300 / fn.upm
    cb = place(pad, pad); cw, ch = W + 2 * pad, H + 2 * pad
    wb, ww, wh = wordmark(fn, ink=SI, accent=SA, foot=SF)
    for tone, col, cc, cwp in [("black", BLACK, COMP_UNITS, COMP_WORDMARK_PX), ("white", WHITE, None, None)]:
        out[f"otm-compact-{tone}.svg"] = svg(cw, ch, _paint(cb, col, col, col, cc))
        out[f"otm-wordmark-{tone}.svg"] = svg(ww, wh, _paint(wb, col, col, col, cwp))
    # Android notification sources at 72/96 (24/36/48 are pixel drawings)
    for N in (72, 96):
        live = N * 20 / 24; _, W0, _ = compact(fn, 100); S = 100 * live / W0
        place, W, H = compact(fn, S, ink=WHITE, accent=WHITE, foot=WHITE)
        out[f"otm-android-notif-{N}.svg"] = svg(N, N, place((N - W) / 2, (N - H) / 2))
    return out, extra


def render_jobs() -> list[dict]:
    """SVG -> PNG renders. src may be a published or an intermediate SVG."""
    J = []
    def job(src, out, w, h, transparent=False, opaque=False):
        J.append(dict(src=src, out=out, width=w, height=h, transparent=transparent, opaque=opaque))
    job("otm-app-icon.svg", "otm-app-icon-1024.png", 1024, 1024)
    job("otm-favicon-32.svg", "otm-favicon-32.png", 32, 32)
    job("otm-favicon-16.svg", "otm-favicon-16.png", 16, 16)
    job("otm-icon-flat.svg", "otm-icon-flat-1024.png", 1024, 1024, opaque=True)
    for out, s in [("otm-web-apple-touch-icon.png", 180), ("otm-web-icon-192.png", 192),
                   ("otm-web-icon-512.png", 512), ("otm-web-icon-mask.png", 512)]:
        job("otm-app-icon.svg", out, s, s, opaque=True)
    for n in (16, 32, 48):
        job(f"otm-favicon-{n}.svg", f"_ico/fav{n}.png", n, n)
    return J


def export_jobs(aspect: dict[str, float]) -> list[dict]:
    J = []
    for m, w1 in [("wordmark", 400), ("compact", 120)]:
        for g in ("on-dark", "on-light"):
            for x in (1, 2, 3):
                src = f"otm-{m}-{g}.svg"; w = w1 * x
                J.append(dict(src=src, out=f"otm-{m}-{g}@{x}x.png", width=w,
                              height=round(w * aspect[src]), transparent=False, opaque=False))
    for m, w in [("wordmark", 800), ("compact", 240)]:
        for t in ("black", "white"):
            src = f"otm-{m}-{t}.svg"
            J.append(dict(src=src, out=f"otm-{m}-{t}@2x.png", width=w,
                          height=round(w * aspect[src]), transparent=True, opaque=False))
    for n in (72, 96):
        J.append(dict(src=f"otm-android-notif-{n}.svg", out=f"otm-android-notif-{n}.png",
                      width=n, height=n, transparent=True, opaque=False))
    return J


def manifest_json() -> str:
    m = {"name": "OneTrackMind", "short_name": "OTM", "display": "standalone",
         "background_color": BG, "theme_color": BG, "start_url": "/",
         "icons": [{"src": "/icon-192.png", "type": "image/png", "sizes": "192x192"},
                   {"src": "/icon-512.png", "type": "image/png", "sizes": "512x512"},
                   {"src": "/icon-mask.png", "type": "image/png", "sizes": "512x512", "purpose": "maskable"}]}
    return json.dumps(m, indent=2) + "\n"


HEAD_SNIPPET = ('<link rel="icon" href="/favicon.ico" sizes="32x32">\n'
                '<link rel="icon" href="/icon.svg" type="image/svg+xml">\n'
                '<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
                '<link rel="manifest" href="/manifest.webmanifest">\n'
                f'<meta name="theme-color" content="{BG}">\n')
