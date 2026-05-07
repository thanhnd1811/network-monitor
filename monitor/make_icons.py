"""Generate PWA icons (192 and 512 px) — a network shield motif."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "web" / "icons"
OUT.mkdir(parents=True, exist_ok=True)


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded square background, blue gradient feel (solid color, simple)
    pad = int(size * 0.04)
    radius = int(size * 0.22)
    bg = (37, 99, 235, 255)  # blue-600
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=bg)

    # Shield outline
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
    d.polygon(shield, fill=(255, 255, 255, 255))

    # Check mark inside shield
    cw = size * 0.06
    pts = [
        (cx - sw * 0.22, cy + sh * 0.02),
        (cx - sw * 0.05, cy + sh * 0.18),
        (cx + sw * 0.25, cy - sh * 0.18),
    ]
    d.line([pts[0], pts[1]], fill=bg, width=int(cw))
    d.line([pts[1], pts[2]], fill=bg, width=int(cw))

    return img


for s in (192, 512):
    img = make_icon(s)
    out = OUT / f"icon-{s}.png"
    img.save(out, "PNG")
    print(f"Wrote {out}")
