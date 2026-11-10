# Programmierregeln

- Alle Programmzeilen sind Englisch: Kommentare und alle Namen. Texte für Nutzer der Anwendung
  stehen englisch im Code und werden über die Sprachkataloge übersetzt (siehe Architektur, Sprachen).
- Commit-Nachrichten sind Englisch.
- Es gibt keine Historienkommentare. Was früher war, steht in der Versionsgeschichte.
- Ein Kommentar beschreibt, wie eine Lösung funktioniert, nie externe Gründe.
- Eine Programmdatei hat höchstens 150 bis 200 Zeilen Code ohne Kommentare. Ausnahme sind Dateien
  mit gleichförmig wiederholtem Inhalt wie Sprachkataloge.
- Formatierung für Menschen: möglichst eine Anweisung pro Zeile.
- Vor dem ersten Release gibt es keine Migrationsfunktionen im Programm. Notwendige Migrationen laufen
  extern mit eigenen Werkzeugen.
