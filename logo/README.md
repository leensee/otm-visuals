# OTM logo build

Regenerates the full OneTrackMind logo set — the 49 files in the design system's
**Logos** asset group plus `otm-web-favicon.ico` — from the Oxanium ExtraBold
outlines. Output file names match the design system one to one.

The measurements of record (typeface, tracking, word gap, TRACK size, rail
proportions, keyline, optical compensation, app-icon safe zone, favicon and
notification-icon rules) are written up in the design system at
`assets/Logos/SPEC.md`. That spec is the acceptance test; this directory is the
implementation.

## Setup

```sh
cd logo
python3 -m pip install -r requirements.txt
npm ci                      # Playwright + @fontsource/oxanium (the font is not committed)
npx playwright install chromium   # or set CHROMIUM_PATH to an existing Chromium
```

## Build

```sh
python3 build.py --out out/
```

- `out/` — the published set, named as in the design system.
- `out/_extra/` — intermediates (`otm-wordmark-on-dark.svg`, `otm-compact-on-dark.svg`),
  `manifest.webmanifest`, `head-snippet.html`, and the render job list.

The build refuses a non-empty output folder unless `--force` is given, refuses any
font other than the pinned `oxanium-latin-800-normal.woff2` (checked by SHA-256),
and stops with a non-zero exit at the first failed step.

## Verify against the published set

Download the Logos group from the design system into a folder, then:

```sh
python3 verify.py out/ path/to/published/
```

SVGs are compared as parsed XML (the design system's asset store re-serializes
markup without changing content); PNGs pixel for pixel; `.ico` entry by entry.
Missing or extra files fail. On 2026-10-19 the build matched all 50 published
files.

## Tests

```sh
python3 -m pytest -q tests
```

Covers the pixel designs (fit, two separate rails, malformed input), font
pinning, deterministic SVG output, the published file list, and — when Node and
Chromium are available — a full build with the no-alpha checks on the iOS and web
icons.

## Layout

| Path | What it does |
|---|---|
| `otmlogo/geometry.py` | Font loading (hash-pinned), compact mark, wordmark, SVG wrapper |
| `otmlogo/pixel.py` | Hand-hinted 24/36/48 px Android notification icons, as editable text grids |
| `otmlogo/assets.py` | Every published SVG, and the PNG render job list |
| `build.py` | Runs SVG → pixel icons → `render.mjs` → finishing (no-alpha icons, `favicon.ico`, maskable check) |
| `render.mjs` | SVG → PNG with Playwright's Chromium |
| `verify.py` | Compares a build with the published set |

## Android notification icons

Ship `otm-android-notif-{24,36,48,72,96}.png` as `drawable-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_stat_otm.png`.
Do not replace them with a single vector drawable — Android would rescale the
vector at mdpi–xhdpi and lose the pixel hinting that keeps the keyline and both
rails visible at 24 px.
