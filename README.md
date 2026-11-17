# Laganda Clips

Gör korta klipp för sociala medier (Instagram, Facebook, LinkedIn, X) av
Lagandas poddavsnitt som spelas in i Riverside. Eftersom vi mest spelar in
ljud lägger verktyget på rörliga bilder (B-roll), ljudvåg, rubrik och
undertexter i Lagandas färger och typsnitt.

## Var allt ligger

| Vad | Var |
|---|---|
| Koden | GitHub: `ART3M-HUB/laganda-clips` (det här repot) |
| Alla filer (ljud, video, färdiga klipp) | Google Drive → Min enhet → **Laganda Clips** – https://drive.google.com/drive/folders/1CXSi2_iKZjyJO1nIYEI7vZiw8SXdMnDd |

Mapparna i Drive:

| Mapp | Vem | Innehåll |
|---|---|---|
| 1 Inkommande – hela avsnitt från Riverside | Du | Hela avsnittet (helst ljudfil, MP3/WAV) |
| 2 Mall – exempelvideo på hur det ska se ut | Du | Exempel på önskat utseende |
| 3 B-roll – videos att lägga ovanpå | Du | Videoklipp som visas medan vi pratar |
| 4 Att granska – färdiga klipp och texter | Agenten | En mapp per klipp: videofiler + `inlagg.md` |
| 5 Publicerade – flytta hit när du lagt upp | Du | Det som är publicerat |

Videofilerna i git ignoreras – de bor bara i Drive.

**Viktigt om åtkomst:** Claudes Drive-koppling ser bara filer som Claude själv
skapat och klarar max ~3 MB per fil. Därför delas mappen **Laganda Clips** med
*Alla som har länken* (Dela → Allmän åtkomst), och agenten hämtar filerna
direkt från Google med `clips/fetch_drive.py`. Färdiga klipp (6–8 MB) är för
stora för att laddas upp via kopplingen – de skickas till Artem i Claude-chatten.

## Flöde

1. Ladda upp ett helt avsnitt i mapp 1 (WAV eller MP3 från Riverside).
2. Agenten hämtar mapparna 1–3 via länken (`clips/fetch_drive.py`).
3. Agenten (Claude) transkriberar avsnittet på svenska (`clips/transcribe.py`).
4. Agenten läser utskriften och väljer 3–5 avsnitt på 30–60 s som står på
   egna ben, och skriver en plan (`plan.json`) med rubrik och inläggstexter.
5. `clips/render.py` gör ett klipp per format:
   - `9x16.mp4` – Instagram Reels
   - `4x5.mp4` – Facebook
   - `1x1.mp4` – LinkedIn och X
6. Agenten skickar klippen och `inlagg.md` i chatten. **Inget publiceras
   automatiskt** – du granskar, lägger upp själv och sparar gärna i mapp 5.

## Köra själv

```sh
pip install -r requirements.txt     # kräver även ffmpeg
python clips/fetch_drive.py <länk till mapp 1> work/avsnitt
python clips/transcribe.py work/avsnitt/<fil> work/avsnitt
# skriv work/avsnitt/plan.json (se render.py för format)
python clips/render.py work/avsnitt/plan.json --broll work/broll
```

Utseendet (färger, typsnitt, antal ord per undertextrad, hur länge varje
B-roll visas) ställs in i `config/brand.json`. Typsnitten i `fonts/` är
Google Fonts-ersättare för profilens typsnitt (OFL-licens).

Taligenkänning: KBLab:s svenska Whisper-modell (`KBLab/kb-whisper-small`),
hämtas från huggingface.co första gången.
