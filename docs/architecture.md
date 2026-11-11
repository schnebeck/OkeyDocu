# Architektur

## Datenmodell

    customers ─< assets (Baum aus Elementen, Typ aus asset_kinds) ─ kind_features
                   └─< campaigns ─< measurements ─< measured_values
                          └─< reports

| Begriff | Bedeutung |
|---|---|
| Kampagne | Ein Prüftermin an einer Anlage. Sie ist die Einheit, aus der ein Protokoll entsteht. |
| Messung | Ein Vorgang mit Zeitpunkt, Funktion und Bewertung. Sie hat 0 bis n Messwerte. |
| Messwert | `kind` ist `number`, `text` oder `photo`. |

Zahlen werden doppelt gespeichert: `raw` ist der Text des Messgeräts und wird unverändert
gedruckt, `base_value` und `base_unit` dienen zum Vergleichen und Filtern (`2.05MΩ` wird
2050000 Ω). Ein Wertefilter bleibt innerhalb seiner Einheit.

Jede Gerätemessung behält ihre Herkunft: Datensatz des Geräts (`raw_data`), Seriennummer,
Firmware, Eingangszeit am PC mit Zeitzone. Die GUID eines Geräts kommt datenbankweit nur einmal vor.

Das Programm migriert keine Datenbanken. Es legt eine neue Datenbank im aktuellen Schema an und
weist jede andere Schemaversion beim Start ab. Eine nötige Umstellung läuft vorher mit einem externen
Werkzeug.

Ein Foto hängt als Messwert an der Messung, zu der es gehört. Lässt es sich nicht eindeutig
zuordnen, wird es eine eigene Messung mit der Funktion `foto`. Solche Fotos fließen nicht in das
Gesamtergebnis ein.

## Struktur

Die Struktur eines Kunden ist ein Baum beliebiger Tiefe (`assets`), frei verschachtelbar wie bei
IZYTRON. Die Typen der Elemente stehen in `asset_kinds`, ihre Merkmale in `kind_features`; beides ist
unter Einstellungen → Strukturtypen änderbar (`ui/kinds_page.py`). Mitgeliefert werden die Typen aus
`data/kinds.yaml`. Jeder Typ nennt seinen IZYTRON-Typcode für den Import und ein Prüfintervall. Merkmalswerte liegen
gesammelt am Element (`features_json`); leere werden nicht gespeichert und nirgends gezeigt. Wird ein
Typ gelöscht, bekommen seine Elemente einen Ersatztyp, ihre Werte bleiben unsichtbar erhalten.
Im Protokoll übersetzen die Sprachdateien Typen und Merkmale über ihren Schlüssel (`kinds`,
`features`), nicht über den deutschen Namen: „Leiter“ ist als Typ eine Steigleiter, im Messwert ein
Leiter. Selbst angelegte Typen und Merkmale bleiben deutsch.

Eine Messung hängt an einem Element (`asset_id`), ihr Ort im Protokoll ist der Pfad dorthin. Umbuchen,
Umbenennen und Verschieben schreiben diesen Pfad in offenen Kampagnen nach (`campaign/structure.py`);
versiegelte Messungen bleiben, wo sie sind, und ein Element, an dem sie hängen, lässt sich nicht
löschen. Ein Push des Geräts bringt keinen Ort mit, er landet beim im Baum gewählten Element. Ein Abruf
aus dem Gerätespeicher bringt den Gerätepfad mit; fehlende Elemente entstehen dabei als Messpunkte.

Fällig wird eine Prüfung, wenn seit dem Abschluss der letzten Kampagne an einem Element dessen
Intervall (eigenes oder das des Typs) abgelaufen ist, 30 Tage im Voraus. Eine abgeschlossene Kampagne
mit Mängeln wartet auf eine Nachprüfung, bis eine Kampagne über `follows_id` auf sie verweist
(`campaign/due.py`). Beides zeigt die Übersicht unter „Fällig“.

## Was an einer Messung feststeht

Messwert, Einheit und Zeitstempel sind endgültig. Das erzwingen Datenbank-Trigger, nicht nur die
Oberfläche. Der Versatz der Geräteuhr darf `local_time` neu berechnen, `device_time` bleibt.

Überschreibbar sind Funktion, Messort, Prüfer, Kommentar und Bewertung, je Messwert Bezeichnung,
Grenzen und Bewertung (`EDITABLE_FIELDS`). Texte zu korrigieren und doppelte Messungen zu löschen ist
Alltag und hinterlässt keinen Vermerk. Von einer gelöschten Messung bleibt nur die Kennung, damit sie
beim Abruf nicht zurückkommt. Änderungen an Funktion, Bewertung und Grenzwerten stehen dagegen mit
altem und neuem Wert in `measurement_log`, das sich nur fortschreiben lässt. Im Protokoll sind
solche Messungen als „geändert" und von Hand erfasste als „manuell" gekennzeichnet.

## Offen und abgeschlossen

Eine Kampagne ist offen, auch nach einem Import, und lässt sich überarbeiten. Ein Protokoll entsteht
erst aus einer abgeschlossenen Kampagne, also spätestens dann ist sie geschlossen. Vorher zeigt ein
Entwurf (`drafts/entwurf.pdf`, mit Hinweis „ENTWURF“, nicht archiviert), wie es aussähe.
„Bestätigen“ schließt ab, versiegelt, legt das PDF ab und signiert in einem Schritt. Das Zertifikat
wird vorher geprüft; scheitert danach etwas, bleibt der Datensatz versiegelt und das Protokoll lässt
sich unter „Protokolle“ nachholen.

Der Abschluss versiegelt den Datensatz (`campaign/seal.py`): Über alle Inhalte wird eine SHA-256-
Summe gebildet und mit einem Schlüssel aus KWallet beglaubigt (HMAC). Jedes Siegel enthält das
vorherige. Stammdaten gehören nicht dazu, ein umbenannter Kunde ist keine Manipulation. Vor jedem
Protokoll und jeder Signatur wird geprüft; ein veränderter Datensatz wird abgewiesen.

Grenzen: Wer den Schlüssel hat, kann ein Siegel fälschen. Das Verschwinden der neuesten Kampagne
fällt in der Kette nicht auf. Deshalb steht das Siegel im Protokoll: Ein signiertes Protokoll
verankert es außerhalb dieses Rechners. Geht der Schlüssel verloren, lassen sich die Daten weiter
gegen die Summe prüfen, die Echtheit aber nicht mehr.

## Abgeschlossene Kampagnen

Datenbank-Trigger verhindern jede Änderung an Messungen, Messwerten und Schritten einer
abgeschlossenen Kampagne, auch am Programm vorbei. Protokolle entstehen nur aus abgeschlossenen
Kampagnen. Eine Signatur erzeugt einen neuen Archiveintrag, das Original bleibt erhalten.

