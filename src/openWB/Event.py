from typing import Any

from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
   configupdate = 1  # Konfig-Änderung. info: config-Item    payload: neuer Wert
   resetEnergy = 2   # Ladepunkt Reset. info: Ladepunkt-ID   payload: None
   resetDaily = 3    # Reset daily-Werte.
   resetNoon = 4     # Reset daily (at noon)
   resetMonthly = 5  # Reset monthly-Werte

@dataclass
class OpenWBEvent:
   type: EventType
   info: Any = None
   payload: Any = None

