"""Renderar färdiga klipp för sociala medier från en klippplan.

Användning:
    python clips/render.py work/avsnitt/plan.json [--only 9x16] [--clip 01]

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
      "title": "Din förmåga att anpassa dig avgör din succé",
      "broll": [12, 55, 90, 168],
      "fix": {"Laganda": "Laganda"},
      "posts": {"instagram": "...", "linkedin": "...", "facebook": "...", "x": "..."}
    }
  ]
}

"broll" är löpnummer (k) ur config/broll_tags.json i den ordning de ska
visas; de hämtas automatiskt. "fix" rättar felhörda ord i undertexterna.

Stil (efter exemplen i Drive-mapp 2): B-roll i helbild, hook-rubrik överst i
fet seriff på svart rundad platta, undertexter några ord i taget där ordet som
sägs ligger på en klarblå rundad platta.

Resultat: out/<episode>/<id>-<titel>/<format>.mp4 + inlagg.md
"""

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import broll as brollmod  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "config" / "brand.json").read_text())
STYLE = BRAND["style"]
FONTS = ROOT / "fonts"
FPS = 30
# libass ritar ett typsnitt med storlek S ungefär som PIL med storlek S * 0.674
ASS_TO_PX = 0.674


def ass_color(hex_rgb: str, alpha: int = 0) -> str:
    h = hex_rgb.lstrip("#")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ass_time(t: float) -> str:
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def slug(text: str) -> str:
    s = text.lower()
    for a, b in (("å", "a"), ("ä", "a"), ("ö", "o"), ("é", "e")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "klipp"


class Measure:
    def __init__(self, file: str, ass_size: int):
        self.font = ImageFont.truetype(str(FONTS / file), max(1, round(ass_size * ASS_TO_PX)))

    def width(self, text: str) -> float:
        return self.font.getlength(text)


def rounded_rect(w: float, h: float, r: float) -> str:
    """ASS-ritning (\\p1) av en rundad rektangel med övre vänstra hörnet i 0,0."""
    r = min(r, w / 2, h / 2)
    k = r * 0.4477  # bezier-approximation av kvartscirkel
    return (
        f"m {r:.1f} 0 l {w - r:.1f} 0 b {w - k:.1f} 0 {w:.1f} {k:.1f} {w:.1f} {r:.1f} "
        f"l {w:.1f} {h - r:.1f} b {w:.1f} {h - k:.1f} {w - k:.1f} {h:.1f} {w - r:.1f} {h:.1f} "
        f"l {r:.1f} {h:.1f} b {k:.1f} {h:.1f} 0 {h - k:.1f} 0 {h - r:.1f} "
        f"l 0 {r:.1f} b 0 {k:.1f} {k:.1f} 0 {r:.1f} 0"
    )


def wrap(words, measure: Measure, max_w: float):
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if cur and measure.width(test) > max_w:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


def chunk_words(words, max_words, measure: Measure, max_w: float):
    """Korta undertextrader: max N ord, bryt vid skiljetecken, pauser och bredd."""
    chunks, cur = [], []
    for i, w in enumerate(words):
        if cur and measure.width(" ".join(x["w"] for x in cur + [w])) > max_w:
            chunks.append(cur)
            cur = []
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        pause = nxt is not None and nxt["s"] - w["e"] > 0.6
        punct = w["w"][-1:] in ".,!?:;"
        if len(cur) >= max_words or pause or punct or nxt is None:
            chunks.append(cur)
            cur = []
    return chunks


def layout(w: int, h: int):
    tall = h / w > 1.3
    base = w  # exemplen är 1080 breda; skala efter bredd, begränsa för liggande
    if not tall:
        base = min(w, h * 1.0)
    return {
        "title_y": h * (0.205 if tall else 0.15),
        "caption_y": h * (0.735 if tall else 0.80),
        "title_size": round(base * STYLE["title_size"]),
        "caption_size": round(base * STYLE["caption_size"]),
        "max_w": w * 0.84,
    }


def build_ass(words, title, duration, w, h) -> str:
    c = BRAND["colors"]
    L = layout(w, h)
    cap_font, title_font = STYLE["caption_font"], STYLE["title_font"]
    cap_m = Measure(STYLE["caption_font_file"], L["caption_size"])
    tit_m = Measure(STYLE["title_font_file"], L["title_size"])
    shadow = max(2, L["caption_size"] // 22)
    outline = L["caption_size"] * STYLE.get("caption_outline", 0.0)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{cap_font},{L['caption_size']},{ass_color(c['white'])},{ass_color(c['white'])},{ass_color('#000000')},{ass_color('#000000', 0x40)},0,0,0,0,100,100,0,0,1,{outline:.1f},{shadow},5,0,0,0,1
Style: Title,{title_font},{L['title_size']},{ass_color(c['white'])},{ass_color(c['white'])},{ass_color('#000000')},{ass_color('#000000')},0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Box,{cap_font},10,{ass_color('#000000')},{ass_color('#000000')},{ass_color('#000000')},{ass_color('#000000', 0xFF)},0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    cx = w / 2
    end_all = ass_time(duration)

    # Rubrik: rader i fet seriff på en svart rundad platta
    tl = wrap(title.split(), tit_m, L["max_w"] * 0.92)
    line_h = L["title_size"] * 0.78
    pad_x, pad_y = L["title_size"] * 0.38, L["title_size"] * 0.26
    box_w = max(tit_m.width(x) for x in tl) + 2 * pad_x
    box_h = line_h * len(tl) + 2 * pad_y
    if STYLE.get("title_box", True):
        ev.append(
            f"Dialogue: 0,{ass_time(0)},{end_all},Box,,0,0,0,,"
            f"{{\\an5\\pos({cx:.0f},{L['title_y']:.0f})\\1c{ass_color(STYLE['title_box_color'])}"
            f"\\1a&H{STYLE['title_box_alpha']:02X}&\\p1}}{rounded_rect(box_w, box_h, L['title_size'] * 0.28)}{{\\p0}}"
        )
    top = L["title_y"] - (line_h * len(tl)) / 2
    for i, line in enumerate(tl):
        y = top + line_h * (i + 0.5) + L["title_size"] * STYLE["text_y_offset"]
        ev.append(f"Dialogue: 1,{ass_time(0)},{end_all},Title,,0,0,0,,{{\\an5\\pos({cx:.0f},{y:.0f})}}{ass_escape(line)}")

    # Undertexter: varje ord placeras för sig så att plattan hamnar exakt bakom ordet
    hl = STYLE["highlight_color"]
    space = cap_m.width(" ")
    cy = L["caption_y"]
    ty = cy + L["caption_size"] * STYLE["text_y_offset"]
    bh = L["caption_size"] * 0.82
    for chunk in chunk_words(words, STYLE["caption_words"], cap_m, L["max_w"]):
        texts = [x["w"] for x in chunk]
        widths = [cap_m.width(t) for t in texts]
        total = sum(widths) + space * (len(texts) - 1)
        x = cx - total / 2
        centers = []
        for wd in widths:
            centers.append(x + wd / 2)
            x += wd + space
        c_start = chunk[0]["s"]
        c_end = chunk[-1]["e"] + 0.12
        if STYLE.get("caption_box", True):
            pw = total + L["caption_size"] * 0.75
            ph = L["caption_size"] * 1.12
            ev.append(
                f"Dialogue: 0,{ass_time(c_start)},{ass_time(c_end)},Box,,0,0,0,,"
                f"{{\\an5\\pos({cx:.0f},{cy:.0f})\\1c{ass_color(STYLE['caption_box_color'])}"
                f"\\1a&H{STYLE['caption_box_alpha']:02X}&\\p1}}{rounded_rect(pw, ph, L['caption_size'] * 0.24)}{{\\p0}}"
            )
        for j, t in enumerate(texts):
            ev.append(
                f"Dialogue: 2,{ass_time(c_start)},{ass_time(c_end)},Caption,,0,0,0,,"
                f"{{\\an5\\pos({centers[j]:.0f},{ty:.0f})}}{ass_escape(t)}"
            )
        for i, cw in enumerate(chunk):
            s = cw["s"]
            e = chunk[i + 1]["s"] if i + 1 < len(chunk) else c_end
            bw = widths[i] + L["caption_size"] * 0.30
            ev.append(
                f"Dialogue: 1,{ass_time(s)},{ass_time(e)},Box,,0,0,0,,"
                f"{{\\an5\\pos({centers[i]:.0f},{cy:.0f})\\1c{ass_color(hl)}\\p1}}"
                f"{rounded_rect(bw, bh, L['caption_size'] * 0.16)}{{\\p0}}"
            )
    return head + "\n".join(ev) + "\n"


def render_one(audio, words, clip, fmt, broll, outfile, workdir):
    w, h = BRAND["formats"][fmt]
    start, end = float(clip["start"]), float(clip["end"])
    dur = end - start
    fixes = clip.get("fix", {})
    rel = []
    for x in words:
        if x["s"] >= start - 0.05 and x["e"] <= end + 0.3:
            t = x["w"]
            for a, b in fixes.items():
                t = re.sub(rf"\b{re.escape(a)}\b", b, t)
            if t.strip():
                rel.append({"w": t, "s": max(0.0, x["s"] - start), "e": x["e"] - start})
    ass = workdir / f"{clip['id']}_{fmt}.ass"
    ass.write_text(build_ass(rel, clip["title"], dur, w, h))

    seg = float(STYLE.get("broll_seconds", 4.0))
    inputs, fparts = [], []
    n = max(1, math.ceil(dur / seg))
    labels = []
    for i in range(n):
        src = broll[i % len(broll)]
        # varje klipp används från början; återkommer det, ta en senare bit
        off = (i // len(broll)) * seg
        inputs += ["-stream_loop", "-1", "-ss", f"{off:.2f}", "-t", f"{seg:.2f}", "-i", str(src)]
        fparts.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"fps={FPS},setsar=1,format=yuv420p,trim=duration={seg:.2f},setpts=PTS-STARTPTS[b{i}]"
        )
        labels.append(f"[b{i}]")
    dim = STYLE.get("broll_dim", 0.0)
    post = f",eq=brightness={-dim:.2f}" if dim else ""
    fparts.append(f"{''.join(labels)}concat=n={n}:v=1:a=0,trim=duration={dur:.2f}{post}[bg]")
    inputs += ["-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", str(audio)]
    ass_arg = str(ass).replace(":", "\\:")
    fparts.append(f"[bg]subtitles={ass_arg}:fontsdir={FONTS}[v]")
    fparts.append(
        f"[{n}:a]aresample=48000,loudnorm=I=-14:TP=-1.5:LRA=11,"
        f"afade=t=in:d=0.08,afade=t=out:st={max(dur - 0.3, 0):.2f}:d=0.3[aout]"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
        "-filter_complex", ";".join(fparts),
        "-map", "[v]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-maxrate", "6M", "-bufsize", "12M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        "-t", f"{dur:.2f}", str(outfile),
    ]
    subprocess.run(cmd, check=True)


def write_posts(clip, outdir: Path, formats):
    ch = BRAND["channels"]
    names = {"instagram": "Instagram (Reels)", "facebook": "Facebook", "linkedin": "LinkedIn", "x": "X / Twitter"}
    lines = [f"# {clip['title']}", "", f"Klipp {clip['id']}: {clip['start']:.1f}–{clip['end']:.1f} s i avsnittet", ""]
    for key, label in names.items():
        fmt = ch.get(key)
        lines += [f"## {label}", f"Fil: `{fmt}.mp4`" if fmt in formats else "Fil: –", "",
                  clip.get("posts", {}).get(key, "").strip(), ""]
    (outdir / "inlagg.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--only", help="rendera bara dessa format, t.ex. 9x16,1x1")
    ap.add_argument("--clip", help="rendera bara klipp med detta id")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    words = json.loads(Path(plan["words"]).read_text())
    formats = args.only.split(",") if args.only else sorted(set(BRAND["channels"].values()))
    workdir = ROOT / "work" / "ass"
    workdir.mkdir(parents=True, exist_ok=True)

    clips = [c for c in plan["clips"] if not args.clip or c["id"] == args.clip]
    needed = sorted({k for c in clips for k in c.get("broll", [])})
    if needed:
        print(f"Hämtar {len(needed)} B-roll-klipp ...", flush=True)
        brollmod.fetch_many(needed)

    for clip in clips:
        broll = [brollmod.path_for(k) for k in clip.get("broll", [])]
        if not broll:
            sys.exit(f"Klipp {clip['id']} saknar 'broll' i planen")
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
