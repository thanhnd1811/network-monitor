"""Generate ic_launcher.png at multiple DPIs for the Android app (pre-API-26 fallback)."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent / "android-src" / "app" / "src" / "main" / "res"

DPI_SIZES = {
    "mipmap-mdpi":    48,
    "mipmap-hdpi":    72,
    "mipmap-xhdpi":   96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

BLUE = (37, 99, 235, 255)
WHITE = (255, 255, 255, 255)


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = int(size * 0.04)
    radius = int(size * 0.22)
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=BLUE)

    # Shield
    cx, cy = size / 2, size / 2 + size * 0.02
    sw = size * 0.5
    sh = size * 0.55
    shield = [
        (cx - sw / 2, cy - sh / 2 + sh * 0.06),
        (cx, cy - sh / 2),
        (cx + sw / 2, cy - sh / 2 + sh * 0.06),
        (cx + sw / 2, cy + sh * 0.05),
        (cx, cy + sh / 2),
        (cx - sw / 2, cy + sh * 0.05),
    ]
    d.polygon(shield, fill=WHITE)

    # Check mark
    cw = max(2, size * 0.06)
    p1 = (cx - sw * 0.22, cy + sh * 0.02)
    p2 = (cx - sw * 0.05, cy + sh * 0.18)
    p3 = (cx + sw * 0.25, cy - sh * 0.18)
    d.line([p1, p2], fill=BLUE, width=int(cw))
    d.line([p2, p3], fill=BLUE, width=int(cw))
    return img


for folder, size in DPI_SIZES.items():
    out_dir = ROOT / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    img = make_icon(size)
    out_file = out_dir / "ic_launcher.png"
    img.save(out_file, "PNG")
    print(f"Wrote {out_file}")