## Das 0/1/n-Problem in Vorlagen

Eine Vorlage ist eine Liste von Blöcken. Ein `measurements`-Block legt nicht fest, wie viele
Messungen es gibt, sondern beschreibt drei Darstellungen, zwischen denen die Daten entscheiden:

| Daten | Darstellung |
|---|---|
| 0 | Satz mit Begründung, oder der Block entfällt (`none: {hide: true}`) |
| 1 | Formular mit Bezeichnung und Wert |
| n | Tabelle mit Min- und Max-Zeile |

Messungen verschiedener Funktionen teilen sich keine Tabelle, weil ihre Spalten nicht
zusammenpassen; jede Funktion wird für sich gezählt. Der Min/Max-Vergleich läuft über
`base_value`, angezeigt wird der Originaltext.

Ein Messblock nennt zuerst, was seine Messungen gemeinsam haben: Einstellungen des Messgeräts,
Messbedingungen wie den R_LO-Offset und Grenzwerte. Die Tabelle darunter zeigt je Messung nur, was
sich unterscheidet, und was gemessen wurde (`reporting/measurement_table.py`). Werte, die nur bei
nicht bestandener Messung zählen, bekommen nur dann eine Spalte. Messwerte stehen als Zahl und
Einheit mit Vorsatz in Tausenderstufen (p, n, µ, m, k, M, G, T), etwa `220 mΩ`; dabei wird nur
das Komma verschoben, nie gerundet. Formelzeichen sind kursiv mit aufrechtem, tiefgestelltem Index.

Bemerkungen gehören in die Zeile ihrer Messung: Kommentar, Notizen, Anhänge und Verweise auf Fotos
stehen untereinander in der Spalte „Bemerkung“. Fotos sind durch das Protokoll nummeriert (`[3]`);
die Bemerkung verweist darauf, mit Hinweisnummer, wenn das Foto markiert ist („siehe Hinweis 1 in
[3]“). Das PDF setzt jedes Foto wie eine Fußnote auf die Seite der Zeile, die es nennt, mit der
Liste der Hinweise darunter: höchstens drei nebeneinander und zwei Reihen je Seite
(`reporting/pdf_photos.py`).

Der Block `structure` ordnet die Messungen nach dem Strukturbaum der Anlage. Mit `order: place`
ist jedes Element mit Messungen ein Abschnitt mit seinen Merkmalen und darin je Messgröße ein
Block; mit `order: function` steht jede Messgröße einmal, mit dem, was all ihre Elemente teilen,
und darunter je Element nur noch, was davon abweicht. Schritte eines Plans ohne Messung folgen mit
ihrer Begründung. Die Standardvorlage verwendet `order: place`.

Am Fuß stehen Ort, Datum und Name schon auf den Linien (`fills` des Blocks `signature`): der Sitz
der eigenen Firma, das Erstellungsdatum und der Prüfer, dessen hinterlegte Unterschrift den Namen
ersetzt. Die digitale Signatur kommt danach.

`resolve()` wandelt Vorlage und Daten in Dokumentknoten um, `render_pdf()` macht daraus das PDF.
Platzhalter laufen in einer Jinja-Sandbox, damit eine Vorlage nicht an Programminterna kommt.

Die Protokollsprache ist unabhängig von der Programmsprache und wird mit dem Protokoll gespeichert.
`reporting/language.py` hält sie während der Erzeugung; jeder Text wird über sein deutsches
Original in `data/languages/<code>.yaml` nachgeschlagen, Fehlendes bleibt deutsch. Messwerte
werden nie gerundet, nur Dezimalzeichen und Abstand folgen der Sprache. Notizen und Anhänge an
Messungen stehen bei ihnen, solche an Orten im Block `attachments`.

Das Gesamtergebnis übertreibt nicht: Ein ausgelassener oder leerer Schritt ergibt „Nicht
vollständig geprüft“, nie „Bestanden“.

## Sprachen

Alle Texte stehen englisch im Code und werden beim Anzeigen nachgeschlagen: `tr("Serial number
{serial}", serial=…)`, gezählt mit `plural()`, Modulkonstanten mit `N_()` markiert und dort übersetzt,
wo sie erscheinen (`easymeasurement/l10n/`). Jede Sprache hat einen Ordner unter `data/languages/<code>/`:
`language.yaml` mit Namen und Formaten für Datum, Zeit und Dezimalzeichen, daneben Katalogdateien je
Bereich mit `texts` (Englisch → Sprache) und `contexts` für ein englisches Wort, das zwei Übersetzungen
braucht. Ein Text darf in mehreren Dateien stehen, aber nur mit derselben Übersetzung.

Die Programmsprache wird unter „Einstellungen → Sprache“ gewählt und gilt ab dem nächsten Start;
„Wie das System“ übernimmt bei jedem Start die Systemsprache. Der Hinweis darunter erscheint in der
gerade gewählten Sprache. Angeboten werden nur Sprachen mit `program: true`; die übrigen dienen
Protokollen. `speaking()` setzt für einen Thread eine andere Sprache, etwa für ein Protokoll, dessen
Sprache mit der Programmsprache vorbelegt ist.

Gespeicherte Wörter (Schritttitel, Vorlagenzeilen, Ergebnisnamen) können in jeder Katalogsprache
geschrieben sein. `in_language()` erkennt sie über die Kataloge wieder und gibt sie in der aktuellen
Sprache aus; Unbekanntes bleibt, wie es ist. Diese Wörter stehen in `stored*.yaml`. So liest sich eine
deutsch geschriebene Vorlage auch als englisches Protokoll. Die mitgelieferte Standardvorlage ist
englisch und wird beim Anlegen der Datenbank in der Programmsprache abgelegt.

Strukturtypen und Merkmale kommen englisch aus `data/kinds.yaml`. Beim Lesen aus der Datenbank
erscheinen sie in der aktuellen Sprache, solange ihr Name einer der mitgelieferten ist, in welcher
Sprache auch immer; erkannt wird er über den Schlüssel, damit „Leiter“ die Leiter bleibt. Ein
umbenannter Typ behält seinen Namen.

Mitgelieferte Messpläne (`data/plans/`) und die Messanleitungen der Treiber sind englisch. Beim
Laden übersetzt `campaign/plan_language.py` ihre Texte (Titel, Einstellungen, Warnungen, Schritte,
Quelle, Anschlussbild) in die Programmsprache; die deutschen Fassungen stehen in
`data/languages/de/instructions.yaml`. Schlüssel, Funktionen, Buchsen und Klemmen-IDs bleiben
unübersetzt. Ein selbst geschriebener Plan bleibt in der Sprache, in der er geschrieben wurde.
Eine Kampagne speichert ihre Schritte in der Sprache beim Start; Protokolle in einer anderen
Sprache finden den Titel über die Kataloge wieder.

