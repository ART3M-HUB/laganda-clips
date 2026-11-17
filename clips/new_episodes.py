"""Listar avsnitt i Drive-mapp 1 som inte är klippta än.

Användning:
    python clips/new_episodes.py            # skriver ut nya avsnitt: <id>\t<filnamn>
    python clips/new_episodes.py --done X   # markera filnamn X som klart i processed.txt

Mappen måste vara delad med "Alla som har länken". Klara avsnitt står i
processed.txt (ett filnamn per rad) och committas i repot.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_drive import list_folder  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "config" / "brand.json").read_text())
PROCESSED = ROOT / "processed.txt"
AUDIO_EXT = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".mp4", ".mov", ".webm")


def done() -> set:
    if not PROCESSED.exists():
        return set()
    return {line.strip() for line in PROCESSED.read_text().splitlines() if line.strip()}


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--done":
        names = done() | {sys.argv[2].strip()}
        PROCESSED.write_text("\n".join(sorted(names)) + "\n")
        print(f"Markerat som klart: {sys.argv[2]}")
        return
    seen = done()
    for fid, name in list_folder(BRAND["drive"]["incoming"]):
        if name.strip() in seen or not name.lower().endswith(AUDIO_EXT):
            continue
        if name.lower().startswith("copy of "):
            continue
        print(f"{fid}\t{name}")


if __name__ == "__main__":
    main()
