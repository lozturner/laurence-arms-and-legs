"""Generate paperclip.ico from the in-app paperclip glyph. Runs in CI."""
from PIL import Image, ImageDraw
from pathlib import Path


def paperclip_image(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (44, 62, 80, 255))  # solid bg so it shows in Explorer
    d = ImageDraw.Draw(img)
    pad = size // 6
    line = max(2, size // 14)
    d.rounded_rectangle(
        (pad, pad, size - pad, size - pad // 2),
        radius=size // 4, outline="#ecf0f1", width=line,
    )
    d.rounded_rectangle(
        (pad + line * 2, pad + line * 2, size - pad - line * 2, size - pad // 2 - line),
        radius=size // 5, outline="#ecf0f1", width=line,
    )
    return img


def main():
    out = Path(__file__).with_name("paperclip.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base = paperclip_image(256)
    icons = [paperclip_image(s) for s in sizes]
    base.save(out, format="ICO", sizes=[(s, s) for s in sizes], append_images=icons)
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
