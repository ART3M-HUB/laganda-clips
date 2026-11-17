# Laganda Clips – instruktioner för agenten

Kommunicera på svenska. Läs README.md för översikten. Drive-mappar och id:n
finns i `config/brand.json` under `drive`.

## En körning

1. Lista filer i Drive-mapp 1 (`drive.incoming`). Hoppa över avsnitt som redan
   har en mapp i mapp 4 eller 5 med samma avsnittsnamn.
2. Ladda ner avsnittet till `work/<avsnitt>/` och B-roll från mapp 3 till
   `work/broll/`.
3. `python clips/transcribe.py work/<avsnitt>/<fil> work/<avsnitt>`.
4. Läs `transcript.txt` och välj 3–5 klipp:
   - 30–60 s, börjar och slutar på hel mening, begripligt utan sammanhang.
   - Ett tydligt påstående, tips, siffra eller rolig replik i början (krok).
   - Rubrik max ~6 ord. Hitta aldrig på citat eller fakta som inte sägs.
5. Skriv `work/<avsnitt>/plan.json` med inläggstexter per kanal:
   Instagram (kort, emojis ok, 5–8 hashtags), Facebook (lite längre, fråga
   till följarna), LinkedIn (sakligt, lärdom för tränare/klubbar), X (max 260
   tecken). Alla på svenska.
6. `python clips/render.py work/<avsnitt>/plan.json`. Titta på en bildruta
   per format innan uppladdning.
7. Skapa en undermapp i mapp 4 per klipp: `<avsnitt> – <id> <rubrik>` och
   ladda upp alla mp4-filer och `inlagg.md`.

## Regler

- Publicera aldrig själv på sociala medier förrän Artem uttryckligen bett om det.
- Radera aldrig något i Drive. Flytta inte filer i mapp 1.
- Committa aldrig ljud/video eller modeller (se .gitignore).
- Ändringar i utseende görs i `config/brand.json` eller `render.py`.
