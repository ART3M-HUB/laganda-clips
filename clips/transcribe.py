"""Transkriberar ett helt avsnitt till ord med tidskoder.

Användning:
    python clips/transcribe.py avsnitt.mp3 work/avsnitt

Skapar:
    work/avsnitt/words.json      – alla ord med start/slut (sekunder)
    work/avsnitt/transcript.txt  – meningar med tidskoder, för att välja klipp
"""

import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "config" / "brand.json").read_text())


def fmt(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:05.2f}"


def main(audio: str, outdir: str) -> None:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(
        BRAND["whisper_model"],
        device="cpu",
        compute_type="int8",
        download_root=str(ROOT / "models"),
    )
    segments, info = model.transcribe(
        audio,
        language="sv",
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    words, lines = [], []
    for seg in segments:
        lines.append(f"[{fmt(seg.start)} - {fmt(seg.end)}] {seg.text.strip()}")
        for w in seg.words or []:
            words.append({"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)})
        print(lines[-1], flush=True)
    (out / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=0))
    (out / "transcript.txt").write_text("\n".join(lines) + "\n")
    print(f"\nKlart: {len(words)} ord, {info.duration:.0f} s ljud -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
