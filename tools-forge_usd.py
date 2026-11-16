"""Dollar UV distractors, built from the official reference image.

Source: "Decoding Dollars: the $100", U.S. Currency Education Program,
the detail showing the security thread under ultraviolet light.

The $100 thread must glow PINK. The Teller Toolkit gives the colour for
every denomination: $100 pink, $50 yellow, $20 green, $10 orange,
$5 blue. A bleached lower denomination reprinted as a $100 keeps its own
thread, so the colour is the giveaway - which is what these reproduce.
"""
from PIL import Image
import numpy as np, base64, io, os, json

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_W, OUT_H = 400, 494          # keeps the reference's portrait shape

src = Image.open(os.path.join(BASE, "p5_6_256x316.png")).convert("RGB")
src = src.resize((OUT_W, OUT_H), Image.LANCZOS)
a0 = np.asarray(src).astype(np.float32)
r, g, b = a0[..., 0], a0[..., 1], a0[..., 2]
thread = (r > 110) & (b > 90) & (g < r - 35)
# widen by a couple of pixels so anti-aliased edges do not keep a pink
# fringe, which would betray the edit
from PIL import ImageFilter
_m = Image.fromarray((thread * 255).astype(np.uint8))
_m = _m.filter(ImageFilter.MaxFilter(5))
thread = np.asarray(_m) > 127
# brightness inside the thread carries the "USA 100" lettering
lum = (r * 0.4 + g * 0.3 + b * 0.3)
norm = np.clip((lum - 60) / 150.0, 0, 1.25)


def recolour(rgb_mul, label):
    out = a0.copy()
    tint = np.stack([norm * rgb_mul[0], norm * rgb_mul[1], norm * rgb_mul[2]], axis=-1)
    out[thread] = tint[thread]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), label


def thread_dark():
    """Defect: the thread does not fluoresce at all."""
    out = a0.copy()
    bg = np.median(a0[~thread], axis=0)
    out[thread] = bg * (0.75 + 0.3 * norm[thread][:, None])
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), "fil éteint"


def paper_glows():
    """Defect: ordinary paper with optical brighteners lights up."""
    out = a0.copy()
    l = out.mean(axis=2, keepdims=True)
    dark = np.clip(1.0 - l / 120.0, 0, 1)
    out = out + dark * (np.array([205.0, 210.0, 230.0]) - out) * 0.72
    out[thread] = a0[thread]                      # thread itself unchanged
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), "papier fluorescent"


VARIANTS = {
    "usdUV": (src, "AUTHENTIQUE — fil rose"),
    "usdUVa": recolour((60, 120, 235), "fil bleu (billet de 5 $ blanchi)"),
    "usdUVb": recolour((235, 205, 60), "fil jaune (billet de 50 $ blanchi)"),
    "usdUVc": thread_dark(),
    "usdUVd": paper_glows(),
}

store = os.path.join(BASE, "usd-imgs.json")
out = {}
for key, (img, label) in VARIANTS.items():
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    out[key] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    print(f"{key:8s} {img.size[0]}x{img.size[1]}  {buf.tell()/1024:5.1f} KB   {label}")
    img.save(os.path.join(BASE, f"tile-{key}.png"))
json.dump(out, io.open(store, "w", encoding="utf-8"))
print(f"\ntotal: {sum(len(v) for v in out.values())/1024:.0f} KB of base64")

from PIL import ImageDraw
rows = [(lbl, Image.open(os.path.join(BASE, f"tile-{k}.png"))) for k, (_, lbl) in VARIANTS.items()]
sheet = Image.new("RGB", (OUT_W * len(rows), OUT_H + 22), (10, 14, 30))
d = ImageDraw.Draw(sheet)
for i, (lbl, im) in enumerate(rows):
    d.text((i * OUT_W + 6, 4), lbl, fill=(245, 245, 252))
    sheet.paste(im, (i * OUT_W, 20))
sheet.save(os.path.join(BASE, "usd-preview.png"))
print("preview:", sheet.size)
