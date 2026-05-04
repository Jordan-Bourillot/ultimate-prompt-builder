"""Generate the Windows .ico from the Triskell logo (PIL).

Run: python tools/make_icon.py
Output: assets/icon.ico (multi-resolution: 16, 32, 48, 64, 128, 256)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app import _make_triskell_logo  # noqa: E402

OUT_ICO = ROOT / "assets" / "icon.ico"
OUT_PNG = ROOT / "assets" / "icon.png"

OUT_ICO.parent.mkdir(parents=True, exist_ok=True)

# Multi-resolution ICO so Windows picks the right size in every context.
# Generate a high-res master and let Pillow downsample for each requested size.
sizes = [16, 32, 48, 64, 128, 256]
master = _make_triskell_logo(256, "#08080F").convert("RGBA")
master.save(
    OUT_ICO,
    format="ICO",
    sizes=[(s, s) for s in sizes],
)
master.save(OUT_PNG, format="PNG")

print(f"Wrote {OUT_ICO} (sizes: {sizes}) — {OUT_ICO.stat().st_size} bytes")
print(f"Wrote {OUT_PNG} (256x256) — {OUT_PNG.stat().st_size} bytes")
