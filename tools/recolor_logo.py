"""Recolor the user-provided chat-bubble logo to Triskell Studio brand colors.

Source : assets/logo_source.png  (gold bubble on navy background)
Target : indigo -> violet -> orange gradient on Triskell BG (#08080F)

Strategy:
  1. Detect the "gold" pixels (high red, high green, low blue) using HSV.
  2. Replace them with a vertical 3-stop gradient (indigo -> violet -> orange).
  3. Replace the dark navy background with the Triskell BG color.
  4. Keep white sparkles white.
  5. Save as PNG (multiple sizes) and ICO (multi-resolution).

Run: python tools/recolor_logo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image

SOURCE = ROOT / "assets" / "logo_source.png"
OUT_PNG = ROOT / "assets" / "logo.png"
OUT_ICO = ROOT / "assets" / "icon.ico"
OUT_LANDING = ROOT / "landing" / "public" / "img" / "icon.png"

INDIGO = (99, 102, 241)
VIOLET = (139, 92, 246)
ORANGE = (249, 115, 22)
BG = (8, 8, 15)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient_at(t: float):
    """3-stop linear gradient: indigo (0) -> violet (0.5) -> orange (1)."""
    if t <= 0.5:
        return lerp(INDIGO, VIOLET, t * 2)
    return lerp(VIOLET, ORANGE, (t - 0.5) * 2)


def recolor(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    pixels = img.load()
    out = Image.new("RGBA", (w, h))
    out_pixels = out.load()

    for y in range(h):
        # Vertical gradient position
        t = y / max(1, h - 1)
        grad = gradient_at(t)
        for x in range(w):
            r, g, b, a = pixels[x, y]

            # White / light pixels -> keep (sparkles + light text)
            if r > 220 and g > 220 and b > 220:
                out_pixels[x, y] = (r, g, b, a)
                continue

            # Background detection: low saturation, low value -> BG
            mx = max(r, g, b)
            mn = min(r, g, b)
            sat = (mx - mn) / mx if mx else 0
            if mx < 70 and sat < 0.3:
                out_pixels[x, y] = (*BG, 255)
                continue

            # Gold detection: warm hue (R > B), with significant saturation
            if r > b and (r + g) > 2 * b and sat > 0.15:
                # Brightness-aware: keep luminosity profile but reskin in brand color
                lum = mx / 255
                color = tuple(int(c * (0.4 + 0.6 * lum)) for c in grad)
                out_pixels[x, y] = (*color, a)
                continue

            # Mid grey or dark non-gold: tint towards BG
            blend_t = 1 - (mx / 255)
            color = lerp((r, g, b), BG, min(1.0, blend_t))
            out_pixels[x, y] = (*color, a)

    return out


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Source missing: {SOURCE}")
    src = Image.open(SOURCE)
    print(f"Source: {src.size} {src.mode}")

    # Process at full res then downsample
    rebranded = recolor(src)
    rebranded.save(OUT_PNG, format="PNG")
    print(f"Wrote {OUT_PNG}")

    # Landing icon (256)
    OUT_LANDING.parent.mkdir(parents=True, exist_ok=True)
    rebranded.resize((512, 512), Image.LANCZOS).save(OUT_LANDING)
    print(f"Wrote {OUT_LANDING}")

    # Multi-res ICO for Windows
    sizes = [16, 32, 48, 64, 128, 256]
    rebranded.save(OUT_ICO, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Wrote {OUT_ICO} (sizes: {sizes})")


if __name__ == "__main__":
    main()
