# Features implementiert
## Core
Datenobjekt, Konfigurationsobjekt, Runner
## Module
  Implementierung eines EVU (smashm), Wechselrichter (SMA), Ladepunkt (GO-e)
## Regelalgorithmen
PV, Peak, Sofortladen mit beliebig vielen Ladepunkten und Priorisierung
Nicht ausschalten toggle (aka: Min-PV)

## GUI

Lademodus per LP einstellen

# Features TODO
## Core
- threaded runner / asynchrone Loopzeiten
- API um an Daten zu kommen

## Module
- Batteriespeicher
- SOC Modul
- generische Wrapperklasse für nicht konvertierte Module

## Regelung

- Ladestop nach Menge
- Ladestop nach SOC
- Kein Ausschaltdelay, wenn Ladung noch nicht begonnen wurde / beendet wurde

- Schieflast

## GUI

- Fast alles mit Konfigurations über GUI

- Alles von dem ich gar nicht weiß, daß es das auch gibt

## Notes Ladelimitierung:

openWB/config/set/sofort/lp/1/chargeLimitation => msmoduslp%i
0 = Keine
1 = Energy  => openWB/config/set/sofort/lp/1/energyToCharge => lademkwh%i
       republish: openWB/lp/1/boolDirectModeChargekWh
2 = SoC     => openWB/config/set/sofort/lp/1/socToChargeTo => sofortsoclp%i
       republish: openWB/lp/1/boolDirectChargeModeSoc
       
Resetbutton: openWB/config/set/sofort/lp/1/resetEnergyToCharge = b"Reset"
Restzeit publish <str> to openwb/lp/1/timeremaining
Restzeit = (lademkwh - aktgeladen)[kWh] / ladeleistung[W] * 1000[W/kW] * 60 [min/h] = [min]
