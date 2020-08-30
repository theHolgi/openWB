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


# Leistungsarbitrierung v2

## Regelgruppen

Es gibt (mindestens) 2 Regelgruppen; jeder Ladepunkt ist genau einer Gruppe zugeordnet:

- PV 
- PV peak shaving
- Sofortladen (Null-Regler, aber zum Aufruf der LPs die in dieser Gruppe sind)

"PV" und "PV peak shaving" funktionieren im Wesentlichen gleich, aber haben verschiedene Regelbereiche.
PV möchte Überschuss nahe 0 halten, ohne Übertritt nach unten
PV peak shaving möchte Überschuss nahe Limit halten, ohne Übertritt nach oben

"Sofortladen" wird nicht geregelt. Der Ladepunkt wird nur aufgerufen und stellt seinen Soll-Strom direkt ein.

## Erkennung gesättigter / blockierter Ladepunkt

Eine Nicht-Ladebereitschaft (kein Fahrzeug angesteckt) erkennt der LP wenn technisch möglich selbst und fordert keine Leistung an.
Ein gesättigtes Fahrzeug (Nimmt nicht mehr als die momentane Leistung ab) erkennt der LP selbst. 
Erhöhung der Leistung wird mit der niedrigsten Priorität gesendet, um nur zum Zuge zu kommen wenn kein anderer die Leistung anfordert.

## Einschalt- / Ausschaltverzögerung

Werden vom Ladepunkt selbst gezählt.
TODO: LP in Ausschaltverzögerung muss dem Arbiter signalisieren, zunächst andere LPs zu reduzieren.

## Kommunikation LP <-> Regler

Ladepunkte generieren eine Liste:
- minimales Leistungsinkrement (z.B. 0 -> 6A oder gar nicht)
- maximales Leistungsinkrement (Platz bis Pmax)
- minimales Leistungsdekrement (ebenso)
- maximales Leistungsdekrement (Platz bis Pmin)
- Flag, LP in Einschaltverzögerung. Zugeteilte Leistung muss nicht von anderen abgezogen werden, aber bitte zuteilen 
damit der LP die Verzögerung zählen kann.

Inkremente sind mit Priorität versehen. Standardprorität ist am LP konfiguriert, 
darüber lassen sich Ladepunkte untereinander sowie gegenüber Batteriespeicher priorisieren.

z.B. Ein LP mit SOC < Wunsch-% liefert:

- P+min prio medium: 1A * 230V*1 Ph (in Stufen von 1A)
- P+max prio medium: 3A * 230V* 1 Ph (noch 3A, dann ist Wunsch-P zum SOC Laden)
[- P+max prio low:   12A * 230V*1 Ph (noch 12A bis I-max erreicht)]
 Wird erst gesendet, wenn die 3A Anforderung erfüllt ist.
- P-min prio medium: 1A * 230V*1Ph (in Stufen von 1A, aber nur erlaubt wenn mit Prio "high" abgezogen wird)
- P-max prio medium: 600W (so viel lädt er über Pmin)

z.B. ein Batteriespeicher liefert:
- P+min 10W prio low -> Kann in 10W Schritten Leistung verändern
- P+max 3000W prio low -> Könnte noch 3kW schneller
- P-min 10W prio low -> Kann auch um 10W runter
- P-max = llaktuell -> Kann bis auf 0W sofort runterregeln

z.B. Ladepunkt an gesättigtem Fahrzeug:
- P+min 1A * 230V*1 Ph prio idle -> Wenn noch Leistung frei ist, probieren wir 1A mehr. Sonst bleiben wir bei aktuell.
- P+max 10A * 230V*1 Ph prio idle -> so viel mehr ginge von I-max. Aber hat ja keinen Sinn.
- P-min 1A * 230V*1 Ph prio low -> was lädt, das lädt. Wegnehmen gegen meine Default-Prio.
- P-max 600W (Differenz zu Pmin)

