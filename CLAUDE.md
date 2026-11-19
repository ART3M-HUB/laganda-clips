# Laganda Clips – instruktioner för agenten

Kommunicera på svenska. Läs README.md för översikten. Drive-mappar och id:n
finns i `config/brand.json` under `drive`, stilen under `style`.

## Automatisk körning (schemalagd, en gång per dag)

Gör inget och svara bara kort om det inte finns något nytt avsnitt.

1. **Förbered miljön** (behövs i en ny container):
   `pip install -q -r requirements.txt` och se till att `ffmpeg` finns.
   Modellen hämtas till `models/` första gången (~470 MB).
2. **Nya avsnitt:** `python clips/new_episodes.py` listar filer i Drive-mapp 1
   som inte finns i `processed.txt`. Tom lista → klart, avsluta.
3. **Hämta avsnittet:** `python clips/fetch_drive.py
   https://drive.google.com/file/d/<id>/view work/<avsnitt>/` (avsnitt = kort
   slug, t.ex. `avsnitt-2026-11-24`). Drive-kopplingen (MCP) ser INTE Artems
   uppladdade filer och klarar max ~3 MB – använd alltid länkhämtningen. Kräver
   att mappen är delad med "Alla som har länken" och att miljön når
   drive.google.com och drive.usercontent.google.com.
4. **Kolla språket först:** transkribera de första ~3 minuterna
   (`--windows 0-180`) med `--lang sv` och läs. Är samtalet på engelska (t.ex.
   en engelsktalande gäst) används `--lang en` – den svenska modellen gör
   engelskt tal oläsligt.
   **Transkribera:** `python clips/transcribe.py work/<avsnitt>/<fil>
   work/<avsnitt> --lang <sv|en>` (kör i bakgrunden). När klippen är valda:
   kör de valda intervallen igen med `--windows` (för engelska med
   `--model Systran/faster-whisper-medium.en`) och använd `words_windows.json`
   som `words` i planen – det ger bättre undertexter.
   Engelska avsnitt: rubrik och undertexter på engelska (som talet),
   inläggstexterna på svenska.
5. **Välj 6–10 klipp** ur `transcript.txt`:
   - 20–60 s, börjar och slutar på hel mening, begripligt utan sammanhang.
   - Krok i början: tydligt påstående, konkret tips, siffra eller rolig replik.
   - Hoppa över intro, småprat, interna skämt och avslutning. Ett klipp om
     appen/tjänsten är bra om det finns (säljsidan:
     https://laganda.vercel.app/info.html).
   - Rubrik (`title`): max ~8 ord, sentence case, svensk, säger vad tittaren får.
   - Hitta aldrig på citat eller fakta. Inläggstexterna får bara påstå det som
     sägs i klippet.
6. **Skriv `work/<avsnitt>/plan.json`** (format i `clips/render.py`):
   - `start`/`end` från `words.json`: första ordets `s` − 0,12 och sista
     ordets `e` + 0,35.
   - `broll`: 10–18 löpnummer `k` ur `config/broll_tags.json`, valda efter
     vad som sägs (kategorierna beskriver innehållet). Bara k som finns där.
   - `fix`: rätta tydligt felhörda ord (engelska fackord, namn, siffror).
     Gissa inte – lämna hellre och flagga i rapporten.
   - `posts`: Instagram (kort, emojis ok, 5–8 hashtags), Facebook (lite
     längre, fråga till följarna), LinkedIn (sakligt, lärdom för tränare och
     klubbar), X (max 260 tecken).
7. **Rendera:** `python clips/render.py work/<avsnitt>/plan.json` (i bakgrunden;
   ca 3–5 min per klipp och format). Ta en bildruta ur några klipp och titta
   på den innan leverans.
8. **Leverera i chatten** med SendUserFile (`status: proactive`,
   `display: attach`): per klipp `9x16`, `4x5`, `1x1`, plus en samlad
   `inlagg_*.md`. Skriv en tabell med klipp, rubrik, längd och tid i
   avsnittet, och flagga osäkra undertexter. Uppladdning till Drive via
   kopplingen fungerar inte för filer över ~3 MB.
9. **Markera klart och spara:** `python clips/new_episodes.py --done "<filnamn>"`,
   kopiera planen till `plans/<avsnitt>.json`, committa och pusha.

## Regler

- Publicera aldrig själv på sociala medier förrän Artem uttryckligen bett om det.
- Radera, flytta eller ändra aldrig något i Drive.
- Committa aldrig ljud, video eller modeller (se .gitignore).
- B-roll visar barn och ungdomar – använd bara klipp ur `broll_tags.json`.
- Ändringar i utseende görs i `config/brand.json` eller `clips/render.py`.
  Nuvarande stil är godkänd av Artem: fet seriff (Fraunces), rubrik på svart
  rundad platta, undertexter med svart kontur och klarblå (#009dfd) platta
  bakom ordet som sägs.