`tests/test_l10n.py` verlangt für jeden markierten Text und jedes Wort der mitgelieferten Pläne und
Anleitungen einen deutschen Eintrag mit denselben Platzhaltern und meldet Einträge, die nichts
benutzt.

## Messgeräte-Abstraktion

Drei Schichten: Treiber, Mapping, Vokabular. Ausführlich und mit dem Beispiel eines
Schallpegelmessers in [hardware-abstraction.md](hardware-abstraction.md).

`devices/base.py` definiert `MeterDriver`: `identify()`, `read_clock()`, `read_measurements()`
und optional `subscribe_live()`. Die Schnittstelle liest nur. Sie kann weder eine Messung
starten noch Geräteeinstellungen ändern, denn das tut der Prüfer am Gerät. Ein neues Messgerät
ist ein neuer Treiber in `devices/registry.py`; die Anwendung bleibt unverändert. Die Codes des
Geräts kennt nur sein Mapping (`devices/profitest_prime/mapping.py`); Funktionen, Ergebnisse,
Größen, Ergebniswörter und Einstellungen heißen in der App nach ihrem Vokabular
(`easymeasurement/vocabulary/`, `data/vocabulary/*.yaml`).

Beim Start einer Kampagne mit Gerät werden die Geräteidentität, der Uhrenversatz und die schon
vorhandenen Messungen festgehalten. Abgerufen wird danach nur, was neu ist, mit korrigierter Zeit.

### PROFITEST PRIME

USB-CDC mit 115200 8N1 oder Bluetooth über einen RFCOMM-Socket (Kanal 1). Der Prüfer wählt nur das
Gerät, Ports und Adressen zeigt die App nicht. `discovery.py` findet es über die USB-Kennung
(1CD7:0117) und unter den gekoppelten Geräten von BlueZ; ein gekoppeltes Gerät steht auch dann in der
Liste, wenn es gerade aus ist. Intern heißt der Port `/dev/ttyACM0` oder `bt:<Adresse>`.

Einmalig richtet der Dialog unter „Einstellungen" die Bluetooth-Kopplung ein. `pairing.py` steuert dafür
`bluetoothctl` mit einem Agenten für die PIN. Die PIN wird nicht gespeichert.

Eine Kampagne startet in jeder Schalterstellung, in der sich die Uhr stellen lässt. Der
Gerätespeicher wird dabei nicht gelesen, weil das per Bluetooth 15 s dauert und die Stellung Setup braucht.
Stattdessen trennt die Zeit Alt und Neu: Neu ist, was ab `stored_since` liegt.

Gerätezugriffe laufen über `run_busy()` außerhalb des GUI-Threads. Die Datenbankverbindung gehört
dem GUI-Thread, deshalb lesen die Worker nur vom Gerät und das Ablegen folgt danach.

**Gerätetexte:** Messungen behalten die TS-Codes, die das Gerät sendet, für Messgrößen und
Einstellungen, wie IZYTRON auch (dort mit Vorsatz `PROFITEST_`). Die Wörter dazu stehen in der
Übersetzungsdatei des Geräts (`DATABASEXML:GET:TRANSLATIONFILE`, 12 Sprachen, etwa eine Minute per
Bluetooth). Beim Einrichten über „Einstellungen → Messgeräte“, über Bluetooth nach dem Koppeln oder per
USB mit „Einrichten …“, prüft das Programm den Stand und überträgt, was fehlt
(`ui/instrument_prepare.py`, Tabellen `device_texts` und `device_text_sets`). Die Texte gelten für die
Firmware, mit der sie gelesen wurden; findet ein Kampagnenstart eine andere Firmware, kommt derselbe
Abgleich mit Wartefenster. Angezeigt werden Einstellungen in Worten, etwa „RLO - Polung: Automatische
Umpolung“; ohne Texte bleibt der Code. Der IZYTRON-Import schlüsselt Einstellungen ebenso nach Code,
Leiterbezüge neutral als `conductor`. Die Herstellertexte gehören zu den lokalen Daten, nie ins Repo.

**Test und Geräteprotokoll:** „Einstellungen → Messgeräte → Testen …“ verbindet kurz und prüft
Verbindung, Gerätekennung, Kalibrierung, Uhr, Drehrad, An- und Abmelden von Push/Print und die
Gerätetexte (`devices/instrument_check.py`, `ui/instrument_test.py`). Gestellt und gemessen wird dabei
nichts; eine abweichende Uhr oder eine überfällige Kalibrierung ist ein Hinweis, kein Fehler. Jeder Lauf
bleibt in `instrument_tests`. „Geräteprotokoll …“ zeigt je Seriennummer den Lebenslauf aus diesen Läufen
und den Kampagnen, in denen das Gerät benutzt wurde, mit Firmware, Kalibrierung und der Abweichung der
Uhr, wie sie vor dem Stellen gefunden wurde (`campaign/instrument_history.py`, `ui/instrument_log.py`).
Das Protokoll braucht keine Verbindung.

`transport.py` führt eine feste Liste erlaubter Befehle: Lesebefehle, die drei Befehle des
Push-Modus und die Abfrage des Drehschalters. Alles andere wird vor dem Senden abgewiesen, weil Schreibbefehle den Geräteinhalt
ersetzen und ein unbekannter Befehl eine Messung mit echter Prüfspannung auslösen könnte.

Ein Lesethread besitzt die Verbindung und trennt Antworten von unaufgeforderten Events. Befehle
laufen einzeln, Antworten werden über das Befehlsecho zugeordnet. Befehle ohne XML-Form antworten mit
einer Textzeile ohne Echo.

**Drehschalter:** `read_selector()` liefert Stellung und mögliche Funktionen. Gefragt wird nur an
festen Punkten: beim Einrichten eines Schritts und auf Knopfdruck, nie laufend und nie während eines
Schritts im Messen. Das Gerät schreibt ein Event stückweise, und nichts hält eine Antwort davon ab,
mitten hineinzugeraten.

**Push/Print:** `subscribe_live()` schaltet den Modus ein. Je Speichern-Druck kommt ein Event, die
Messung geht zuerst an den Callback, danach die Quittung. Ein Push bleibt nicht im Gerätespeicher,
der Empfänger hat also die einzige Kopie. Deshalb wird auch ein unlesbarer Datensatz unverändert
als Funktion `unreadable` ausgeliefert. Der Treiber verlässt den Modus beim Schließen, beim
Programmende und nach einem Absturz beim nächsten Verbinden. Reißt die Verbindung ab, meldet er das
und verbindet sich neu, aber nur mit demselben Gerät. Die Callbacks laufen auf einem eigenen Thread.
Abmelden kann sich nur die Schnittstelle, die sich angemeldet hat. Gelingt das nicht oder kommt die
Verbindung über einen anderen Weg zurück, bittet die App, das Gerät aus- und wieder einzuschalten.

