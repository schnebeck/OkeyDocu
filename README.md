# EasyMeasurement

Messdatenablage und Protokollerstellung für den Linux-Plasma-Desktop.

**Producer:** Thorsten Schnebeck (Urheber, Rechteinhaber und Verantwortung)

Alles dreht sich um eine Kette:

    Kunde → Anlage → Messkampagne → Messung → Messwert → Protokoll

- **Geführte Messung:** Verkabelung als interaktive Grafik, Aufbau bestätigen, beliebig viele
  Messungen. Ein Simulator liefert Zufallswerte, wenn kein Messgerät angeschlossen ist.
- **Stammdaten:** Kunden und ihre Anlagen, Maschinen und Geräte als Baum
- **Messwerte:** Zahl mit Einheit oder Text, dazu Fotos je Messung mit nummerierten
  Markierungen und der Einstufung als Hinweis oder Mangel.
- **Suchen und Filtern:** Volltext, Kunde, Anlage samt Unteranlagen, Kampagne, Messgröße,
  Bewertung, Zeitraum, Wertebereich mit Einheit (`max 1MΩ`), nur mit Foto
- **Protokolle:** aus Vorlagen, die 0, 1 oder n Messungen je Datensatz darstellen können. Die
  Vorlagen entstehen in einem grafischen Editor mit Live-Vorschau, ein Logo lässt sich importieren,
  skalieren und frei platzieren.
- **Ablage:** Abgeschlossene Kampagnen sind gesperrt. Archivierte PDFs tragen eine Prüfsumme
  und behalten die verwendete Vorlage.
- **Signatur:** PAdES mit X.509-Zertifikat aus einer PKCS#12-Datei, auch S/MIME
- **Messgeräte:** austauschbar hinter einer Abstraktionsschicht. Messwerte lassen sich auch
  ohne Gerät von Hand erfassen.

## Starten

    tools/setup-venv.sh
    .venv/bin/python -m easymeasurement

Die `.venv` ist isoliert und nutzt die festen Versionen aus `requirements.txt`. Nur PySide6 kommt
aus der Distribution (Paket `python3-pyside6`), weil es zum System-Qt passen muss, damit der
Plasma-Stil geladen wird. Daten liegen unter
`~/.local/share/EasyMeasurement`; `EASYMEASUREMENT_DATA` wählt einen anderen Ordner.

## Tests

    .venv/bin/python -m pytest

Alle Testdaten sind erfunden. Echte Geräteabrufe enthalten Kundendaten und gehören nicht in
dieses Repository.

## Fotos

Fotos werden über den Aufnahmezeitpunkt einer Messung zugeordnet. Der Zeitpunkt kommt aus den
EXIF-Daten, ersatzweise aus dem Dateinamen. Messenger entfernen EXIF-Daten: Fotos besser per USB
oder KDE Connect übertragen. Ein Foto ohne eindeutige Zuordnung bleibt als eigener Eintrag
erhalten und lässt sich suchen.

Mehr dazu in [docs/architecture.md](docs/architecture.md).

## Lizenz

GPL-3.0-or-later, siehe [LICENSES](LICENSES/GPL-3.0-or-later.txt).