z.B. ladebereiter Ladepunkt, aktuell "aus":
- Flag "ondelay"
- P+min 6A * 230V * 1Ph -> Einschalten mit 6A oder gar nicht
- P+max 16A * 230V * 1Ph -> Gerne auch direkt auf 16A
- P-min 0W prio egal -> Weniger als nichts geht nun gar nicht
- P-max 0W

Ladepunkt mit "Minimalstrom" und Lädt mit diesem:
- P-min 0A
- P-max 0A
- P+min/max analog oben

Ladepunkt auf minP und die Sonne ist aus:
- P+min 1A * 230V * 1Ph -> Erhöhen geht von Seiten des LP ja schon. Wird nur nichts geben.
- P+max 10A * ...
- P-min 6A * 230V * 1Ph -> Abschalten gibt ja 6A frei.
- P-max 6A ...          -> Ist gleichzeitig die maximal freigebbare Leistung.


Szenario: 2000W Überschuss, 2LP aus
-> beide signalisieren "P+min 1300W"
-> Zuteilung Einschalten nur an den ersten.

Szenario: 2LP gleiche Prio; einer Lädt mit 2000W, einer aus. Überschuss 1000W.
-> 3000W Budget. Kann LP2 eingeschaltet werden?
-> LP1 signalisiert P-max 700W. Also reicht es.
-> LP2 wird freigegeben. Solange LP2 ondelay signalisiert, bekommt LP1 die vollen 3000W
-> Wenn LP2 einschaltet, ist Flag "ondelay" weg. LP1 wird die Leistung abgezogen.
Sollten sich zwischendurch die Bedingungen ändern (Weniger PV-Leistung...), wird LP2 wieder gesperrt und resettet counter.

Szenario: 2LP laden: low-Prio 2000W, high-Prio 1000W. Kein Überschuss.
Low-Prio soll abgeschaltet werden, damit high-Prio schneller kann.
-> Zuteilung (-P-max) an LP1. Zuteilung "llaktuell" an LP2 (Status quo bis Leistung verfügbar)
-> Nächste Loop ist Überschuss da. Wird an LP2 zugeteilt.

## Funktionsweise Arbiter

- Ermittle den Zielkorridor des Überschusses.
z.B. +200W bis +600W sei eingestellt. Liegt der aktuelle Überschuss darüber -> Leistungserhöhung
Liegt er darunter -> Leistungsreduktion
Liegt er darin -> Leistungsverschiebung

* Einschaltversuch (in Erhöhung + Verschiebungsmodus)
Ab jetzt werden abgeschaltete LPs nicht mehr berücksichtigt.

a) Leistungserhöhung; gleiche Prioritäten gleichzeitig bedienen:
- sortiere P+min nach Prioritäten (highest first).
- sortiere als 2. Key die mit niedrigster ist-Leistung nach oben
Innerhalb der höchsten Priorität:
- Plane die Differenz zum Max-Lader ein, wenn im Korridor P+min/P+max
 ( < P+min: Keine Anpassung, > P+max: nur P+max)
-  ist der berechnete Überschuss im Korridor, höre auf.
-  verlässt der berechnete Überschuss den Korridor, ignoriere letzte Aktion und höre auf.
- Angepasst, aber Budget übrig? Fange von vorne an:
 - Weitere Erhöhung des Restbudgets in gleichen Teilen auf alle, nicht über P+max hinaus.
 - sollte für alle LPs in dieser Prio P+max ausgeschöpft sein und immer noch Budget vorhanden:     
 setze in nächster Prio fort.

Szenario: 3 LP; alle aus. Überschuss: 3000W
Leistung kann aktuell nicht abgegeben werden. Aber nur LP1+2 können eingeschaltet werden.
Szenario: 4LP; LP4 lädt auf 1000W. Überschuss: 3000
LP4 kann zunächst auf Max gestellt werden.
-> Step 2: LP4 auf 3700W, Überschuss: 300W
   LP4 signalisiert nun P-max (prio high) >2000W. LP1 muss und kann eingeschaltet werden.


