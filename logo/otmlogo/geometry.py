"""Vector geometry for the OTM wordmark and compact mark.

Every measurement here is the approved value of record (see the design
system's assets/Logos/SPEC.md). Output is deterministic: the same font file and
the same arguments always produce byte-identical SVG text.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pathops
import uharfbuzz as hb
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

# Palette — Brand page Color System (source of record).
OFF, ORA, BLU, BG = "#E8E6DC", "#E8610A", "#5C92B9", "#0F1117"
WHITE, BLACK = "#FFFFFF", "#000000"

# Oxanium ExtraBold (latin, 800), @fontsource/oxanium 5.3.0.
FONT_SHA256 = "acb6db05b7b56c2d3b081f3cc1b2844ddadedd523fb1df921680372c685c52e0"

# Optical compensation for dark letters on light grounds, in font units for the
# compact mark (S=300 -> 0.3 scale) and in px for the wordmark (S=200).
COMP_UNITS = 15
COMP_WORDMARK_PX = 3

UNION, INTERSECT, DIFF = pathops.PathOp.UNION, pathops.PathOp.INTERSECTION, pathops.PathOp.DIFFERENCE


class FontHashError(ValueError):
    """The font file is not the pinned Oxanium ExtraBold build."""


class Font:
    def __init__(self, path: str | Path):
        data = Path(path).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != FONT_SHA256:
            raise FontHashError(
                f"font {path} has sha256 {digest}; expected {FONT_SHA256} "
                "(@fontsource/oxanium 5.3.0, oxanium-latin-800-normal.woff2)")
        self.f = TTFont(io.BytesIO(data))
        self.gs = self.f.getGlyphSet()
        self.upm = self.f["head"].unitsPerEm
        self.cmap = self.f.getBestCmap()
        buf = io.BytesIO()
        self.f.flavor = None
        self.f.save(buf)
        self.hbf = hb.Font(hb.Face(buf.getvalue()))

    def glyph(self, ch):
        return self.gs[self.cmap[ord(ch)]]

    def path(self, ch, dx=0):
        p = pathops.Path()
        pen = p.getPen(glyphSet=self.gs)
        self.glyph(ch).draw(TransformPen(pen, (1, 0, 0, 1, dx, 0)))
        return pathops.simplify(p, clockwise=True)

    @property
    def cap(self):
        c = getattr(self.f["OS/2"], "sCapHeight", 0)
        return c or self.path("H").bounds[3]


def rect(x0, y0, x1, y1):
    p = pathops.Path()
    p.moveTo(x0, y0); p.lineTo(x1, y0); p.lineTo(x1, y1); p.lineTo(x0, y1); p.close()
    return p


def op(a, b, o):
    return pathops.op(a, b, o)


def d(p):
    pen = SVGPathPen(None)
    p.draw(pen)
    return pen.getCommands()


def outer(fn: Font, ch):
    """The largest contour of a glyph (the O's outside edge)."""
    rp = RecordingPen()
    fn.glyph(ch).draw(rp)
    contours, cur = [], []
    for o, a in rp.value:
        cur.append((o, a))
        if o in ("closePath", "endPath"):
            contours.append(cur); cur = []
    best, bb = None, -1
    for c in contours:
        p = pathops.Path(); pen = p.getPen(glyphSet=fn.gs)
        for o, a in c:
            getattr(pen, o)(*a)
        b = p.bounds; area = (b[2] - b[0]) * (b[3] - b[1])
        if area > bb:
            bb = area; best = p
    return pathops.simplify(best)


def grow(p, k):
    q = pathops.Path(); p.draw(q.getPen())
    q.stroke(2 * k, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4)
    q.convertConicsToQuads()
    return op(q, p, UNION)


def compact(fn: Font, S, ink=OFF, accent=ORA, foot=BLU, blue=True, k_units=None, comp=None):
    """The OTM compact mark at size S (font size in px).

    Returns (place, width, height); place(x, y) yields the SVG group with the
    mark's top-left at (x, y). comp adds a stroke of that many font units to
    the ink letters (optical compensation on light grounds).
    """
    cap = fn.cap
    k = 0.035 * fn.upm if k_units is None else k_units
    Opath = fn.path("O"); ob = Opath.bounds
    Tg = fn.path("T"); tb = Tg.bounds
    band = op(Tg, rect(tb[0], 0, tb[0] + (tb[2] - tb[0]) * 0.05, tb[3] + 10), INTERSECT).bounds
    bar_bot, bar_top = band[1], tb[3]
    stem = op(Tg, rect(tb[0] - 10, cap * 0.25, tb[2] + 10, cap * 0.3), INTERSECT).bounds
    G = 0.135 * cap
    xT = ob[2] + G - stem[0]; T = fn.path("T", xT); stem_r = stem[2] + xT
    mb0 = fn.path("M").bounds; xM = stem_r + G - mb0[0]; M = fn.path("M", xM); mb = M.bounds
    mid = (mb[0] + mb[2]) / 2
    leftM = op(M, rect(mb[0] - 5, bar_bot, mid, bar_top + 50), INTERSECT)
    orange = op(T, op(rect((ob[0] + ob[2]) / 2, bar_bot, mb[0] + 1, bar_top), leftM, UNION), UNION)
    Mcut = op(M, rect(mb[0] - 5, bar_bot - k, mid, bar_top + 50), DIFF)
    orange = op(orange, grow(outer(fn, "O"), k), DIFF)
    xmin, xmax = ob[0], mb[2]
    g0 = 0.11 * cap; headh = 0.09 * cap; gaph = 0.07 * cap; footh = 0.06 * cap
    parts = [(Opath, ink, comp), (Mcut, ink, comp), (orange, accent, None),
             (rect(xmin, -g0 - headh, xmax, -g0), accent, None)]
    Hu = cap + g0 + headh
    if blue:
        parts.append((rect(xmin, -g0 - headh - gaph - footh, xmax, -g0 - headh - gaph), foot, None))
        Hu += gaph + footh
    sc = S / fn.upm

    def paint(c, cw):
        s = f' stroke="{c}" stroke-width="{cw}" stroke-linejoin="miter"' if cw else ""
        return f'fill="{c}"{s}'

    def place(x, y):
        tr = f'translate({x - xmin*sc:.3f} {y+cap*sc:.3f}) scale({sc:.6f} {-sc:.6f})'
        return f'<g transform="{tr}">' + "".join(
            f'<path d="{d(p)}" {paint(c, cw)}/>' for p, c, cw in parts) + '</g>'
    return place, (xmax - xmin) * sc, Hu * sc


def wordmark(fn: Font, S=200, ink=OFF, accent=ORA, foot=BLU, track=-0.025, gap=0.006, comp=None):
    """The ONE·TRACK·MIND wordmark. Returns (svg body, width, height)."""
    cap = fn.cap * S / fn.upm; pad = cap * 0.5; base = pad + cap

    def text(s, size, x0, b, tr):
        buf = hb.Buffer(); buf.add_str(s); buf.guess_segment_properties()
        hb.shape(fn.hbf, buf, {"kern": True})
        sc = size / fn.upm; x = x0; out = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
            pen = SVGPathPen(fn.gs)
            fn.gs[fn.f.getGlyphName(info.codepoint)].draw(TransformPen(pen, (sc, 0, 0, -sc, x, b)))
            out.append(pen.getCommands()); x += pos.x_advance * sc + tr * size
        return " ".join(out), x - tr * size - x0

    one, w1 = text("ONE", S, pad, base, track)
    footh, gaph, headh, tgap = 0.045 * cap, 0.06 * cap, 0.075 * cap, 0.075 * cap
    ts = 0.62 * cap / (fn.cap / fn.upm); gx = gap * S
    _, tw = text("TRACK", ts, 0, 0, track * 0.5); rp = 0.012 * S; xt = pad + w1 + gx
    tb = base - (footh + gaph + headh + tgap)
    trk, _ = text("TRACK", ts, xt + rp, tb, track * 0.5); rw = tw + 2 * rp
    xm = xt + rw + gx; mind, wm = text("MIND", S, xm, base, track)
    s = f' stroke="{ink}" stroke-width="{comp}" stroke-linejoin="miter"' if comp else ""
    body = (f'<path d="{one}" fill="{ink}"{s}/><path d="{trk}" fill="{accent}"/>'
            f'<rect x="{xt:.2f}" y="{base-footh-gaph-headh:.2f}" width="{rw:.2f}" height="{headh:.2f}" fill="{accent}"/>'
            f'<rect x="{xt:.2f}" y="{base-footh:.2f}" width="{rw:.2f}" height="{footh:.2f}" fill="{foot}"/>'
            f'<path d="{mind}" fill="{ink}"{s}/>')
    return body, xm + wm + pad, base + pad


def svg(w, h, body, bg=None, title="OneTrackMind"):
    r = f'<rect width="{w:.2f}" height="{h:.2f}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}" '
            f'width="{w:.2f}" height="{h:.2f}" role="img" aria-label="{title}">'
            f'<title>{title}</title>{r}{body}</svg>\n')
