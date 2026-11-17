"""Hämtar filer från Google Drive som delats med "Alla som har länken".

Användning:
    python clips/fetch_drive.py <länk till fil eller mapp> <målmapp>

En mapplänk hämtar alla filer direkt i mappen (inte undermappar).
Filer som redan finns med samma storlek hoppas över.
"""

import html
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (laganda-clips)"}


def get(url: str):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)


def parse_id(link: str):
    m = re.search(r"/folders/([\w-]+)", link)
    if m:
        return "folder", m.group(1)
    m = re.search(r"/file/d/([\w-]+)", link) or re.search(r"[?&]id=([\w-]+)", link)
    if m:
        return "file", m.group(1)
    if re.fullmatch(r"[\w-]{20,}", link):
        return "file", link
    sys.exit(f"Känner inte igen länken: {link}")


def list_folder(folder_id: str):
    """Listar filer i en länkdelad mapp via Drives enkla inbäddningsvy."""
    page = get(f"https://drive.google.com/embeddedfolderview?id={folder_id}").read().decode("utf-8", "replace")
    entries = re.findall(
        r'<a href="https://drive\.google\.com/file/d/([\w-]+)/view[^"]*"[^>]*>.*?'
        r'<div class="flip-entry-title">(.*?)</div>',
        page, re.S,
    )
    if not entries and "flip-entry" not in page:
        sys.exit("Kunde inte läsa mappen – är den delad med 'Alla som har länken'?")
    return [(fid, html.unescape(name).strip()) for fid, name in entries]


def download(file_id: str, dest_dir: Path, name: str | None = None) -> Path:
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    with get(url) as r:
        ctype = r.headers.get("Content-Type", "")
        if "text/html" in ctype:
            sys.exit(f"Fick en webbsida i stället för filen {file_id} – är den delad med länk?")
        if not name:
            cd = r.headers.get("Content-Disposition", "")
            m = re.search(r"filename\*=UTF-8''([^;]+)", cd) or re.search(r'filename="([^"]+)"', cd)
            name = urllib.parse.unquote(m.group(1)) if m else file_id
        size = int(r.headers.get("Content-Length") or 0)
        dest = dest_dir / name
        if dest.exists() and size and dest.stat().st_size == size:
            print(f"  finns redan: {name}")
            return dest
        print(f"  hämtar: {name} ({size / 1e6:.1f} MB)", flush=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            shutil.copyfileobj(r, f, length=1 << 20)
        tmp.rename(dest)
    return dest


def main(link: str, outdir: str):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    kind, fid = parse_id(link)
    if kind == "file":
        download(fid, out)
    else:
        files = list_folder(fid)
        print(f"{len(files)} filer i mappen")
        for file_id, name in files:
            download(file_id, out, name)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
