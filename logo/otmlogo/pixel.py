"""Hand-hinted pixel drawings of the OTM mark for Android notification icons.

At 24/36/48 px the vector mark, scaled down, loses its keyline and merges its
rails. These grids keep the vector's proportions (letters 2.45 cap wide,
strokes 0.25 cap, crossbar 0.23 cap, M notch to mid-height with two bottom
counters) with every edge on a whole pixel. White on transparent.
"""
from __future__ import annotations

M_ART = {
    24: ["###...###",
         "####.####",
         "####.####",
         "#########",
         "#########",
         "##.###.##",
         "##..#..##",
         "##..#..##"],
    36: ["####.....####",
         "#####...#####",
         "#####...#####",
         "######.######",
         "######.######",
         "#############",
         "#############",
         "#############",
         "###.#####.###",
         "###..###..###",
         "###..###..###",
         "###..###..###"],
    48: ["######......######",
         "######......######",
         "#######....#######",
         "#######....#######",
         "########..########",
         "########..########",
         "##################",
         "##################",
         "##################",
         "##################",
         "##################",
         "####.########.####",
         "####...####...####",
         "####...####...####",
         "####...####...####",
         "####...####...####"],
}

# cap: letter height; s: stroke; Ow: O width; cut: corner step; kl: keyline;
# stem/sw: T stem x and width; Mx: M x; bar: crossbar rows; g0/head/gap/foot: rails.
SPEC = {
    24: dict(cap=8, s=2, Ow=7, cut=1, kl=1, stem=8, sw=2, Mx=11, bar=2, g0=1, head=1, gap=1, foot=1),
    36: dict(cap=12, s=3, Ow=10, cut=1, kl=1, stem=12, sw=3, Mx=17, bar=3, g0=1, head=1, gap=1, foot=1),
    48: dict(cap=16, s=4, Ow=14, cut=2, kl=1, stem=16, sw=4, Mx=22, bar=4, g0=2, head=2, gap=1, foot=1),
}

SIZES = tuple(sorted(SPEC))


class GridError(ValueError):
    """A pixel design is malformed or falls outside its canvas."""


def build(N: int) -> list[list[int]]:
    """Return the N×N grid (1 = white pixel)."""
    if N not in SPEC:
        raise GridError(f"no pixel design for {N}px; have {SIZES}")
    p = SPEC[N]; art = M_ART[N]
    Mw = len(art[0])
    if any(len(r) != Mw for r in art) or len(art) != p["cap"]:
        raise GridError(f"{N}px M art must be {p['cap']} rows of equal width")
    if any(set(r) - {"#", "."} for r in art):
        raise GridError(f"{N}px M art may contain only '#' and '.'")
    W = p["Mx"] + Mw
    H = p["cap"] + p["g0"] + p["head"] + p["gap"] + p["foot"]
    pad = N // 12  # Android 24dp icon: 2dp padding per side
    if W > N - 2 * pad or H > N - 2 * pad:
        raise GridError(f"{N}px design {W}x{H} exceeds live area {N-2*pad}")
    ox = (N - W) // 2; oy = (N - H) // 2
    g = [[0] * N for _ in range(N)]

    def px(r, c):
        g[oy + r][ox + c] = 1

    cap, s, Ow, cut = p["cap"], p["s"], p["Ow"], p["cut"]
    for r in range(cap):  # O with stepped corners
        for c in range(Ow):
            inner = s <= r < cap - s and s <= c < Ow - s
            dr = min(r, cap - 1 - r); dc = min(c, Ow - 1 - c)
            if not inner and dr + dc >= cut:
                px(r, c)
    for r in range(p["bar"]):  # crossbar: after the keyline, into the M
        for c in range(Ow + p["kl"], p["Mx"]):
            px(r, c)
    for r in range(cap):  # T stem
        for c in range(p["stem"], p["stem"] + p["sw"]):
            px(r, c)
    for r, row in enumerate(art):  # M
        for c, ch in enumerate(row):
            if ch == "#":
                px(r, p["Mx"] + c)
    y = cap + p["g0"]
    for r in range(p["head"]):
        for c in range(W):
            px(y + r, c)
    y += p["head"] + p["gap"]
    for r in range(p["foot"]):
        for c in range(W):
            px(y + r, c)
    return g


def to_png(g, path):
    from PIL import Image
    N = len(g)
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    for r in range(N):
        for c in range(N):
            if g[r][c]:
                im.putpixel((c, r), (255, 255, 255, 255))
    im.save(path)
