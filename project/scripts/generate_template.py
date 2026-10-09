"""Generate templates/certificate_template.png (decorative background only).

Dynamic text is overlaid at render time by ReportLab, so a designer can replace
this PNG with any A4-landscape artwork (3508x2480 px recommended) without code changes.

Usage: python scripts/generate_template.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 3508, 2480  # A4 landscape @ 300 DPI
NAVY, GOLD, CREAM = (18, 42, 76), (191, 155, 48), (253, 250, 242)


def main() -> None:
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle([60, 60, W - 60, H - 60], outline=NAVY, width=36)      # outer frame
    d.rectangle([130, 130, W - 130, H - 130], outline=GOLD, width=10)  # inner gold line
    d.rectangle([60, 60, W - 60, 330], fill=NAVY)                      # header band
    d.rectangle([60, H - 330, W - 60, H - 60], fill=NAVY)              # footer band
    for cx, cy in [(190, 190), (W - 190, 190), (190, H - 190), (W - 190, H - 190)]:
        d.ellipse([cx - 45, cy - 45, cx + 45, cy + 45], fill=GOLD)     # corner ornaments
    out = Path(__file__).resolve().parent.parent / "templates" / "certificate_template.png"
    out.parent.mkdir(exist_ok=True)
    img.save(out, optimize=True)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
