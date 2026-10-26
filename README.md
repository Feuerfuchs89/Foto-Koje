# Foto Koje

Schlanker Bildeditor (ein einziges Python-Skript, kein Ballast) mit Unterstützung für normale Bilder **und RAW / Canon C-RAW (CR3)**.

## Funktionen
- Öffnen: PNG, JPG, WebP, BMP, TIFF, GIF sowie RAW (CR2, CR3 inkl. C-RAW, NEF, ARW, DNG, ORF, RW2, RAF, PEF …)
- Regler: Belichtung, Helligkeit, Kontrast, Sättigung, Schärfe, Farbtemperatur, Weichzeichner (Live-Vorschau)
- Werkzeuge: Drehen, Spiegeln, Zuschneiden (Rahmen aufziehen), Größe ändern, S/W, Invertieren, Auto-Kontrast
- Rückgängig / Wiederholen (Strg+Z / Strg+Y)
- Speichern an frei gewähltem Ort: als PNG, JPG, WebP, TIFF, BMP oder im Originalformat
- RAW-Hinweis: Bearbeitete Pixel können nicht in RAW zurückgeschrieben werden. Stattdessen wird die unveränderte RAW-Datei kopiert oder das Ergebnis als TIFF/PNG/JPG exportiert.

## Start
```
pip install -r requirements.txt
python fotokoje.py
```
(Linux: ggf. `sudo apt install python3-tk`)

## Optional: als .exe bauen
```
pip install pyinstaller
pyinstaller --onefile --windowed --icon icon.ico --add-data "icon.png;." fotokoje.py
```

## Dateien
`fotokoje.py`, `icon.png`, `icon.ico`, `requirements.txt`, `README.md`

## Browser-Version (index.html)
Zusätzlich gibt es `index.html` – ohne Installation per Doppelklick oder über GitHub Pages nutzbar (Chrome/Edge empfohlen; 15 Schnellfilter mit Stärkeregler, dort ist auch die freie Ordnerwahl beim Speichern möglich). RAW/C-RAW wird dort über die in der Datei eingebettete JPEG-Vorschau geöffnet, nicht über die echten Sensordaten (dafür die Python-Version nutzen).

## Neu in der Browser-Version
Dunkel/Hell/Auto-Design, 15 Schnellfilter mit Stärkeregler, Schatten/Lichter/Schärfe, Zoom (Mausrad, Doppelklick = zurück) und Verschieben, Vorher/Nachher-Balken (◐), eigene Looks speichern, Stapelverarbeitung (🗂️), offline installierbar (PWA: `manifest.webmanifest`, `sw.js`).

## Veröffentlichen auf GitHub Pages
Alle Dateien ohne Unterordner ins Repository legen → Settings → Pages → Branch `main`, Ordner `/ (root)`.
