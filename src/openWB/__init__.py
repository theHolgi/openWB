from typing import Mapping, Any


class Singleton(object):
   """
   Singleton base class
   http://mail.python.org/pipermail/python-list/2007-July/450681.html
   """

   def __new__(cls, *args, **kwargs):
      """ Create a new instance
      """
      if '_inst' not in vars(cls):
         cls._inst = object.__new__(cls)
      return cls._inst


class DataPackage(dict):
   """A package of Data points"""
   def __init__(self, source: "Modul", payload: Mapping[str, Any] = {}):
      self.source = source
      self.update(payload)
