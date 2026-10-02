"""Render every eval document with headless Edge, then make the 4 simulated photo conditions.

  python -m eval.render_docs
Writes eval/renders/<id>.png and eval/photos/<id>__<condition>.jpg, and copies two scam samples to web/samples."""
import shutil
import subprocess
import time
import zlib
from pathlib import Path

from PIL import Image, ImageChops

from eval.conditions import CONDITIONS, apply, jpeg_bytes

ROOT = Path(__file__).parent
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PROFILE = Path(r"D:\tmp\edge-eval-profile")
SAMPLES = {"scam_sms_power_cut": "scam_sms.jpg", "scam_whatsapp_lottery": "scam_whatsapp.jpg"}


def render(html: Path, png: Path) -> None:
    phone = '<div class="bar">' in html.read_text(encoding="utf-8")   # the SMS / WhatsApp shell
    size = "400,820" if phone else "800,1130"
    png.unlink(missing_ok=True)
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={PROFILE}",
                    f"--window-size={size}", f"--screenshot={png}", html.resolve().as_uri()],
                   check=True, capture_output=True, timeout=60)
    for _ in range(120):   # Edge's launcher returns before the browser process has written the file
        if png.exists() and png.stat().st_size and time.time() - png.stat().st_mtime > 0.5:
            break
        time.sleep(0.25)
    img = Image.open(png).convert("RGB")
    bbox = ImageChops.difference(img, Image.new("RGB", img.size, img.getpixel((img.width - 1, img.height - 1)))).getbbox()
    if bbox and not phone:   # trim the empty page below the paper
        img = img.crop((0, 0, img.width, min(img.height, bbox[3] + 24)))
    img.save(png)


def main() -> None:
    (ROOT / "renders").mkdir(exist_ok=True)
    photos = ROOT / "photos"
    photos.mkdir(exist_ok=True)
    for old in photos.glob("*.jpg"):
        if "__" not in old.stem:
            old.unlink()   # v1 names; v2 photos are <id>__<condition>.jpg
    for html in sorted((ROOT / "papers").glob("*.html")):
        png = ROOT / "renders" / f"{html.stem}.png"
        render(html, png)
        page = Image.open(png)
        for cond in CONDITIONS:
            seed = zlib.crc32(f"{html.stem}/{cond}".encode())
            (photos / f"{html.stem}__{cond}.jpg").write_bytes(jpeg_bytes(apply(page, cond, seed), cond))
        if html.stem in SAMPLES:
            shutil.copy(photos / f"{html.stem}__clean.jpg", ROOT.parent / "web" / "samples" / SAMPLES[html.stem])
        print("rendered", html.stem)


if __name__ == "__main__":
    main()
