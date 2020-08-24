# Rollen
Alle Module sind Threads, die durch Events angetriggert werden. Events können "Start of new loop" oder andere wichtige Neuigkeiten sein.

## Data provider
Data provider sind Module, die rein Daten bereitstellen.
- Wechselrichter
- Leistungsmessung

Es gibt Data provider, von denen nur eine Instanz Sinn macht (Bezugsmodul) und Module, die mehrfach instanziierbar sind
(Wechselrichter).
Von letzteren werden die gelieferten Datenpunkte mit der Instanz-ID geführt, ggf. wird ein summierter Datenpunkt vom Core gebildet.

WR1: Pvwatt_1 \
WR2: Pvwatt_2 \
&rarr;   Pvwatt = sum(Pvwatt_n)

## Aktor
Aktoren sind Stellglieder; im Kontext OpenWB Ladepunkte.
Aktoren sind auch idR Data Provider (z.B. IST-Ladestrom); der Unterschied ist daß Aktoren *nach* der Regelung aufgerufen werden.


## Ladepunkt
Ein Ladepunkt kombiniert
- Einen Regler (eigene Regelstrategie)
- Einen Aktor
- ggf. ein SOC-Modul (*)

(*) Hat jemand eine geile IDee, wie man das fahrbare SOC-Modul magisch einem Ladepunkt zuordnen kann? Mein $Fahrzeug kann ja mal an LP1 und mal an LP2 eingestöpselt sein.

Batterien sind Ladepunkte, da sie eine Wunsch Ladeleistung in die Arbitrierung beisteuern können. (Priorität je nach SOC)

Q: Kann man Batterien eine Soll-Ladeleistung geben oder regeln die immer selber nach Einspeiseleistung? Wenn ja, eher Data Provider und Berücksichtigung bei der Berechnung des Überschuss-Budgets.

## Core Modul
Das Core Modul sammelt Daten und Konfiguration und stellt sie Modulen über eine API zur Verfügung, koordiniert außerdem das Scheduling.

Konfiguration ist mit Daten sehr verwandt; kann verändert werden (über UI), aber ist ansonsten sehr statisch.
Konfigurationspunkte sind nicht "unavailable", sondern unbekannte Config-Punkte werden bei Anfrage automatisch mit Defaults beantwortet.

Datenpunkte können dagegen "unavailable" sein (z.B. SOC wenn nicht vorhanden)

# Events

Konfigurationsänderungen lösen ein Config-Event aus.
(Quelle ist die UI, d.h. MQTT, sowie ein Startup-Modul das initial die openwb.conf liest)
Module können darauf reagieren.
Ggf. muss der Core selbst reagieren und neue Module starten, wenn die Modulkonfiguration geändert wurde.

Data Provider (auch Aktoren) senden ein Datenpaket an den Core und melden damit gleichzeitig Ready zum Regeln.


# Loop 
1) Trigger an alle Datenpunkte zur Lieferung ihrer Daten
2) Synchronisationspunkt, bis alle Module Ready gemeldet haben (evtl. auch alle Aktoren aus der letzten Loop)
3) Berechnung von verfügbarer Überschussleistung
4) MQTT Ausgabe (move at will)
5) Arbitrierung der Leistung an die Ladepunkte
6) Aufruf der Aktoren mit zugeteilter Leistung
7) Warten auf nächsten Zyklus


# Leistungsarbitrierung
Ladepunkte (d.h. deren Regler) fordern eine Liste von Leistung kombiniert mit Priorität an
- "Sofortladen": 
  * Muss nichts anfordern, lädt einfach sowieso
  * Schmälert das Budget für andere LPs über seinen IST-Strom
* "PV": 
  * (Max-I)*(Phasen) kW, Prio: low
* "PV" mit SOC < 50%:
  * (Max-I)*(Phasen) kW, Prio: low
  * Minimalleistung, Prio: medium

Mehrere Ladepunkte bekommen das Budget anhand ihrer Priorität aufgeteilt.
Einschalt- und Ausschaltverzögerung wird vom Ladepunkt selbst verwaltet.
 - LP in Ausschaltverzögerung fordert keine Leistung an, beansprucht aber weiter Budget (siehe Arbitrierung unten)
 - LP in Einschaltverzögerung fordert Min-Leistung an, um zu testen ob ihm diese (kontinuierlich) genehmigt wird.


Zuteilung der Leistung muss bei mehreren LPs ein bisschen intelligent erfolgen:

Ein LP nimmt vom verfügbaren Budget idR nur den IST-Ladestrom weg, nicht das ihm zugeteilte Budget.
(Kein Auto angeschlossen, Auto lädt langsamer als ihm erlaubt ist)

Andererseits darf die Leistung nicht an mehreren LPs gleichzeitig über das Verfügbare hinaus erhöht werden,
sonst drohen Überschwinger.

a) Es ist mehr Leistung verfügbar als aktuell abgenommen wird. Prio-mäßig muss auch kein LP verringert werden:

* Restbudget -= Summe aller IST 
* Ein LP lädt nicht mit zuletzt zugewiesenem Strom? &rarr; Zuweisung von I+1. Reduzierung des Budgets um 1A
* Aufteilung des Restbudgets auf die anderen LPs.

b) ... aber prio-mäßig muss ein LP verringert werden:
Wir wissen ja nicht, ob der High-Prio LP alle Leistung abnimmt. Daher:
- Low-Prio LP bekommt aktuelles IST (außer er hatte eh 0, d.h. ist in Ausschaltverzögerung. Die soll nicht resettet werden.)
- High-Prio lädt mit zuletzt zugeteiltem Strom? &rarr; Erhöhe High-Prio LP(s)
- Tut er gar nicht &rarr; setze High-Prio auf IST+1A, erhöhe Low-Prio.

c) Bilanz ist ausgeglichen, aber es müsste von einem low-Prio Leistung zum high-Prio verlagert werden:
* High-Prio Lädt mit dem zuletzt zugeteilten Strom?
  * nein: Nichts tun 
  * ja: Verringere Strom am Low-Prio um 1A. Erhöhe High-Prio um 1A.

d) Bilanz ist negativ.
* Verringere Strom an Low-Prio LP(s)
* Wenn das reicht, und der Soll-Strom an LPs nicht unter Min-A ist &rarr; Ende
- Wenn doch, verringere auch High-Prio LP in der Annahme daß die Low-Prio LPs Min-A ziehen.

