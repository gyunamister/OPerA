from dataclasses import dataclass
# from dtween.digitaltwin.ocpn.objects.obj import Marking
from typing import List, Dict, Any, Optional


@dataclass
class Impact(object):
    name: str
    score: float

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, valve):
        return self.name == valve.name
