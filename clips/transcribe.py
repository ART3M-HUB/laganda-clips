"""Transkriberar ett avsnitt (eller valda delar) till ord med tidskoder.

Användning:
    python clips/transcribe.py avsnitt.mp3 work/avsnitt [--lang en] [--model M]
    python clips/transcribe.py avsnitt.mp3 work/avsnitt --lang en --windows 120.5-171,300-345

--lang:    sv (standard, KBLab:s svenska modell) eller en (engelsk modell).
           Kolla språket i de första minuterna innan hela avsnittet körs –
           den svenska modellen gör engelskt tal oläsligt.
--model:   annan modell, t.ex. Systran/faster-whisper-medium.en för bättre
           kvalitet på utvalda klipp (långsammare).
--windows: transkribera bara dessa tidsintervall (sekunder) och skriv
           words_windows.json – används för noggrann utskrift av valda klipp.

Skapar:
    work/avsnitt/words.json      – alla ord med start/slut (sekunder)
    work/avsnitt/transcript.txt  – meningar med tidskoder, för att välja klipp
"""

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "config" / "brand.json").read_text())
MODELS = {"sv": BRAND["whisper_model"], "en": BRAND.get("whisper_model_en", "Systran/faster-whisper-small.en")}


def fmt(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:05.2f}"


def load_audio(path: str, start: float = 0.0, dur: float = 0.0) -> np.ndarray:
    """Avkodar valfri ljud-/videofil till 16 kHz mono med ffmpeg."""
    cmd = ["ffmpeg", "-v", "error"]
    if start:
        cmd += ["-ss", f"{start:.2f}"]
    if dur:
        cmd += ["-t", f"{dur:.2f}"]
    cmd += ["-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def run(model, audio, lang, offset=0.0, vad=True):
    segments, info = model.transcribe(
        audio,
        language=lang,
        word_timestamps=True,
        vad_filter=vad,
        condition_on_previous_text=False,
    )
    words, lines = [], []
    for seg in segments:
        lines.append(f"[{fmt(seg.start + offset)} - {fmt(seg.end + offset)}] {seg.text.strip()}")
        for w in seg.words or []:
            words.append({"w": w.word.strip(), "s": round(w.start + offset, 2), "e": round(w.end + offset, 2)})
        print(lines[-1], flush=True)
    return words, lines, info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("outdir")
    ap.add_argument("--lang", default="sv", choices=["sv", "en"])
    ap.add_argument("--model")
    ap.add_argument("--windows")
    a = ap.parse_args()

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(a.model or MODELS[a.lang], device="cpu", compute_type="int8",
                         download_root=str(ROOT / "models"))

    if a.windows:
        words = []
        for part in a.windows.split(","):
            s, e = (float(x) for x in part.split("-"))
            s0 = max(0.0, s - 1.0)
            w, _, _ = run(model, load_audio(a.audio, s0, e - s0 + 1.0), a.lang, offset=s0, vad=False)
            words += w
        (out / "words_windows.json").write_text(json.dumps(words, ensure_ascii=False, indent=0))
        print(f"\nKlart: {len(words)} ord i {len(a.windows.split(','))} intervall -> {out / 'words_windows.json'}")
        return

    words, lines, info = run(model, load_audio(a.audio), a.lang)
    (out / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=0))
    (out / "transcript.txt").write_text("\n".join(lines) + "\n")
    print(f"\nKlart: {len(words)} ord, {info.duration:.0f} s ljud -> {out}")


if __name__ == "__main__":
    main()