- Gespeicherte Messungen werden auf Anforderung abgerufen, nicht fortlaufend: Das Gerät zeigt
  währenddessen einen eigenen Bildschirm. Es gibt sie nur mit dem Drehschalter auf Setup frei,
  sonst kommt Fehler 402.
- Die Gerätecodes (`TSnnnn`) in `mapping.py` folgen der Übersetzungsdatei des Geräts. Unbekannte
  Codes bleiben als Code erhalten und werden beim Anzeigen aus den Gerätetexten benannt.
- Das Gerät hat nur eine Spannungsfunktion. Bringt sie Außenleiterspannungen mit, gilt sie als
  Drehfeldmessung `u3`. Das Drehfeld selbst steht in `VERIFICATION` und wird als neutrales Wort
  gespeichert (`right`, `left`), damit Protokolle in jeder Sprache möglich bleiben.
- Das Gerät schreibt das Ohm-Zeichen U+2126, nicht das griechische Omega. `Quantity.parse`
  vereinheitlicht die Einheit, `raw` behält das Original.
- `passed` zählt nur neben einem Grenzwert. Reine Informationswerte wie die Netzspannung kommen
  auch in bestandenen Messungen mit `passed="false"`.

## Import aus IZYTRON

`importing/izytron.py` liest eine Kopie der IZYTRON-Datenbank nur lesend und legt einen Prüftag als
abgeschlossene Kampagne an, mit Anlagenbaum, Messungen und Sichtprüfung. Den Versatz der Geräteuhr
an jenem Tag nennt der Aufruf, er hängt vom Datum ab. Zeiten aus Sichtprüfungen sind schon Ortszeit.
Abteilung und Ansprechpartner kommen mit: die Abteilung der Anlage (`Abstract_Device.Department`),
sonst die des Ansprechpartners, und der erste aktive Ansprechpartner des Kunden (`Contact`) mit
Telefon, ersatzweise Mobilnummer, und E-Mail. Die Kostenstelle, die IZYTRON je Prüfobjekt führt,
gehört dem Kunden; sie wird nicht übernommen, weil die Kostenstelle einer Kampagne die eigene ist.

    python -m easymeasurement.importing.izytron KOPIE.sqlite --offset -120

## Geräteuhr

Die Uhr des Messgeräts hat keine Zeitzone, keine Sommerzeit und geht etwa 35 s im Monat nach.
Deshalb stellt `CampaignService.start()` sie vor jeder Kampagne auf die Laptopzeit, ohne Rückfrage.
Das Ziel ist, dass es keinen Versatz gibt. Die Laptopzeit muss dafür stimmen, also per NTP laufen.

Das Stellen wird nachgeprüft: Bleibt eine Abweichung ab 3 s, startet die Kampagne nicht.

Im Normalfall gibt es deshalb keinen Versatz, und die Oberfläche zeigt nichts zur Uhr: Die
Statusanzeige erscheint nur bei ungeprüfter oder abweichender Uhr, die Protokollzeile „Geräteuhr“
nur, wenn ein Versatz Zeiten tatsächlich korrigiert hat. „Messgerät → Uhr stellen …“ prüft und stellt
nach Rückfrage, in jeder Stellung des Drehrads. Ein Push bleibt nicht im Gerätespeicher; lief die
Verbindung seit dem Start der Kampagne ohne Unterbrechung, liegt dort nichts mit der alten Zeit, und
die Uhr wird direkt gestellt. Nach einem Abbruch, einer Pause oder einem Neustart des Programms holt
sie vorher ab, was im Gerät gespeichert ist; dieser Abruf braucht die Stellung Setup. Der Versatz bleibt als Absicherung erhalten. `clock_checks` hält jede Prüfung fest, jede Messung
speichert ihren Versatz (`clock_offset_s`) neben `device_time` und `local_time`. Gebraucht wird er
für Geräte ohne stellbare Uhr, bei einer Abweichung während der Kampagne und für Messungen eines
früheren Tages, deren Versatz sich von Hand angeben lässt. Wird die Uhr während einer Kampagne
gestellt, fragt die App vorher und holt erst die Messungen vom Gerät, die noch die alte Zeit tragen.

## Messkampagne

Das Hauptfenster ist nach der Arbeit geordnet, nicht nach Datenarten. In der Mitte steht die
gewählte Kampagne (`ui/campaign_page.py`) mit ihren Messwerten, rechts einklappbar Ort, Messplan,
gewählte Messung, Fotos und Protokolle (`ui/side_panel.py`). Bereiche ohne Inhalt schrumpfen dort
auf eine graue Zeile, die sagt, was hier erscheinen würde; nur offene Bereiche mit Inhalt bekommen
freie Höhe.

Die Liste aller Kampagnen (`ui/campaign_list.py`) liegt nicht dauerhaft neben der Arbeit. Sie fährt
als Schublade (`ui/edge_drawer.py`) über den Inhalt, sobald die Maus den linken Fensterrand
berührt, und verschwindet wieder, wenn die Maus sie verlässt; F9 klappt sie ebenso aus. Im
maximierten Fenster genügt es, die Maus an den Bildschirmrand zu schieben. Die Maus wird dafür
regelmäßig abgefragt, nicht verfolgt, damit kein Widget seine Bewegungen melden muss. „Ansicht →
Kampagnenliste anheften“ stellt sie fest neben die Seiten; ihre Breite bleibt dann über
den Neustart erhalten. Zur Übersicht führt der Knopf mit dem Haus vor dem Titel.

Links neben den Messwerten steht die Struktur der Anlage wie Ordner im Dateimanager
(`ui/structure_tree.py`): Zeilen der Tabelle auf ein Element ziehen bucht sie um, Kontextmenü, F2,
Entf und Einfg arbeiten am Baum. Ohne Maus bucht „Verschieben nach …“ im Kontextmenü einer Zeile
(`ui/move_overlay.py`). Die Zahl je Element ist „diese Prüfung / letzte Prüfung“. Baum und Tabelle
stehen in einem gezeichneten Rahmen (`ui/board.py`): oben über die ganze Breite die Zeile mit dem,
was alle Zeilen gemeinsam haben, und der Anzahl, darunter je eine Werkzeugleiste gleicher Höhe,
dann die Kopfzeilen von Baum und Tabelle auf einer Linie. Die Werkzeugleiste der Tabelle hält nur
„Von Hand …“ und ein Filterfeld; Bearbeiten, Foto, Verschieben und Löschen einer Zeile stehen in
ihrem Kontextmenü und auf F2 und Entf, so steht nichts dauerhaft ausgegraut im Bild. Erklärende
Sätze stehen als Tooltip: am Kopf „Struktur“ und am Hinweis über dem Rahmen, dessen fetter Teil
sichtbar bleibt. Zwischen den Hauptblöcken des Fensters liegen 8 px Fensterhintergrund; eine
gespeicherte Splitter-Stellung ändert daran nichts.

