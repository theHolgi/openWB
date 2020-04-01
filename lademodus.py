#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import sys
import unittest
import subprocess
from openWBlib import *

class NurPVModus:
   def __init__(self, values, config):
      self.values = values
      self.config = config

   def minimal(self, message):
      """Set all ladepunkte to minimum"""
      req = {}
      if self.config['minimalapv'] == self.config['minimalalp2pv']:
         req['all'] = self.config['minimalapv']
         log("alle Ladepunkte, Lademodus NurPV. %s %i Ampere" % (message, self.config['minimalapv']))
      else:
         req['lp1'] = self.config['minimalapv']
         log("LP1, Lademodus NurPV. %s %i Ampere" % (message, self.config['minimalapv']))
         req['lp2'] = self.config['minimalalp2pv']
         log("LP2, Lademodus NurPV. %w %i Ampere" % (message, self.config['minimalalp2pv']))
      return req

   def run(self):
      req = {}
      values = self.values
      config = self.config
      llsoll = values['llsoll']   # TODO: max from loadvars
      uberschuss = -values['wattbezug']  # TODO: Glättung
      mindestuberschussphasen = uberschuss * values['anzahlphasen']
      if config['lastmanagement'] == 0 and config['socmodul'] != "none":
         if values['soc'] < config['minnurpvsoclp1']:
            if values['ladestatus'] == 0:
               req['all'] = config['minnurpvsocll']
               log("LP1, Lademodus NurPV. Ladung mit %i Ampere, %i % SoC noch nicht erreicht" % (config['minnurpvsoclp1'], values['sofortsoclp1']))

               debug("Starte PV Laden da %i % zu gering" % values['soc'])
            else:
               if llsoll != config['minnurpvsocll']:
                  req['all'] = config['minnurpvsocll']
                  log("LP1, Lademodus NurPV. Ladung geändert auf %i Ampere, %i % SoC noch nicht erreicht" % (config['minnurpvsoclp1'], values['soc']))
            return req

         if values['soc'] > config['maxnurpvsoclp1']:
            if values['ladestatus'] == 1:
               req['all'] = 0
               log("LP1, Lademodus NurPV. Ladung gestoppt, %i % SoC erreicht" % values['soc'])
               debug("Beende PV Laden da %i % erreicht" % config['maxnurpvsoclp1'])
            return req

      if values['ladestatus'] == 0:
         if values['ladestatuss1'] == 1 or values['ladestatuss2'] == 1:
            req['all'] = 0
            log("alle Ladepunkte, Lademodus NurPV. Ladung gestoppt")
         log("Überschuss %i; mindestens %i" % (uberschuss, mindestuberschussphasen))
         if  mindestuberschussphasen <= uberschuss:
            pvecounter=values['pvecounter']
            if pvecounter < config['einschaltverzoegerung']:
               pvecounter=pvecounter + 10
               values['pvecounter'] = pvecounter
               debug("PV Einschaltverzögerung auf %i erhöht, Ziel %i" % (pvecounter, config['einschaltverzoegerung']))
               return
            else:
               debug("nur pv ladung auf %i starten" % config['minimalapv'])
               values['pvcounter'] = 0
               values['pvecounter'] = 0
               values['soctimer'] = 20000
               return self.minimal('Lademodus NurPV. Ladung gestartet')
         else:
            values['pvcounter'] = 0
            return {}

      ladeleistung = values['mqttladeleistung']  # schon aufsummiert über alle Ladepunkte
      if ladeleistung < 300:
         if llsoll > config['minimalapv']:
            llneu=config['minimalapv']
            values['pvcounter'] = 0
            return self.minimal('Ladung geändert auf')
         if llsoll < config['minimalapv']:
            llneu=config['minimalapv']
            values['pvcounter'] = 0
            return self.minimal('Ladung geändert auf')
         if llsoll == config['minimalapv']:
            if uberschuss < mindestuberschussphasen:
            #if (( wattbezugint > abschaltuberschuss )); then
               #pvcounter=$(cat /var/www/html/openWB/ramdisk/pvcounter)
               #if (( pvcounter < abschaltverzoegerung )); then
               #	pvcounter=$((pvcounter + 10))
               #	echo $pvcounter > /var/www/html/openWB/ramdisk/pvcounter
               #	if [[ $debug == "1" ]]; then
               #		echo "Nur PV auf Minimalstromstaerke, PV Counter auf $pvcounter erhöht"
               #	fi
               #else
                  if os.path.isfile('ramdisk/nurpvoff'):
                     req['all'] = 0
                     log("alle Ladepunkte, Lademodus NurPV. Ladefreigabe aufgehoben, Überschuss unterschritten")
                     debug("pv ladung beendet")
                     os.unlink('ramdisk/nurpvoff')
                  else:
                     open('ramdisk/nurpvoff')
      else:
         # if [[ $speichervorhanden == "1" ]]; then
         #    if (( speicherleistung < 0 )); then
         #       if (( speichersoc > speichersocnurpv )); then
         #          uberschuss=$((uberschuss + speicherleistung + speicherwattnurpv))
         #          wattbezugint=$((wattbezugint - speicherleistung - speicherwattnurpv))

         #       else
         #          uberschuss=$((uberschuss + speicherleistung))
         #          wattbezugint=$((wattbezugint - speicherleistung))
         #       fi
         #    fi
         # fi
         if uberschuss > os.environ['schaltschwelle']:
            if llsoll == config['maximalstromstaerke']:
               return
            if config['pvbezugeinspeisung'] == "0":
               llneu=llsoll + ( uberschuss / 230 / values['anzahlphasen'])
            else:
               if llsoll == config['minimalapv']:
                  llneu=llsoll+1
               else:
                  llneu=llsoll + ( (uberschuss - os.environ['schaltschwelle']) / 230 / values['anzahlphasen'])
            if llneu > config['maximalstromstaerke']:
               llneu=config['maximalstromstaerke']
            if llsoll < config['minimalapv']:
               llneu=config['minimalapv']
            if config['adaptpv'] == 1 and values['soc'] > 0 and values['soc1'] > 0 and values['anzahlphasen'] == 2:
               if config['minimalalp2pv'] > config['minimalapv']:
                  config['minimalapv']=config['minimalalp2pv']
               socdist = values['soc1'] - values['soc']
               if socdist < 0: socdist = -socdist
               anzahl=socdist / config['adaptfaktor']
               if values['soc1'] > values['soc']:
                  higherev='lp2'
                  lowerev='lp1'
               else:
                  higherev='lp1'
                  lowerev='lp2'
               llhigher=llneu
               lllower=llneu
               for i in range(anzahl):
                  if llhigher > config['minimalapv']  and lllower < config['maximalstromstaerke']:
                     llhigher=llhigher - 1
                     lllower=lllower + 1
               req[higherev] = llhigher
               req[lowerev] = lllower
               log("LP%s, Lademodus NurPV. Adaptive PV Ladung geändert auf %i Ampere" % (higherev, llhigher))
               log("LP%s, Lademodus NurPV. Adaptive PV Ladung geändert auf %i Ampere" % (lowerev, lllower))
               time.sleep(1)
               values['llsoll'] = llneu
               values['llsolls1'] = llneu
               debug("Adaptiert auf: %s -> %i, %s -> %i" % (higherev, llhigher, lowerev, lllower))
            else:
               req['all'] = llneu
               log("alle Ladepunkte, Lademodus NurPV. Ladung geändert auf %i Ampere" % llneu)
               debug("pv ladung auf %i erhoeht" % llneu)
            values['pvcounter'] = 0
            return req
         pvregelungm = values('offsetpv')  # TODO: Take over from regel.sh
         if uberschuss < pvregelungm:
            if llsoll > config['minimalapv']:

               llneu= llsoll - 1 + ( (uberschuss - pvregelungm) / 230 / values['anzahlphasen'])
               if llneu < config['minimalapv']:
                  llneu=config['minimalapv']
               if False: # (( adaptpv == 1 )) && (( soc > 0 )) && (( soc1 > 0 )) && ((values['anzahlphasen'] == 2 )); then
                  # socdist=$(echo $((soc1 - soc)) | sed 's/-//')
                  # anzahl=$((socdist / adaptfaktor))
                  # if (( soc1 > soc )); then
                  #    higherev=s1
                  #    lowerev=m
                  # else
                  #    higherev=m
                  #    lowerev=s1
                  # fi
                  # llhigher=$llneu
                  # lllower=$llneu
                  # for ((i=1;i<=anzahl;i++)); do
                  #    if (( llhigher > minimalapv )) && (( lllower < maximalstromstaerke )); then
                  #       llhigher=$((llhigher - 1))
                  #       lllower=$((lllower + 1))
                  #    fi
                  # done
                  # runs/set-current.sh $llhigher $higherev
                  # echo "$date LP$higherev, Lademodus NurPV. Adaptive PV Ladung geändert auf $llhigher Ampere" >>  ramdisk/ladestatus.log
                  # runs/set-current.sh $lllower $lowerev
                  # echo "$date LP$lowerev, Lademodus NurPV. Adaptive PV Ladung geändert auf $lllower Ampere" >>  ramdisk/ladestatus.log

                  # sleep 1
                  # echo $llneu > ramdisk/llsoll
                  # echo $llneu > ramdisk/llsolls1

                  # if (( debug == 1 )); then
                  #    echo $llneu "reduziert, adaptiert auf"
                  #    echo auf $llhigher A für LP $higherev
                  #    echo auf $lllower A für LP $lowerev
                  # fi
                  pass
               else:
                  req['all'] = llneu

                  log("alle Ladepunkte, Lademodus NurPV. Ladung geändert auf %i Ampere" % llneu)
                  debug("pv ladung auf  %i reduziert" % llneu)
               values['pvcounter'] = 0
            else:
               wattbezugint = values['glattwattbezug']
               if wattbezugint > config['abschaltuberschuss']:
                  pvcounter=values['pvcounter']
                  if pvcounter < config['abschaltverzoegerung']:
                     values['pvcounter'] = pvcounter + 10
                     debug("Nur PV auf Minimalstromstaerke, PV Counter auf %i erhöht" % values['pvcounter'])
                  else:
                     req['all'] = 0
                     log("alle Ladepunkte, Lademodus NurPV. Ladung gestoppt zu wenig PV Leistung: %i" % wattbezugint)
                     debug("pv ladung beendet")
                     values['pvcounter'] = 0
               else:
                  values['pvcounter'] = 0
            return req

class MaxPVModus:
   def __init__(self, values, config):
      pass
   def run(self):
      pass

class TestStringMethods(unittest.TestCase):
   def test_nurPV(self):
      mockvalues = {}
      mockconfig = {}
      controller = NurPVModus(mockvalues, mockconfig)
      self.assertEqual(controller.run(), None)
   def test_maxPV(self):
      mockvalues = {}
      mockconfig = {}
      controller = MaxPVModus(mockvalues, mockconfig)
      self.assertEqual(controller.run(), None)

if __name__ == '__main__':
   if len(sys.argv) < 2:
      sys.stderr.write("Usage: %s <lademodus>" % sys.argv[0])
      sys.exit(1)
   mode = int(sys.argv[1])
   config = openWBconfig()
   values = openWBValues()
   if mode == 3:  # Nur-PV
      controller = NurPVModus(values, config)
   elif mode == 5: # Max-PV
      controller = MaxPVModus(values, config)
   setCurrent(controller.run())
