"""Builds every training distractor from the genuine ECB images.

Each defect is a documented counterfeit failure mode, so the feedback
shown to the candidate names a real check. Nothing here is a usable
reproduction of a banknote: these are 500 px UV and infrared views.
"""
from PIL import Image, ImageEnhance
import numpy as np, os, io, base64, json

BASE = os.path.dirname(os.path.abspath(__file__))
W = 500
H50, H100 = round(W / 1.818), round(W / 1.909)


def load(name, h):
    return Image.open(os.path.join(BASE, name)).convert("RGB").resize((W, h), Image.LANCZOS)


# ----------------------------------------------------------------- UV defects
def uv_paper_glows(img):
    """Defect: the paper itself fluoresces. Genuine paper stays dark."""
    a = np.asarray(img).astype(np.float32)
    lum = a.mean(axis=2, keepdims=True)
    dark = np.clip(1.0 - lum / 110.0, 0, 1)
    a = a + dark * (np.array([150.0, 140.0, 190.0]) - a) * 0.55
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def uv_wrong_colour(img):
    """Defect: the print fluoresces, but in the wrong colour."""
    a = np.asarray(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    glow = (g > 95) & (g > b + 15)
    lum = (r * 0.3 + g * 0.6 + b * 0.1)
    # same brightness, pushed from yellow-green towards orange-red
    orange = np.stack([lum * 1.12, lum * 0.55, lum * 0.22], axis=-1)
    out = a.copy()
    out[glow] = orange[glow]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def uv_print_not_fluorescent(img):
    """Defect: the fluorescent print is missing; the main area stays dark."""
    a = np.asarray(img).astype(np.float32)
    g, b = a[..., 1], a[..., 2]
    glow = (g > 95) & (g > b + 15)
    out = a.copy()
    lum = out[..., :3].mean(axis=2)
    # keep the engraving as a dark blue ghost instead of a green glow
    shade = np.stack([lum * 0.22, lum * 0.34, lum * 0.72], axis=-1)
    out[glow] = shade[glow]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


# ----------------------------------------------------------- infrared defects
def ir_nothing_disappears(normal, h):
    """Defect: ordinary inks, so the note stays fully readable."""
    g = normal.convert("L").resize((W, h), Image.LANCZOS)
    g = ImageEnhance.Brightness(g).enhance(1.26)
    g = ImageEnhance.Contrast(g).enhance(0.85)
    return g.convert("RGB")


def ir_too_much_survives(img):
    """Defect: print that should vanish is still there, faint but legible."""
    g = img.convert("L")
    a = np.asarray(g).astype(np.float32)
    # pull the faint ghosting up into clearly visible mid greys
    a = 255 - (255 - a) * 2.6
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGB")


def ir_almost_blank(img):
    """Defect: even the features that must remain have vanished."""
    g = img.convert("L")
    a = np.asarray(g).astype(np.float32)
    a = 255 - (255 - a) * 0.22
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGB")


def ir_numeral_gone(img):
    """Defect: the value numeral, which must stay visible, is absent."""
    from PIL import ImageFilter
    g = img.convert("L")
    a = np.asarray(g).astype(np.float32)
    h, w = a.shape
    y0, y1, x0, x1 = int(h * 0.55), h, 0, int(w * 0.34)
    region = a[y0:y1, x0:x1]
    med = np.median(region)
    dark = region < med - 10
    if dark.any():
        paper = float(np.median(region[~dark])) if (~dark).any() else med
        region = region.copy()
        region[dark] = paper + np.random.uniform(-2.5, 2.5, size=int(dark.sum()))
        a[y0:y1, x0:x1] = region
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    # feather the patched area so no outline betrays the edit
    blur = out.filter(ImageFilter.GaussianBlur(1.1))
    ab, ao = np.asarray(blur).astype(np.float32), np.asarray(out).astype(np.float32)
    m = np.zeros_like(ao)
    m[y0:y1, x0:x1] = 1.0
    merged = ao * (1 - m) + ab * m
    return Image.fromarray(np.clip(merged, 0, 255).astype(np.uint8)).convert("RGB")


# --------------------------------------------------------------------- build
uv100, uv50 = load("crop-uv100.png", H100), load("crop-uv50.png", H50)
ir100, ir50 = load("crop-ir100.png", H100), load("crop-ir50.png", H50)
normal100 = Image.open(os.path.join(BASE, "note-eur-normal.jpg"))

SPEC = {
    "uv100a": (uv_paper_glows(uv100), "100 € UV — le papier brille"),
    "uv100b": (uv_wrong_colour(uv100), "100 € UV — fluorescence de la mauvaise couleur"),
    "uv100c": (uv_print_not_fluorescent(uv100), "100 € UV — impression non fluorescente"),
    "uv50a": (uv_paper_glows(uv50), "50 € UV — le papier brille"),
    "uv50b": (uv_wrong_colour(uv50), "50 € UV — fluorescence de la mauvaise couleur"),
    "uv50c": (uv_print_not_fluorescent(uv50), "50 € UV — impression non fluorescente"),
    "ir100a": (ir_nothing_disappears(normal100, H100), "100 € IR — rien ne disparaît"),
    "ir100b": (ir_too_much_survives(ir100), "100 € IR — trop subsiste"),
    "ir100c": (ir_numeral_gone(ir100), "100 € IR — nombre de valeur absent"),
    "ir50a": (ir_too_much_survives(ir50), "50 € IR — trop subsiste"),
    "ir50b": (ir_almost_blank(ir50), "50 € IR — presque rien ne subsiste"),
    "ir50c": (ir_numeral_gone(ir50), "50 € IR — nombre de valeur absent"),
}

out = json.load(io.open(os.path.join(BASE, "newimgs.json"), encoding="utf-8"))
total = 0
for key, (img, label) in SPEC.items():
    if key.startswith("ir"):
        img = img.convert("L")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80 if key.startswith("uv") else 82,
             optimize=True, progressive=True)
    out[key] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    total += len(out[key])
    print(f"{key:8s} {img.size[0]}x{img.size[1]}  {buf.tell()/1024:5.1f} KB   {label}")
    img.convert("RGB").save(os.path.join(BASE, f"gen-{key}.png"))

json.dump(out, io.open(os.path.join(BASE, "newimgs.json"), "w", encoding="utf-8"))
print(f"\n12 generated tiles: {total/1024:.0f} KB of base64")

# preview: each question as it will be seen
from PIL import ImageDraw
GROUPS = [("100 € UV", "uv100", ["uv100a", "uv100b", "uv100c"], uv100),
          ("50 € UV", "uv50", ["uv50a", "uv50b", "uv50c"], uv50),
          ("100 € IR", "ir100", ["ir100a", "ir100b", "ir100c"], ir100),
          ("50 € IR", "ir50", ["ir50a", "ir50b", "ir50c"], ir50)]
rows = []
for title, gkey, fakes, gimg in GROUPS:
    rows.append(("AUTHENTIQUE — " + title, gimg.convert("RGB")))
    for f in fakes:
        rows.append(("faux — " + SPEC[f][1], Image.open(os.path.join(BASE, f"gen-{f}.png"))))
sheet = Image.new("RGB", (W, sum(r[1].height + 20 for r in rows)), (10, 14, 30))
y = 0
d = ImageDraw.Draw(sheet)
for label, im in rows:
    d.text((6, y + 4), label, fill=(245, 245, 252))
    sheet.paste(im, (0, y + 18))
    y += im.height + 20
sheet.save(os.path.join(BASE, "forge-all-preview.png"))
print("preview:", sheet.size)