Messfunktion, Messung und Prüfablauf sind drei Ebenen. Die Messfunktion sagt, was gemessen wird
(RISO, RLO). Eine Messung ist ein Ergebnis, ein Messwert oder die Antwort auf eine Frage. Ein
Prüfablauf (Tabelle `runs`, `campaign/runs.py`) ist eine benannte Folge solcher Schritte, etwa eine
Sichtprüfung nach Fragenkatalog: Die Messung zeigt mit `run_id` auf ihn und nennt in `step_name`
ihren Schritt („Zugänglichkeit“). Der IZYTRON-Import legt für jede am PC erfasste Prüfung einen
Prüfablauf an, Messungen vom Gerät bleiben einzeln. In der Tabelle steht ein Prüfablauf als eine
Zeile mit Name, Zahl der Schritte und Mängeln (`ui/measurement_runs.py`); ein Klick auf die Zeit
klappt die Schritte darunter auf. Beim Sortieren bleiben sie unter ihrem Kopf, gleich nach welcher
Spalte und in welcher Richtung. Wer die Zeile verschiebt, verschiebt alle Schritte. Im Siegel
stehen Prüfablauf und Schrittname nur, wo es sie gibt, sodass ältere Siegel gültig bleiben.

Die Oberfläche spricht von Messungen und Prüfungen, nicht von Funktionen: Gemessen werden
Messgrößen mit Wert, Einheit und Grenzen, zusammen bewertet. Die Spalte „Bezeichnung“ nennt die
Messgröße (RISO) oder bei einer Prüfung den Schritt (Zugänglichkeit). Intern bleibt der Schlüssel
`function`, weil Gerät und Protokoll nach ihm unterscheiden.

Eine Wiederholungsprüfung (`campaign/repeat.py`, `campaign/repeat_checks.py`) macht aus der letzten
bestätigten Kampagne derselben Anlage eine Liste offener Punkte. Sie liegen als Schritte mit dem
Plan-Schlüssel `repeat` in der Kampagne und tragen Element, Bezeichnung, Grenzen und Einstellungen
der damaligen Messung, deren Herkunft, Hinweis und Bemerkung, aber keinen Messwert. Die Liste wird
in beliebiger Reihenfolge gefüllt, es gibt keinen geführten Ablauf: Jede Messung, die ankommt, nach
Push&Print, von Hand oder durch Umbuchen, nimmt den offenen Punkt am selben Element mit derselben
Bezeichnung; mehrere solche Punkte trennt der Leiter (L1-PE, …). Weicht eine Grenze oder Einstellung
vom letzten Mal ab, verlangt das Bestätigen eine Begründung; das Programm stellt am Gerät nichts ein,
es prüft nur, was ankam. Ein Punkt lässt sich mit Begründung auslassen. Bestätigt werden kann, sobald
kein Punkt mehr offen ist. Offene Punkte stehen grau in der Tabelle (`ui/campaign_points.py`), der
Strukturbaum zeigt mit „jetzt / letztes Mal“, wo noch etwas fehlt. Gewählt zeigt ein Punkt in der
Seitenleiste (`ui/repeat_point.py`), was zu messen ist, den Hinweis vom letzten Mal zum Übernehmen,
Bearbeiten oder Verwerfen, die Bemerkung von damals und die Fotos der damaligen Messung; neue
Messwerte landen dann bei seinem Element. Unter einer Messung, die einen Punkt genommen hat, stehen
erst danach die Werte vom letzten Mal, mit Hinweis bei deutlicher Änderung (`ui/repeat_compare.py`).

Jede Messung hat neben der Bemerkung, die im Protokoll steht, einen Hinweis zur Durchführung. Er
bleibt intern und kommt bei der nächsten Wiederholung als Hinweis zum Punkt wieder.

In der Messung-Box steht statt eines langen Pfades das gebuchte Element mit Symbol, darüber klein
und von links gekürzt der Weg dorthin (`ui/place_line.py`). Der Stift daneben bucht die Messung um,
der Name zeigt das Element im Baum. Nur eine Messung ohne Element zeigt den freien Messort-Text.

Overlays, die etwas ändern, haben „Übernehmen“ und „Abbrechen“; erst „Übernehmen“ speichert. So
auch die Eigenschaften eines Elements, deren Formular in den Stammdaten dagegen jedes fertige Feld
gleich ablegt. Listen, in denen jede Änderung ihren eigenen Dialog hat, schließen mit „Zurück“.

Unter den Knöpfen im Kopf steht, was bis zur Bestätigung bleibt (`ui/campaign_checks.py`):
Messungen ohne Ort, Mängel und offene Punkte, oder „bereit zum Bestätigen“. „ohne Ort“ springt zu
diesen Messungen, „Mängel“ von Mangel zu Mangel; die offenen Punkte nennt der Tooltip.

Die Spalten der Messwerttabelle verwaltet `ui/table_columns.py`: Ziehen an der Überschrift ordnet
sie an, ein Klick sortiert. Das Kontextmenü der Überschrift sortiert nach der angeklickten Spalte
und blendet Spalten ein und aus. Zeit, Fotozahl und Messwert sortieren nach ihrem Wert statt nach
dem Text, Messwerte erst nach Funktion, dann nach Größe. Eine Spalte, deren Wert in allen Zeilen
gleich ist, weicht der Zeile über der Tabelle, solange „Gleiche Werte über der Tabelle nennen“ an
ist; von Hand ausgeblendete Spalten bleiben in jedem Fall weg. Anordnung, Sortierung und Auswahl
gelten je Ansicht und bleiben für den nächsten Start. Jede Zeile beginnt mit einem Zeichen für ihre
Bewertung (`ui/verdict_marks.py`), das sich in Form und Farbe unterscheidet, auch wenn die Spalte
„Bewertung“ als gemeinsamer Wert oben steht. Bei Prüffragen steht die Antwort vor der Frage
(`ui/measurement_cells.py`), etwa „nein – Sind vollständige Schaltungsunterlagen vorhanden?“.

Mit Messplan stehen über den Messwerten Anschlussbild und Anleitung des Schritts, ohne Plan nur der
Hinweis auf das, was als Nächstes zu tun ist. Die Anleitung zur eingestellten Messfunktion holt ohne
Plan „Hilfe → Anleitung zur Messung“ (F1). Verbindung, Geräteuhr und Stand der Kampagne stehen in
der Statusleiste, also immer im Blick.

