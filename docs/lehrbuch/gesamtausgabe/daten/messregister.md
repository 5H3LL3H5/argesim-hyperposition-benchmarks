# Messregister lesen und prüfen

Das [Messregister](messregister.csv) enthält 80 Tabellenkennungen und 24 ergänzende Versuchsnachweise. Die Spalten haben unterschiedliche Bezugspunkte:

- **Physische PDF-Seite** und **PDF-Ausgabe** bezeichnen für Tabellen die vom gleichnamigen PDF-Ziel gelieferte, bei 1 beginnende Seitennummer. Sie werden aus der gesetzten Datei ausgelesen, nicht aus den Seitenmarken des Manuskripts geschätzt.
- **Archivfundstelle** kennzeichnet die 24 Zusatzzeilen. Ihre früheren Seiten stammen aus dem Register der Druckfassung v9.17; sie werden nicht als aktuelle PDF-Ziele ausgegeben.
- **Buchrevision** hält die ursprüngliche Erfassung fest. **Code- oder Datenherkunft** nennt die Herkunft des bereitgestellten Belegs. **Datei ab Paketwurzel** und **SHA-256** beziehen sich auf die tatsächlich ausgelieferten Bytes des vollständigen Labor-ZIPs.

Die [Acht-Fälle-Messausgaben](qss-matrix-ausgaben.csv) trennen die Vorauflage mit 222 Erfolgen, den v9.18-Vergleich mit 209, die Skalierungs-Gegenprobe mit 227 und die aktuell gedruckte Kontaktwiederholung mit 224. Jede Reihe hat 456 Konfigurationen. Gleiche Fall-, Solver- und Quantumkennungen bedeuten hier nicht, dass die Laufwerte verschiedener Messstände austauschbar sind.

## Druckfassung und Labor abnehmen

Aus dem Checkout, mit Poppler (`pdfinfo`, `pdftotext`):

```sh
python scripts/build_studienbuch.py --full-lab /tmp/ARGESIM_Rechenlabor.zip
python scripts/pruefe_messregister.py --pdf docs/ARGESIM_SOLVER_STUDY.pdf \
  --lab /tmp/ARGESIM_Rechenlabor.zip --edition v9.22
```

Bei neuer Druckfassung zuerst PDF und vollständiges Laborexport-ZIP bauen. Dann bei demselben Prüfaufruf die neue Ausgabe und zusätzlich `--update docs/lehrbuch/gesamtausgabe/daten/messregister.csv` angeben. Anschließend die Ausgaben und ihr Manifest erneut bauen und ohne `--update` prüfen. Die Abnahme vergleicht neben Hashes und PDF-Zielen die 168 Summenzellen in Kapitel 18 und alle 456 gerundeten Einzelwerte in Anhang B mit der aktuellen Primärdatei. Sie startet die archivierten Simulationen nicht erneut.
