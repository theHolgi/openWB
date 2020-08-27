
core = None  # The OpenWBcore singleton

def getCore():
   return core

def setCore(o):
   global core
   core = o

class Event:
   """Abstract class for an event"""
   pass

# A decorator for Modules to register with the core.
#def OpenWBModule(cls):
#   getCore().add_module(cls)
#   return cls


# Properties that every Modul has:
# name - Its name, built as CLASSNAME or CLASSNAME_<id> (when multiple instances)
# configprefix - Prefix for configuration
#              i.e. "bezugmodul1" für Bezugmodul Instanz 1
# id   - The ID (starting from 1) when multiple instances are possible
# core - the core class
# core.config - configuration
# core.data   - Data


class Modul:
   """Abstract class for a module"""
   def __init__(self, instance_id: int):
      name = self.__class__.__name__
      if hasattr(self.__class__, 'multiinstance') and self.__class__.multiinstance:
         self.id = instance_id
         name += '_' + str(instance_id)
      self.name = name
      self.configprefix = None  # Provided during setup
      self.core = getCore()

   def setup(self, config):
      """Setup the module (another possiblinity than overriding the constructor)"""
      pass

   def event(self, event: Event):
      """Process an event"""
      raise NotImplementedError


class DataPackage(dict):
   """A package of Data points"""
   def __init__(self, source: Modul, payload: dict = {}):
      self.source = source
      self.update(payload)


class DataProvider(Modul):
   """Abstract class for a data provider"""

   def trigger(self):
      raise NotImplementedError

class Ladepunkt:
   """Identifiziert einen Ladepunkt"""
   multiinstance = True
   type = "lp"

# Ein Ladepunkt sollte folgende Datenpunkte senden:
# llaktuell - Aktuelle Ladeleistung
# Optionale Datenpunkte:
# plugstat - Stecker eingesteckt (1|0)
# chargestat - Auto lädt (1|0)
# llkwh - Gesamte Lademenge
# llv1, llv2, llv3 - Spannung
# lla1, lla2, lla3 - Strom


class PVModul:
   """Identifiziert einen Wechselrichter"""
   multiinstance = True
   type = "wr"

# Ein Wechselrichter sollte folgende Datenpunkte senden:
#