Ohne gewählte Kampagne steht in der Mitte die Übersicht (`ui/dashboard.py`): offene und
abgeschlossene Messungen getrennt als Karten mit ihrem nächsten Schritt, eine Suche über alle und
Kacheln zu Stammdaten, Messplänen, Vorlagen, Archiv, Benutzern und Messgerät. Die Reihenfolge folgt
den Daten (Beginn, letzte Messung, Abschluss, letztes Protokoll); die Kampagne, für die gerade
gemessen wird, steht immer vorn. Das Programm startet dort, „Übersicht“ (Alt+Pos1) führt zurück,
ohne eine laufende Messung zu unterbrechen.

Titel und Anlage einer offenen Kampagne ändert „Kampagne bearbeiten …“ (`ui/campaign_edit.py`). Die
Anlage darf nur wechseln, wenn danach keine Messung und keine Datei an einem Ort außerhalb der neuen
Anlage hängt (`misplaced` in `campaign/editing.py`); zur übergeordneten Anlage geht es also immer.
Ein Rechtsklick in der Kampagnenliste bietet an, was mit der Kampagne gerade möglich ist.
Eine Kampagne wird nach Rückfrage gelöscht; ihr Ordner mit Fotos, Dateien und Protokollen kommt
in den Papierkorb. Bei einer versiegelten bleibt ein Eintrag in `deleted_campaigns` mit ihrem Siegel
und einem HMAC aus demselben Schlüssel. Die Siegelprüfung der nächsten Kampagne erkennt ihn an. Der
Trigger `campaign_no_delete` lässt eine versiegelte Kampagne nur mit diesem Eintrag gehen, wer am
Programm vorbei löscht, bricht also weiter die Kette.
Das Änderungsprotokoll bleibt beim Löschen stehen; da SQLite IDs gelöschter Zeilen neu vergibt,
gehört ein Eintrag nur zu der Messung, deren `device_uid` und Kampagne er trägt.

Was nicht zur einzelnen Kampagne gehört, öffnet ein eigenes Fenster neben ihr: Stammdaten, Vorlagen,
Protokollarchiv und die Suche über alle Messwerte. Knöpfe und Menüs teilen sich dieselben `QAction`,
damit sie nie etwas Unterschiedliches anbieten.

Fenstergrößen, Trennlinien, eingeklappte Bereiche und ausgeblendete Leisten bleiben über einen
Neustart erhalten (`ui/view_memory.py`). Trennlinien werden beim Ziehen gespeichert, nicht beim
Beenden: Dann ist etwa der Bereich des geführten Schritts oft gar nicht sichtbar und käme ohne Platz
zurück.

**Ansehen und Messen sind getrennt.** Ein Klick in der Liste zeigt eine Kampagne, ohne das Messgerät
anzufassen. Erst „Messung fortsetzen" oder ein Doppelklick gibt ihr das Gerät. Das Fenster merkt sich
deshalb zwei Kampagnen: die angezeigte (`campaign_id`) und die messende (`live_id`). Wer während einer
Messung eine andere Kampagne ansieht, unterbricht nichts. Jede Lesung trägt die Kampagne, zu der ihre
Sitzung gehört, und landet dort, was auch immer gerade zu sehen ist. Geräteaktionen sind gesperrt,
solange das Gerät für eine andere Kampagne misst.

Solange eine Kampagne misst, hält `LiveSession` das Messgerät im Push-Modus und verbindet neu, wenn es
verschwindet. Ein Push geht zuerst in `CampaignService.receive()`, das ihn sofort speichert, dem
aktiven Schritt zuordnet oder offen lässt. Die Verbindung ist exklusiv: Für das Nachholen vom Gerät
und die Uhrprüfung tritt die Sitzung kurz zur Seite (`ui/instrument_control.py`). Vor dem Abschluss
wird sie getrennt, damit keine Lesung auf einen geschlossenen Datensatz trifft.

## Fotos und Anlagen

Ein Foto ist kein Messwert, sondern steht in der eigenen Tabelle `photos`. Seine Aufnahmezeit bleibt
unverändert, `placement` sagt, was über seine Zuordnung entscheidet:

- `timeline`: Es gehört zur nächstliegenden Messung. Eine Verschiebung (`photo_shift_s`) bewegt alle
  Fotos, eine Lücke (`photo_gaps`) alles ab ihrem Zeitpunkt.
- `pinned`: Ein Mensch hat es einer Messung zugeordnet, die Zeitleiste lässt es in Ruhe.
- `stack`: Es liegt ohne Zuordnung auf dem Stapel, die Datei bleibt erhalten.

Die Zeitleiste (`ui/photo_timeline.py`) zeigt Messungen und Fotos auf einer Zeitachse wie im Videoschnitt.
Eine Linie verbindet jedes Foto mit seiner Messung. Ein Foto seitlich zu ziehen verschiebt alle, es nach
oben auf eine Messung zu ziehen ordnet nur dieses fest zu. Die Spur unter dem Zeiger entscheidet, was
beim Loslassen passiert, und die Hinweiszeile sagt es vorher. Fotos lassen sich auch auf eine Tabellenzeile
ziehen. Die Zeitleiste ist ein Werkzeug zum Zuordnen: Sie steht unter der Tabelle, solange sie gebraucht
wird. „Fotos zuordnen“ im Kopf der Kampagne (F7) blendet sie ein, „Schließen“ in ihrer Leiste wieder aus;
nach einem Import öffnet sie sich von selbst. Eine Laufleiste unter den Spuren folgt Zoom und Verschieben.
Der Stapel steht in der Seitenleiste.

Die Bilddateien liegen nicht in der Datenbank, sondern unverändert im Ordner der Kampagne
(`campaigns/<uuid>/photos/`), benannt nach dem Anfang ihrer SHA-256-Prüfsumme. Die Tabelle `photos`
führt Dateiname, Prüfsumme, Aufnahmezeit und Zuordnung; das Siegel deckt über die Prüfsumme auch die
Datei ab. Ein Foto wird nie umgerechnet: Das Original bleibt der Beleg. Vergrößern brächte keine
Einzelheit dazu, deshalb gibt es keine Mindestauflösung durch Hochrechnen; die Fotoansicht nennt die
Pixel und warnt unter 1000 an der langen Seite, dass das Foto im Protokoll grob wirkt.

Für Protokoll und Vorschaubilder gibt es Proxys (`campaign/photo_proxies.py`): verkleinerte, aufrecht
gedrehte JPEG-Kopien mit höchstens 1400 Pixeln an der langen Seite im Ordner `proxies/` der Kampagne,
benannt nach Original und Größe. Ein Proxy trägt die Änderungszeit seines Originals; weicht sie ab,
entsteht er neu, so bleiben Proxy und Original im Gleichlauf. Beim Öffnen einer Kampagne und nach
einem Import entstehen fehlende Proxys im Hintergrund auf allen Kernen bis auf einen; die Statuszeile
zählt mit, und „Entwurf ansehen“ wartet, bis alle fertig sind. Vor jedem Protokoll räumt das Programm
Proxys ohne Original, solche anderer Größe und Reste abgebrochener Schreibvorgänge weg; ein gelöschtes
Foto nimmt seinen Proxy mit. Ohne Markierungen geht der Proxy unverändert in die PDF, mit Markierungen
wird er bemalt und neu kodiert. Proxys gehören nicht zum Siegel und lassen sich jederzeit löschen. Das
Protokoll wird neben dem Fenster gezeichnet, das dabei bedienbar bleibt.

