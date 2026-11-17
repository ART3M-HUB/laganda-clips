"""Hämtar utvalda B-roll-klipp från Drive (länkdelad mapp) som lätta kopior.

Användning:
    python clips/broll.py <id-eller-k> [<id-eller-k> ...]

k = löpnumret i config/broll_tags.json. Varje klipp hämtas direkt från Google
med ffmpeg, kortas till max 20 s, får kortsidan 1080 px, 30 fps och inget ljud,
och sparas som work/broll_cache/<k>.mp4. Redan hämtade hoppas över.
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "work" / "broll_cache"
TAGS = json.loads((ROOT / "config" / "broll_tags.json").read_text())
BY_K = {e["k"]: e for cat in TAGS["categories"].values() for e in cat}


def path_for(k: int) -> Path:
    return CACHE / f"{k:03d}.mp4"


def fetch(k: int) -> Path:
    dest = path_for(k)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    e = BY_K[k]
    url = f"https://drive.usercontent.google.com/download?id={e['id']}&export=download&confirm=t"
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if proxy:
        cmd += ["-http_proxy", proxy]
    cmd += [
        "-user_agent", "Mozilla/5.0", "-i", url, "-t", "20", "-an",
        "-vf", "scale='if(lt(iw,ih),1080,-2)':'if(lt(iw,ih),-2,1080)',fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(dest) + ".part.mp4",
    ]
    CACHE.mkdir(parents=True, exist_ok=True)
    subprocess.run(cmd, check=True)
    Path(str(dest) + ".part.mp4").rename(dest)
    print(f"  B-roll {k}: {e['name']}", flush=True)
    return dest


def fetch_many(ks, workers: int = 6):
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(fetch, ks))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    fetch_many([int(a) for a in sys.argv[1:]])
