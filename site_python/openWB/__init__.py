
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

class Modul:
   """Abstract class for a module"""
   def __init__(self, name: str):
      if hasattr(self.__class__, 'multiinstance') and self.__class__.multiinstance:
         name += '_' + str(self.id)
      self.name = name
      self.core = getCore()

   def event(self, event: Event):
      raise NotImplementedError

class DataPackage(dict):
   """A package of Data points"""
   def __init__(self, source: Modul, payload: dict = {}):
      self.source = source
      self.update(payload)


class DataProvider(Modul):
   """Abstract class for a data provider"""

   def __init__(self, instance_id: int):
      self.id = instance_id
      super().__init__(self.__class__.__name__)

   def trigger(self):
      raise NotImplementedError

class Ladepunkt:
   """Identifiziert einen Ladepunkt"""
   multiinstance = True
   type = "lp"

class PVModul:
   """Identifiziert einen Wechselrichter"""
   multiinstane = True
   type = "wr"