Aus den Fotos der gewählten Messung in der Seitenleiste (`ui/photo_gallery.py`) lässt sich ein Foto
auf eine andere Zeile der Tabelle ziehen. Es gehört dann nur noch zu jener Messung, eine Mehrfach-
zuordnung gibt es nicht. Das Kreuz in der Ecke jedes Vorschaubildes löst das Foto von der Messung, solange
die Kampagne offen ist: Es kommt zu den nicht zugeordneten Fotos, Datei, Markierungen und Einstufung
bleiben erhalten. Löschen geht nur dort. Beide Arten stehen im Abschnitt „Fotos“ der Seitenleiste
als Reiter „Messung“ und „Nicht zugeordnet“ (`ui/photo_tabs.py`); wer ein Foto beim Ziehen über
einen Reiter hält, öffnet ihn. Auf dem Reiter „Messung“ abgelegt, gehört es zur gewählten Messung. Solange Fotos keiner Messung gehören, stehen der Abschnitt und der
Reiter in Orange, die Prüfzeile im Kopf meldet „n Fotos nicht zugeordnet“ und führt per Klick
dorthin, und „Bestätigen“ weist darauf hin, dass sie im Protokoll fehlen.

Die Fotoansicht (`ui/photo_preview.py`, `ui/photo_canvas.py`) nimmt nummerierte Markierungen auf: Ein
Rechteck über das Foto gezogen ergibt einen Bereich mit Nummer, der Text daneben erklärt ihn. Ein Klick
auf eine Zeile hebt ihren Bereich hervor; mit „Alle zeigen“ aus bleiben die Markierungen verborgen,
bis ihre Zeile gewählt wird. Daneben steht, als was das Foto ins Protokoll geht: Dokumentation,
Hinweis oder Mangel. Markierungen (Tabelle `photo_marks`, in Anteilen des aufrecht gedrehten Bildes)
und Einstufung (`photos.role`) werden erst mit „Übernehmen“ gespeichert. Das Protokoll zeichnet die
Rahmen mit ihren Nummern ins Foto und setzt die Einstufung und die Texte unter das Bild; ein Mangel
steht dort in Rot. Im Siegel stehen beide nur, wo es sie gibt, sodass ältere Siegel gültig bleiben.

Anlagen (`attachments`) sind Kommentare, Bilder und PDFs an einer Messung oder einem Ort. Sie gehören
immer zu einer Kampagne, damit ein Datensatz in sich vollständig bleibt. Entfernen löst sie von Messung
und Ort, Löschen beendet sie samt Datei. Fotos, Lücken, Anlagen und ihre Dateien gehören zum Siegel.

Dateien und Notizen der letzten bestätigten Prüfung derselben Anlage stehen in einer neuen Kampagne
grau mit Datum beim jeweiligen Element (`campaign/carry_over.py`, `ui/place_files.py`). Was damals an
einer Messung des Elements hing, gilt als am Element; was an der Kampagne selbst hing, als an der
Anlage. „Übernehmen“ kopiert den Eintrag in die offene Kampagne, die abgeschlossene bleibt unverändert
und versiegelt. Übernommenes erscheint nicht mehr als Angebot. Eine kampagnenunabhängige Ablage an
Elementen gibt es bewusst nicht: Erst eine Bauteilliste mit Historie gäbe ihr einen Sinn.

## Benutzer

Ein Benutzer hat Titel, Name, Unterschrift und optional ein Zertifikat (`ui/users.py`). Vom Zertifikat
stehen nur Pfad, Inhaber und Ablaufdatum in der Datenbank, das Passwort wird nie gespeichert. Es dient
nur zum Prüfen und Signieren. Wer schon Kampagnen hat, wird beim Entfernen nur ausgeblendet.

Eine Kampagne verweist auf den Benutzer (`user_id`) und hält seinen Namen zusätzlich als Text fest
(`tester`). Beim Abschluss kommt die Unterschrift als Kopie dazu, ihr Hash gehört zum Siegel. Spätere
Änderungen am Benutzer berühren den Datensatz deshalb nicht. Solange die Kampagne offen ist, lässt sich
der Prüfer wechseln, auf Wunsch auch für die bisherigen Messungen. Das wird registriert, markiert im
Protokoll aber keine Messung als geändert, weil es nichts über das Ergebnis sagt. Eine gepushte Messung
nennt den Prüfer der Kampagne, der Text des Geräts bleibt in `raw_data` erhalten.

## Eingaben

Eingaben sind Überlagerungen, keine eigenen Fenster (`ui/overlay.py`). Die Karte liegt über dem
abgedunkelten Fenster und wird wie ein Dialog mit `exec()` benutzt. Die Arbeit dahinter bleibt sichtbar
und läuft weiter, ein Messwert kommt auch währenddessen an. Enter bestätigt, Esc bricht ab, ein Klick
daneben tut nichts. Ein grauer Hauptknopf erklärt sich selbst: Links daneben steht, was noch fehlt.
Überlagerungen lassen sich schachteln, zum Beispiel „Neu …" beim Prüfer im Kampagnenstart.

## Messpläne und Wizard

Ein Messplan ist eine Folge von Punkten: `check` (Frage mit Ja, Nein oder Überspringen), `measure`
(Messung) und `note` (Hinweis). Pläne liegen als YAML in der Tabelle `plans` und werden unter
Einstellungen → Messpläne bearbeitet (`ui/plan_editor.py`). Änderungen speichern sich selbst. Der Testlauf
(`ui/plan_test_run.py`) zeigt den Plan im Wizard mit einem simulierten Gerät in einer Wegwerf-Datenbank.

Die Anleitung je Messbereich gehört zum Messgerät und liegt bei seinem Treiber
(`devices/profitest_prime/instructions/`), eine Datei je Messfunktion: Drehschalter,
Einstellungen, Warnungen, Anschlussbild, Vorgehen und der Betrieb des Prüflings (`dut`). Ein Messpunkt
übernimmt sie über seine Funktion. Dieselbe Anleitung zeigt die freie Messung auf Wunsch und folgt dort
dem Drehschalter und dem letzten Messwert. Für eine Funktion ohne Anleitung sagt die App das, sie zeigt nie etwas Fremdes.

Eine Kampagne bekommt beim Start einen Plan, weitere kommen über „Messplan zuweisen" dazu. Jeder Punkt
wird dabei als Kopie in `steps` festgehalten, ein korrigierter Plan ändert also keine Kampagne.

