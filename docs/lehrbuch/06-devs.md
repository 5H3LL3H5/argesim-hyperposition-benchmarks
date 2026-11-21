# DEVS und der Ursprung von QSS

Wie kann ein Simulator von einem Ereignis zum nächsten springen, wenn die Temperatur eines Körpers zu jeder reellen Zeit einen Wert hat? Ein Thermostat meldet einen physischen Schaltvorgang, sobald eine Temperaturgrenze erreicht ist. Ein **Quantisierer** kann zusätzlich Schwellen nur für die Rechnung setzen. Seine Meldung bedeutet dann, dass ein neuer Näherungswert an benachbarte Modellkomponenten weitergegeben wird. Der Körper selbst erlebt an diesen Schwellen keinen Sprung.

1976 legte Bernard P. Zeigler mit *Theory of Modelling and Simulation* die Grundlage des DEVS-Formalismus (*Discrete Event System Specification*). Ein atomarer Baustein besitzt einen Zustand, Eingänge, Ausgänge und eine Zeitfortschrittsfunktion. Sie bestimmt die Verweildauer bis zum nächsten internen Übergang. Beim internen Ereignis erzeugt der Baustein zunächst seine Ausgabe und ändert danach seinen Zustand. Trifft vorher eine externe Nachricht ein, aktualisiert er den Zustand unter Berücksichtigung der verstrichenen Zeit und berechnet den nächsten Termin neu. Kopplungen beschreiben, wohin die Nachrichten gelangen. Für gleichzeitige Ereignisse muss das jeweils verwendete DEVS-Modell eine Auswahl- oder Konfluentregel festlegen. [ZE](literatur.md#ze)

| Entwicklung | Welche neue Frage ließ sich bearbeiten? |
|---|---|
| 1998 · Zeigler und Lee | Zustandsquantisierung koppelt kontinuierliche Komponenten über diskrete Nachrichten. Was muss ein Nachbar über eine Änderung erfahren? [ZL](literatur.md#zl) |
| 2001 · Kofman und Junco | Hysterese begrenzt unerwünschtes Hin- und Herschalten. Die quantisierte Dynamik erhält eine DEVS-Realisierung. Wie nähert sie die ursprüngliche ODE an? [KJ](literatur.md#kj) |
| 2002–2006 · Höhere Ordnung, DAEs und hybride Modelle | QSS2 übermittelt auch Steigungen. Für reguläre Index-1-DAEs und für hybride Systeme wurden eigene Konstruktionen untersucht. QSS3 erweitert die lokale Polynomdarstellung. [Q2](literatur.md#q2) · [QD](literatur.md#qd) · [HY](literatur.md#hy) · [Q3](literatur.md#q3) |
| 2012–2014 · Steife Modelle und eigenständige Solver | BQSS und LIQSS behandeln steife Rückkopplung. Der Stand-alone-Solver nutzt die Abhängigkeitsstruktur direkt. Damit werden Vergleiche mit klassischen ODE-Solvern praktisch interessant. [BQ](literatur.md#bq) · [LI](literatur.md#li) · [FK](literatur.md#fk) |

Cellier und Kofman verbinden diese Entwicklungen in ihrem Buch mit der Modellierung kontinuierlicher Systeme. Ein Ereignissimulator kann das gewählte quantisierte Modell bei erfüllten Voraussetzungen exakt ausführen. Die Abweichung dieser Trajektorie von der Lösung der ursprünglichen ODE hängt weiterhin vom Quantum, dem Modell und der Beobachtungsdauer ab. [CK](literatur.md#ck) · [KJ](literatur.md#kj)

## Ein externer Eingang widerruft eine Vorhersage

Ein QSS1-Baustein startet bei $x=q=0$ mit Steigung $+1$ und Quantum $\Delta=1/4$. Bei unveränderter Steigung würde er nach einer Viertelsekunde den Wert $q=1/4$ senden. Bereits bei $t=1/8$ trifft jedoch die neue Steigung $-1/2$ ein. Der kontinuierliche Zustand hat $x=1/8$ erreicht, die letzte gesendete Meldung lautet weiter null.

| Zeitpunkt | Was geschieht? | Konsequenz |
|---|---|---|
| 0 | Start mit Steigung +1 | Erster Ausgabetermin für $t=1/4$ vorgesehen. |
| 1/8 | Externer Eingang ändert die Steigung. | Alte Vorhersage löschen. Zum unteren Rand $-1/4$ fehlen $3/8$ Wegeinheiten. |
| 3/8 | $x$ fällt durch null. | Ein physikalischer Nullwächter könnte hier auslösen. Die Quantisierung fordert keine Meldung. |
| 7/8 | $x$ erreicht $-1/4$. | Internes Ereignis. Ausgabe $q=-1/4$, neuer Abstand zum nächsten unteren Rand $1/4$. |
| 11/8 | $x$ erreicht $-1/2$. | Zweite Ausgabe. |

Die Rechnung verwendet $3/8$ dividiert durch $1/2$, also $3/4$ Wartezeit ab dem Eingang. Die Schwelle für den numerischen Ausgang ist an den **zuletzt gemeldeten** Wert gebunden. Würde man das Raster beim externen Eingang neu zentrieren, ergäbe sich eine andere Ereignisfolge. Die rechte Hälfte von Abbildung 8 im nächsten Kapitel zeigt alle drei Arten von Zeitpunkten.

Der ausführbare Referenztest verwendet rationale Zeiten für den Ereignisplan. Ein zweiter Lauf treibt den öffentlichen QSS1-Solver über eine zusätzliche Zustandskomponente an. Der Test beobachtet dort die tatsächlich an die rechte Seite übergebenen quantisierten Werte. Beide Rechnungen senden bei $7/8$ und $11/8$ dieselben Werte. So lässt sich sogar eine fälschlich beibehaltene Zwischenmeldung erkennen. [Ereignistest](../../tests/test_qss_devs_trace.py)

> **Aufgabe 6.** Wiederholen Sie die Ereignisrechnung mit neuer Steigung −1 ab $t=1/8$. Wann durchquert $x$ die Null, wann kommt die erste interne Ausgabe, wann die zweite? [Lösung](10-loesungen.md#a6)
