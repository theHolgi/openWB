#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import sys
import unittest
import subprocess
from openWBlib import *

class LadeModus(object):
   def __init__(self, values, config):
      self.values = values
      self.config = config

   def minimal(self, message):
      """Set all ladepunkte to minimum"""
      req = {}
      if self.config['minimalapv'] == self.config['minimalalp2pv']:
         req['all'] = self.config['minimalapv']
         log("LP1, %s %i Ampere" % (message, self.config['minimalapv']))
      else:
         req['lp1'] = self.config['minimalapv']
         log("LP1, %s %i Ampere" % (message, self.config['minimalapv']))
         req['lp2'] = self.config['minimalalp2pv']
         log("LP2, %s %i Ampere" % (message, self.config['minimalalp2pv']))
      return req

   def lowcurrent(self):
      """
      Handle niedrige Ladeleistung
      Returns:
        - None - nichts zu tun
        - "min" - setze min
        - "stop" - stoppe Ladung
      """
      ladeleistung = self.values['mqttladeleistung']  # schon aufsummiert über alle Ladepunkte
      llsoll = self.values['llsoll']   # TODO: max from loadvars
      mina   = self.config['minimalapv']
      if ladeleistung < 300:
         self.values['pvcounter'] += 10
         if self.values['pvcounter'] >= 100:
            log("Ladung beendet")
            return "stop"
         if llsoll != mina:
            self.values['pvcounter'] = 0
            return "min"


class NurPVModus(LadeModus):
   def __init__(self, values, config):
      super(NurPVModus, self).__init__(values, config)

   def run(self):
      req = {}
      values = self.values
      config = self.config
      llsoll = values['llsoll']   # TODO: max from loadvars
      uberschuss = -values['wattbezug']  # TODO: Glättung
      mindestuberschussphasen = config['mindestuberschuss'] * values['anzahlphasen']
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

      low = self.lowcurrent()
      if low == "min":
         return self.minimal("Setze auf min")
      elif low == "stop":
         req['all'] = 0
         return req
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

class MaxPVModus(LadeModus):
   def __init__(self, values, config):
      super(MaxPVModus, self).__init__(values, config)

   def run(self):
      req = {}
      values = self.values
      config = self.config
      llsoll = values['llsoll']   # TODO: max from loadvars
      uberschuss = -values['wattbezug']  # TODO: Glättung
      if values['ladestatus'] == 0:
         if  uberschuss > config['maxuberschuss']:
            values['pvecounter'] += 10
            if values['pvecounter'] >= config['einschaltverzoegerung']:
               debug("max-PV ladung auf %i starten" % config['minimalapv'])
               values['pvcounter'] = 0
               values['pvecounter'] = 0
               values['soctimer'] = 20000
               return self.minimal('Lademodus MaxPV. Ladung gestartet')
         else:
            values['pvcounter'] = 0
         return req
      low = self.lowcurrent()
      if low == "min":
         return self.minimal("Setze auf min")
      elif low == "stop":
         req['all'] = 0
         return req
      elif uberschuss > config['maxuberschuss'] and llsoll < config['maximalstromstaerke']:
         values['pvecounter'] += 10
         debug('O-o: Überschuss. Counter %i' % values['pvecounter'])
         if values['pvecounter'] >= config['einschaltverzoegerung']:
            llneu = llsoll+1
            req['all'] = llneu
            log("Max-PV: Ladestrom auf %i A erhöht" % llneu)
            debug("PV ladung auf  %i erhöht" % llneu)
            values['pvecounter'] = 0
         
      if uberschuss < config['maxuberschuss'] - (230 * values['anzahlphasen']) and llsoll > config['minimalapv']:
         values['pvcounter'] += 10
         if values['pvcounter'] >= config['abschaltverzoegerung']:
            llneu = llsoll-1
            log("Max-PV: Ladestrom auf %i A verringert" % llneu)
            debug("PV ladung auf %i A reduziert" % llneu)
            values['pvcounter'] = 0
            req['all'] = llneu
      elif uberschuss < config['maxuberschuss'] - (230 * values['anzahlphasen'] * config['minimalapv']) and llsoll == config['minimalapv']:
         values['pvcounter'] += 10
         if values['pvcounter'] >= config['abschaltverzoegerung']:
            log("Max-PV: Ladung beendet")
            req['all'] = 0
      else:
         values['pvcounter'] = 0
      return req


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
   if mode == 2:  # Nur-PV
      controller = NurPVModus(values, config)
   elif mode == 5: # Max-PV
      controller = MaxPVModus(values, config)
   setCurrent(controller.run())
