from dataclasses import dataclass, field
from dtween.digitaltwin.ocpn.objects.obj import ObjectCentricPetriNet
from dtween.digitaltwin.ocpn.objects.obj import Marking
from dtween.digitaltwin.valve.objects.obj import Valve
from typing import List, Dict, Any, Optional


@dataclass
class DigitalTwin(object):
    _ocpn: ObjectCentricPetriNet
    _valves: List[Valve] = field(default_factory=list)
    _guards: Dict[str, str] = field(default_factory=dict)
    _marking: Marking = field(default_factory=lambda: None)
    _config: Dict[str, float] = field(default_factory=dict)
    _omap: Dict[str, Any] = field(default_factory=dict)

    # log: Optional[ObjectCentricLog] = field(default_factory=lambda: None)

    @property
    def ocpn(self) -> ObjectCentricPetriNet:
        return self._ocpn

    @ocpn.setter
    def ocpn(self, ocpn: ObjectCentricPetriNet) -> None:
        self._ocpn = ocpn

    @property
    def valves(self) -> List[Valve]:
        return self._valves

    @valves.setter
    def valves(self, valves: List[Valve]) -> None:
        self._valves = valves

    @property
    def guards(self) -> Dict[str, str]:
        return self._guards

    @guards.setter
    def guards(self, guards: Dict[str, str]) -> None:
        self._guards = guards

    @property
    def object_types(self):
        return list(set([pl.object_type for pl in self._ocpn.places]))

    @property
    def marking(self):
        return self._marking

    @marking.setter
    def marking(self, marking):
        self._marking = marking

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    @property
    def omap(self):
        return _omap

    @omap.setter
    def omap(self, omap):
        self._omap = omap

# class DigitalTwin(object):
#     def __init__(self, ocpn, valves, guards):
#         self.ocpn = ocpn
#         self.valves = valves
#         self.guards = guards
