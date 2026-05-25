"""
make_icon.py — Generate a placeholder DataRescue icon (assets/icon.ico).

Run from the repo root:
    python build/make_icon.py

Replace assets/icon.ico with your real branded icon before shipping.
Requires Pillow (already in requirements.txt).
"""
import os
from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 32, 48, 64, 128, 256]
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico")
OUTPUT = os.path.normpath(OUTPUT)

FONT_PATHS = [
    # Windows
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\Arial.ttf",
    # macOS
    "/System/Library/Fonts/Helvetica.ttc",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _get_font(size):
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_icon():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    images = []
    for sz in SIZES:
        img = Image.new("RGBA", (sz, sz), (37, 99, 235, 255))   # #2563EB blue
        draw = ImageDraw.Draw(img)
        # Subtle inner circle
        m = sz // 8
        draw.ellipse([m, m, sz - m, sz - m], outline=(255, 255, 255, 80), width=max(1, sz // 32))
        # Text "DR"
        fsize = max(8, sz // 3)
        font = _get_font(fsize)
        text = "DR"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((sz - tw) // 2, (sz - th) // 2 - 1), text, fill=(255, 255, 255, 255), font=font)
        images.append(img)

    # Save the largest frame; Pillow resizes it to all requested sizes internally
    images[-1].save(
        OUTPUT,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
    )
    print(f"Icon saved to: {OUTPUT}")
    print("Replace with your real branded icon before releasing.")


if __name__ == "__main__":
    make_icon()