Der Wizard (`ui/guided.py`) zeigt einen Punkt nach dem anderen mit Fortschritt, Zurück und Weiter.
Die erwartete Antwort geht sofort weiter, jede andere wartet auf einen freiwilligen Kommentar.
Überspringen braucht eine Begründung. J, N und S antworten ohne Maus. Eine Antwort wird wie ein Messwert
gespeichert (`visual_inspection`), steht also in der Tabelle und im Protokoll. Antwortet man neu,
ersetzt das die alte Antwort. Im Protokoll bilden Antworten eine Tabelle, Hinweise erscheinen dort nicht.

Ein Messpunkt läuft so: Aufbau im Anschlussbild anklicken, Einstellungen bestätigen, messen, Weiter.
Mit Live-Verbindung ist jeder Wert schon da, ohne sie holt Weiter den Gerätespeicher ab. Ein Messwert
wird dem aktiven Schritt zugeordnet, wenn die Funktion passt, sonst steht er unter „Nicht zugeordnet".
Ohne Gerät gibt man Werte von Hand ein, sie landen im gezeigten Schritt.

Der mitgelieferte Plan ist ein Entwurf (`released: false`). Seine Anschlussangaben stammen aus der
Bedienungsanleitung, Grenzwerte und Reihenfolge sind Vorschläge.

### Simulator

`devices/simulator.py` ist ein vollwertiger Treiber: Er liefert Zufallswerte, gelegentlich außerhalb
der Grenzwerte, und hat einen zufälligen Uhrenversatz. Mit der Messfunktion lässt sich auch ein
falsch stehender Drehschalter nachstellen. Seine Beschreibung trägt `simulated=True`; daran, nicht
am Schlüssel, erkennt die Anwendung Simulationen. Protokolle aus Simulationen tragen einen Hinweis
und lassen sich nicht signieren.

## Vorlageneditor

Die Vorlagen-Seite zeigt eine Vorlage als Blockliste mit Eigenschaften und Live-Vorschau für 0, 1
und 4 Messungen. Daten werden aus einer Liste eingefügt, Anzeigebedingungen ausgewählt. Der Reiter
„Quelltext“ zeigt dieselbe Vorlage als YAML; Änderungen dort gelten auch im Aufbau.

### Briefkopf und Abschluss

Der Block „Briefkopf“ eröffnet das Protokoll: ein QR-Code mit der Kennung der Prüfung (ihre UUID,
dieselbe wie in der Fußzeile), daneben Titel und Zeilen darunter, darunter ein Rahmen mit
Auftraggeber und Auftragnehmer. Jede Zeile darf Datenfelder enthalten; eine Zeile, deren Datenfelder alle leer sind, entfällt
samt Beschriftung, etwa „Telefon:“ ohne Nummer. Abteilung, Ansprechpartner, Durchwahl und E-Mail
gehören zur Kampagne, nicht zum Kunden: Der Ansprechpartner wechselt mit dem Auftrag. Er steht unter
„Kampagne bearbeiten …“; eine neue Kampagne übernimmt den der letzten Kampagne desselben Kunden.
Im Briefkopf erscheint er unter der Anschrift des Kunden. Die eigene Kostenstelle ist ebenfalls ein
Wert der Kampagne und steht beim Auftragnehmer; sie wird nicht in die nächste Kampagne übernommen. Die eigene
Firma steht einmal zentral unter Einstellungen → Firma (Tabelle `company`, eine Zeile): Name,
Anschrift, Telefon, E-Mail, Internet und Logo. Vorlagen greifen über die Datenfelder `company.*`
darauf zu, der Briefkopf setzt das Logo rechts neben den Titel. Ein Logo-Block mit eigenem Bild
bleibt für Vorlagen, die ein anderes Bild brauchen. Warnhinweise wie „Entwurf“ stehen direkt
unter dem Briefkopf. Die Unterschriftszeile kann darüber gerahmt das Ergebnis tragen, grün bei
bestanden, rot bei nicht bestanden; ihre Felder dürfen Datenfelder enthalten, etwa den Namen des
Prüfers.

### Seitenumbruch

Überschriften bleiben bei dem, was folgt. Vor einer Tabelle beginnt eine neue Seite, wenn Kopfzeile
und erste Zeilen nicht mehr passen, vor einer Fotozeile, wenn eine Bildreihe nicht mehr passt. Läuft
eine Tabelle über eine Seite, beginnt die nächste Seite mit der Überschrift und „(Fortsetzung)“, dann
der Kopfzeile. Absätze lassen keine einzelne Zeile am Seitenende oder -anfang zurück. Spaltenbreiten
richten sich nach dem Inhalt: Jede Spalte bekommt mindestens ihr längstes Wort, kurze Werte samt
Einheit bleiben auf einer Zeile, bei Platzmangel geben nur Spalten mit langen Texten nach. Zwischen
Zahl und Einheit steht ein schmales geschütztes Leerzeichen.

### Logo

Der Block „Logo“ steht außerhalb des Textflusses und wird über Koordinaten in Millimetern auf die
Seite gesetzt, auf der ersten oder auf jeder Seite. Verschoben und skaliert wird auf einer
Seitenminiatur, über Zahlenfelder oder mit Schnellpositionen; das Seitenverhältnis bleibt erhalten.

Das Bild wird in die Vorlage eingebettet (`images:` am Ende des YAML, Schlüssel aus dem Inhalt) und
beim Import auf höchstens 1000 Pixel Kantenlänge verkleinert. Eine Vorlage bleibt so ohne Zusatzdateien
vollständig, und ein archiviertes Protokoll behält das Logo, das damals galt. SVG-Dateien werden beim
Import in ein transparentes Bitmap umgewandelt.

Liegt ein Logo am oberen oder unteren Seitenrand, weicht der Text aus. Das lässt sich abschalten;
ein Logo in der Seitenmitte verdrängt keinen Text.

## Signatur

Signiert wird als PAdES mit einem X.509-Zertifikat aus einer PKCS#12-Datei. Das kann auch ein
S/MIME-Zertifikat sein, zum Beispiel aus Thunderbird oder Kleopatra exportiert. Die Datei bleibt, wo
sie ist. Das Programm merkt sich nur ihren Pfad in `settings.ini`; Schlüssel und Passwort werden
nirgends gespeichert. Vor dem Signieren zeigt ein Dialog Name, E-Mail, Aussteller und Gültigkeit.
Abgelaufene Zertifikate und reine Verschlüsselungszertifikate werden abgewiesen.

Ein E-Mail-Zertifikat ergibt eine technisch gültige Signatur. Ob ein PDF-Programm sie als
vertrauenswürdig anzeigt, hängt davon ab, ob es dem Aussteller vertraut.
