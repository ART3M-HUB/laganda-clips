"""Renderar färdiga klipp för sociala medier från en klippplan.

Användning:
    python clips/render.py work/avsnitt/plan.json [--only 9x16] [--broll mapp]

plan.json (skrivs av agenten efter att den läst transcript.txt):
{
  "episode": "avsnitt-01",
  "audio": "work/avsnitt/avsnitt.mp3",
  "words": "work/avsnitt/words.json",
  "clips": [
    {
      "id": "01",
      "start": 123.4,
      "end": 171.0,
      "title": "Varför uppvärmning vinner matcher",
      "posts": {"instagram": "...", "linkedin": "...", "facebook": "...", "x": "..."}
    }
  ]
}

Resultat: out/<episode>/<id>-<titel>/<format>.mp4 + inlagg.md
"""

import argparse
import json
import math
import random
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "config" / "brand.json").read_text())
FONTS = ROOT / "fonts"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
FPS = 30


def ass_color(hex_rgb: str, alpha: int = 0) -> str:
    """#rrggbb -> &HAABBGGRR (ASS använder BGR)."""
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_time(t: float) -> str:
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def slug(text: str) -> str:
    s = text.lower()
    for a, b in (("å", "a"), ("ä", "a"), ("ö", "o")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "klipp"


def chunk_words(words, max_words):
    """Delar orden i korta rader: max N ord, bryt vid skiljetecken och pauser."""
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        pause = nxt is not None and nxt["s"] - w["e"] > 0.6
        punct = w["w"][-1:] in ".,!?:;"
        if len(cur) >= max_words or pause or punct or nxt is None:
            chunks.append(cur)
            cur = []
    return chunks


def layout(w: int, h: int):
    """Positioner som andel av bildytan per format."""
    tall = h / w
    return {
        "title_y": int(h * (0.10 if tall > 1.2 else 0.09)),
        "caption_y": int(h * (0.56 if tall > 1.2 else 0.58)),
        "wave_y": int(h * (0.72 if tall > 1.2 else 0.74)),
        "wave_h": int(h * (0.09 if tall > 1.2 else 0.12)),
        "brand_y": int(h * 0.93),
        "caption_size": int(min(w, h) * (0.085 if tall > 1.2 else 0.075)),
        "title_size": int(min(w, h) * (0.075 if tall > 1.2 else 0.065)),
        "brand_size": int(min(w, h) * 0.038),
    }


def build_ass(words, title, duration, w, h) -> str:
    c = BRAND["colors"]
    f = BRAND["fonts"]
    L = layout(w, h)
    upper = BRAND.get("caption_uppercase", True)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{f['caption']},{L['caption_size']},{ass_color(c['white'])},{ass_color(c['white'])},{ass_color(c['blue'])},{ass_color('#000000', 0x80)},0,0,0,0,100,100,1,0,1,{max(4, L['caption_size'] // 12)},3,5,60,60,0,1
Style: Title,{f['heading']},{L['title_size']},{ass_color(c['white'])},{ass_color(c['white'])},{ass_color(c['blue'])},{ass_color(c['blue'])},0,0,0,0,100,100,2,0,3,{max(10, L['title_size'] // 4)},0,5,80,80,0,1
Style: Brand,{f['label']},{L['brand_size']},{ass_color(c['orange'])},{ass_color(c['orange'])},{ass_color('#000000')},{ass_color('#000000', 0xFF)},0,0,0,0,100,100,{L['brand_size'] // 2},0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    cx = w // 2
    title_txt = ass_escape(title.upper())
    ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(duration)},Title,,0,0,0,,{{\\pos({cx},{L['title_y']})\\fad(250,0)}}{title_txt}")
    ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(duration)},Brand,,0,0,0,,{{\\pos({cx},{L['brand_y']})}}{BRAND['brand_label']}")

    hl = ass_color(c["orange"])
    for chunk in chunk_words(words, BRAND.get("caption_words_per_line", 3)):
        for i, cw in enumerate(chunk):
            start = cw["s"]
            end = chunk[i + 1]["s"] if i + 1 < len(chunk) else cw["e"] + 0.15
            parts = []
            for j, other in enumerate(chunk):
                t = ass_escape(other["w"].upper() if upper else other["w"])
                if j == i:
                    parts.append(f"{{\\c{hl}\\fscx108\\fscy108}}{t}{{\\c{ass_color(c['white'])}\\fscx100\\fscy100}}")
                else:
                    parts.append(t)
            pop = "\\t(0,80,\\fscx104\\fscy104)" if i == 0 else ""
            ev.append(
                f"Dialogue: 2,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,"
                f"{{\\pos({cx},{L['caption_y']}){pop}}}{' '.join(parts)}"
            )
    return head + "\n".join(ev) + "\n"


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def render_one(audio, words, clip, fmt, broll, outfile, workdir):
    w, h = BRAND["formats"][fmt]
    start, end = float(clip["start"]), float(clip["end"])
    dur = end - start
    rel = [
        {"w": x["w"], "s": x["s"] - start, "e": x["e"] - start}
        for x in words
        if x["s"] >= start - 0.05 and x["e"] <= end + 0.3
    ]
    ass = workdir / f"{clip['id']}_{fmt}.ass"
    ass.write_text(build_ass(rel, clip["title"], dur, w, h))

    L = layout(w, h)
    c = BRAND["colors"]
    seg = float(BRAND.get("broll_seconds", 4.0))
    inputs, fparts = [], []

    if broll:
        rng = random.Random(f"{clip['id']}-{fmt}")
        n = math.ceil(dur / seg)
        order = broll[:]
        rng.shuffle(order)
        labels = []
        for i in range(n):
            src = order[i % len(order)]
            length = probe_duration(src)
            off = rng.uniform(0, max(0.0, length - seg)) if length > seg else 0
            inputs += ["-stream_loop", "-1", "-ss", f"{off:.2f}", "-t", f"{seg:.2f}", "-i", str(src)]
            fparts.append(
                f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                f"fps={FPS},setsar=1,format=yuv420p,trim=duration={seg:.2f},setpts=PTS-STARTPTS[b{i}]"
            )
            labels.append(f"[b{i}]")
        fparts.append(f"{''.join(labels)}concat=n={n}:v=1:a=0,trim=duration={dur:.2f}[bgraw]")
        fparts.append(
            f"[bgraw]eq=brightness=-0.06:saturation=0.85,"
            f"drawbox=x=0:y=0:w=iw:h=ih:color=0x{c['blue'].lstrip('#')}@{BRAND['broll_tint_opacity']}:t=fill[bg]"
        )
        a_idx = n
    else:
        inputs += ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", f"color=c=0x{c['blue'].lstrip('#')}:s={w}x{h}:r={FPS}"]
        fparts.append("[0:v]format=yuv420p[bg]")
        a_idx = 1

    inputs += ["-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", str(audio)]
    fparts.append(f"[{a_idx}:a]aresample=48000,asplit=2[a1][a2]")
    fparts.append(
        f"[a1]showwaves=s={w}x{L['wave_h']}:mode=cline:rate={FPS}:scale=sqrt:"
        f"colors=0x{c['lightblue'].lstrip('#')},format=rgba,colorchannelmixer=aa=0.85[wave]"
    )
    fparts.append(f"[bg][wave]overlay=0:{L['wave_y'] - L['wave_h'] // 2}:shortest=1[v1]")
    ass_arg = str(ass).replace(":", "\\:")
    fparts.append(f"[v1]subtitles={ass_arg}:fontsdir={FONTS}[v]")
    fparts.append(f"[a2]afade=t=in:d=0.15,afade=t=out:st={max(dur - 0.4, 0):.2f}:d=0.4[aout]")

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
        "-filter_complex", ";".join(fparts),
        "-map", "[v]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-t", f"{dur:.2f}", str(outfile),
    ]
    subprocess.run(cmd, check=True)


def write_posts(clip, outdir: Path, formats):
    ch = BRAND["channels"]
    lines = [f"# {clip['title']}", "", f"Klipp {clip['id']}: {clip['start']:.1f}–{clip['end']:.1f} s i avsnittet", ""]
    names = {"instagram": "Instagram (Reels)", "facebook": "Facebook", "linkedin": "LinkedIn", "x": "X / Twitter"}
    for key, label in names.items():
        fmt = ch.get(key)
        lines += [f"## {label}", f"Fil: `{fmt}.mp4`" if fmt in formats else "Fil: –", "", clip.get("posts", {}).get(key, "").strip(), ""]
    (outdir / "inlagg.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--only", help="rendera bara dessa format, t.ex. 9x16,1x1")
    ap.add_argument("--broll", default=str(ROOT / "work" / "broll"), help="mapp med B-roll-videor")
    ap.add_argument("--clip", help="rendera bara klipp med detta id")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    words = json.loads(Path(plan["words"]).read_text())
    broll_dir = Path(args.broll)
    broll = sorted(p for p in broll_dir.glob("*") if p.suffix.lower() in VIDEO_EXT) if broll_dir.exists() else []
    formats = args.only.split(",") if args.only else sorted(set(BRAND["channels"].values()))
    workdir = ROOT / "work" / "ass"
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"B-roll: {len(broll)} filer, format: {', '.join(formats)}")

    for clip in plan["clips"]:
        if args.clip and clip["id"] != args.clip:
            continue
        outdir = ROOT / "out" / plan["episode"] / f"{clip['id']}-{slug(clip['title'])}"
        outdir.mkdir(parents=True, exist_ok=True)
        for fmt in formats:
            target = outdir / f"{fmt}.mp4"
            print(f"  {clip['id']} {fmt} -> {target.relative_to(ROOT)}", flush=True)
            render_one(plan["audio"], words, clip, fmt, broll, target, workdir)
        write_posts(clip, outdir, formats)
    print("Klart.")


if __name__ == "__main__":
    sys.exit(main())