Szenario: LP1 lädt mit 1000W, LP2 mit 2000W (gleiche Prio).
Korridor: +200 bis +600W, ist: +1000W
=> LP1 wird um 400W erhöht; +600W erreicht

          One two                         Spills             
        ist  P+min     P+max               P+min     P+max     
LP1    1000  230W low   *800W low*1       1000   230W low  *230W low*2 
LP2    2000  *230W low*2 800W low         2000   230W med  *500W med*1
LP3    3000  230W low    230W low         3000   *230W low*3  1000W low     
Übersch 1500 -> +800LP1, +230LP2 -> 470   1500  -> +500LP2,+230LP1,+230LP3 -> 540
Korridor: +200 bis +600W


b) Leistungsreduktion; gleiche Prioritäten gleichzeitig bedienen:
Ausschaltbare LPs werden zunächst ignoriert.
- sortiere P-min nach Prioritäten (lowest first)
- sortiere als 2. Key die LPs nach aktueller Leistung.
- Innerhalb der gleichen Priorität, reduziere die Leistung in Richtung min-Lader,
  aber limitiert auf P-min bis P-max.
- Im Korridor -> fertig
- Weitere Verringerung des Budgets in gleichen Teilen auf alle, nicht über P-min hinaus.
 - sollte für alle LPs in dieser Prio P-max ausgeschöpft sein und immer noch Notwendigkeit vorhanden:
 setze in nächster Prio fort.
Wenn am Ende angelangt:
- Ausschalten von LPs sortiert nach Priorität (lowest first) bis Budget erreicht.


             One two                            One can do it              switch off
           ist  P-min     P-max                 P-min     P-max                 P-min
    LP1    1000  230W low  800W low       1000   230W low  230W low      Imin   1300 med
    LP2    2000  230W low  *800W low*2    2000   230W med  500W med      Imin   1300 low
    LP3    3000  230W low  *230W low*1    3000   230W low  *2000W low*1 
    Übersch -1000 -230LP3,-770LP2 -> 200  -1000 -> -1200LP3 -> 200       -2000 -> -LP2,-LP1 -> +600
    Korridor: +200 bis +600W

c) Leistungsverschiebung
- sortiere P+min nach Prio (highest first); 2. key Ladeleistung (lowest first). Außer LP ist aus.
- sortiere P-min nach Prio (lowest first); 2. key Ladeleistung (highest first). Ignoriere LP winner (P+min).
- Eine Liste ist leer -> Ende
- wenn die Prio von P-min höher ist als die von P+min -> Ende
- Arbitriere die P-min Anforderung. 
- Warte darauf, daß in der nächsten Loop die Überschussverteilung stattfindet.

         High steals low                   Equalize           Ignoring self in P-min
        ist  P+min     P-min             P+min   P-min              P+min     P-min
LP1    1000  1A low   *1A low*   
LP2    1000  1A med    1A high    2000   1A low    *1A low*   2000 *1A med* --1A low--
LP3    1000  *1A high* 1A high    1500  *1A low*   1A low     1500  1A low   *1A low*

d) Einschaltversuch für deaktivierte LPs
- sortiere P+min der ausgeschalteten LPs nach Priorität.
Top Prio LP soll eingeschaltet werden.
- Ermittle Budget: Budget ist Überschuss - (lower Bound für Überschuss)
- Addiere P-max aller gleichen oder niedrigeren Priorität zum Budget.
- Wenn ausreichend, arbitriere diesen LP.
Es wird nur 1 LP auf einmal in Betrieb genommen.

               LP3 is higher prio
          P_akt     P+min   P-max
    LP1   3000              *2000* low
    LP2   off    *1300W low*
    LP3   2000               1000 med
    Übersch 500, Korridor 200...
    Budget = 300 + 2000

