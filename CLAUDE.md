# Laganda Clips – instruktioner för agenten

Kommunicera på svenska. Läs README.md för översikten. Drive-mappar och id:n
finns i `config/brand.json` under `drive`.

## En körning

1. Drive-kopplingen ser INTE Artems uppladdade filer och klarar max ~3 MB.
   Hämta i stället via länk: `python clips/fetch_drive.py
   https://drive.google.com/drive/folders/<id> <målmapp>` (id:n i
   `config/brand.json` → `drive`). Mapp 1 → `work/incoming/`, mapp 2 →
   `work/template/`, mapp 3 → `work/broll/`. Kräver att mappen är delad med
   "Alla som har länken" och att miljön når drive.google.com och
   drive.usercontent.google.com.
2. Hoppa över avsnitt som redan finns i `processed.txt` i repot. Lägg till
   filnamnet där när avsnittet är klart och committa.
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
7. Skicka mp4-filerna och `inlagg.md` till Artem i chatten (SendUserFile).
   Uppladdning till Drive via kopplingen fungerar inte för filer över ~3 MB.

## Regler

- Publicera aldrig själv på sociala medier förrän Artem uttryckligen bett om det.
- Radera aldrig något i Drive. Flytta inte filer i mapp 1.
- Committa aldrig ljud/video eller modeller (se .gitignore).
- Ändringar i utseende görs i `config/brand.json` eller `render.py`.
