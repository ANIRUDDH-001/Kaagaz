"""Simulated phone-photo conditions for the eval. Deterministic: the same seed gives the same photo, so a run can be
repeated. These are simulations (tilt, shadow, dim light, noise, creases, blur), labelled as such in the results."""
import io

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

CONDITIONS = ("clean", "tilted", "dim", "creased")
QUALITY = {"clean": 90, "tilted": 80, "dim": 35, "creased": 70}


def _coeffs(src, dst):
    rows = []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    a = np.array(rows, dtype=float)
    b = np.array(src, dtype=float).reshape(8)
    return np.linalg.lstsq(a, b, rcond=None)[0].tolist()


def _tilted(img, rng):
    w, h = img.size
    pad = int(0.08 * w)
    table = Image.new("RGB", (w + 2 * pad, h + 2 * pad), (92, 74, 58))
    table.paste(img, (pad, pad))
    W, H = table.size
    j = lambda s: float(rng.uniform(0, s))  # noqa: E731
    src = [(pad, pad), (pad + w, pad), (pad + w, pad + h), (pad, pad + h)]
    dst = [(pad + j(0.07 * w), pad + j(0.05 * h)), (pad + w - j(0.03 * w), pad + j(0.02 * h)),
           (pad + w - j(0.06 * w), pad + h - j(0.04 * h)), (pad + j(0.02 * w), pad + h - j(0.03 * h))]
    out = table.transform((W, H), Image.PERSPECTIVE, _coeffs(src, dst), Image.BICUBIC, fillcolor=(92, 74, 58))
    shade = np.linspace(1.0, float(rng.uniform(0.55, 0.7)), W)[None, :, None]   # a shadow across the page
    arr = np.asarray(out, dtype=float) * shade
    return Image.fromarray(arr.clip(0, 255).astype("uint8"))


def _dim(img, rng):
    img = ImageEnhance.Brightness(img).enhance(0.55)
    img = ImageEnhance.Contrast(img).enhance(0.8)
    arr = np.asarray(img, dtype=float)
    arr = arr * np.array([1.0, 0.94, 0.82]) + rng.normal(0, 12, arr.shape)      # warm bulb, sensor noise
    return Image.fromarray(arr.clip(0, 255).astype("uint8"))


def _creased(img, rng):
    w, h = img.size
    img = img.rotate(float(rng.uniform(-2.5, 2.5)), resample=Image.BICUBIC, expand=False, fillcolor=(235, 230, 220))
    overlay = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(overlay)
    for _ in range(3):
        if rng.random() < 0.5:
            y = int(rng.uniform(0.2, 0.8) * h)
            d.line([(0, y), (w, y + int(rng.uniform(-20, 20)))], fill=int(rng.uniform(50, 90)), width=int(rng.uniform(3, 7)))
        else:
            x = int(rng.uniform(0.2, 0.8) * w)
            d.line([(x, 0), (x + int(rng.uniform(-20, 20)), h)], fill=int(rng.uniform(50, 90)), width=int(rng.uniform(3, 7)))
    overlay = overlay.filter(ImageFilter.GaussianBlur(4))
    arr = np.asarray(img, dtype=float) * (1 - np.asarray(overlay, dtype=float)[..., None] / 255 * 0.6)
    return Image.fromarray(arr.clip(0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.2))


def apply(img: Image.Image, cond: str, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    img = img.convert("RGB")
    if cond == "clean":
        return img
    return {"tilted": _tilted, "dim": _dim, "creased": _creased}[cond](img, rng)


def jpeg_bytes(img: Image.Image, cond: str) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=QUALITY[cond])
    return buf.getvalue()
