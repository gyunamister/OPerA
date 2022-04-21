from dataclasses import dataclass, field
# from dtween.digitaltwin.ocpn.objects.obj import ObjectCentricPetriNet
from ocpa.objects.oc_petri_net.obj import ObjectCentricPetriNet
from ocpa.objects.oc_petri_net.obj import Marking
# from dtween.digitaltwin.ocpn.objects.obj import Marking
from typing import List, Dict, Any, Optional, Set, Tuple
from dtween.digitaltwin.digitaltwin.action_engine.obj import ActionEngine, Action
from dtween.digitaltwin.digitaltwin.control.obj import Valve, WriteOperation, ActivityVariant

import re


@dataclass
class Guard(object):
    expression: str
    transition: ObjectCentricPetriNet.Transition
    valves: Set[Valve]

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, guard):
        return self.expression == guard.expression and self.transition == guard.transition and self.valves == guard.valves


class DigitalTwin(object):
    _ocpn: ObjectCentricPetriNet
    _valves: Set[Valve]
    _guards: Set[Guard]
    _writes: Set[WriteOperation]
    _write_operations: Set[WriteOperation]
    _activity_variants: Set[ActivityVariant]
    _marking: Marking
    _action_engine: ActionEngine
    _default_control: Tuple[Set[Valve], Set[WriteOperation]]

    def __init__(self, ocpn, valves=set(), guards=set(), writes=set(), write_operations=set(), activity_variants=set(), marking=Marking(), action_engine=ActionEngine(), default_control=None):
        self._ocpn = ocpn
        self._valves = valves
        self._guards = guards
        self._writes = writes
        self._write_operations = write_operations
        self._activity_variants = activity_variants
        self._marking = marking
        self._action_engine = action_engine
        self._default_control = default_control
    # _config: Dict[str, float] = field(default_factory=dict)
    # _omap: Dict[str, Any] = field(default_factory=dict)

    # log: Optional[ObjectCentricLog] = field(default_factory=lambda: None)

    @property
    def ocpn(self) -> ObjectCentricPetriNet:
        return self._ocpn

    @ocpn.setter
    def ocpn(self, ocpn: ObjectCentricPetriNet) -> None:
        self._ocpn = ocpn

    @property
    def valves(self) -> Set[Valve]:
        return self._valves

    @valves.setter
    def valves(self, valves: Set[Valve]) -> None:
        self._valves = valves

    @property
    def writes(self) -> Set[WriteOperation]:
        return self._writes

    @writes.setter
    def writes(self, writes: Set[WriteOperation]) -> None:
        self._writes = writes

    @property
    def write_operations(self) -> Set[WriteOperation]:
        return self._write_operations

    @write_operations.setter
    def write_operations(self, write_operations: Set[WriteOperation]) -> None:
        self._write_operations = write_operations

    @property
    def activity_variants(self) -> Set[ActivityVariant]:
        return self._activity_variants

    @activity_variants.setter
    def activity_variants(self, activity_variants: Set[ActivityVariant]) -> None:
        self._activity_variants = activity_variants

    @property
    def guards(self) -> Set[Guard]:
        return self._guards

    @guards.setter
    def guards(self, guards: Set[Guard]) -> None:
        self._guards = guards

    @property
    def action_engine(self) -> ActionEngine:
        return self._action_engine

    @action_engine.setter
    def action_engine(self, action_engine: ActionEngine) -> None:
        self._action_engine = action_engine

    # @property
    # def object_types(self):
    #     return list(set([pl.object_type for pl in self._ocpn.places]))

    @property
    def marking(self):
        return self._marking

    @marking.setter
    def marking(self, marking):
        self._marking = marking

    def set_default_control(self, valves, write_operations):
        self._default_control = (valves, write_operations)

    # @property
    # def omap(self):
    #     return self._omap

    # @omap.setter
    # def omap(self, omap):
    #     self._omap = omap

    def get_guard(self, transition: ObjectCentricPetriNet.Transition) -> Guard:
        for guard in self._guards:
            if guard.transition == transition:
                return guard
        return None

    def add_guard(self, tr_name: str, expression: str):
        transition = self._ocpn.find_transition(tr_name)
        temp_valves = re.findall("\{(.*?)\}", expression)
        valves = set([v for v in self._valves if v.name in temp_valves])

        guard = Guard(expression, transition, valves)
        self._guards.add(guard)

    def get_writes_by_names(self, write_names):
        writes = []
        for wn in write_names:
            for write in self._writes:
                if write.name == wn:
                    writes.add(write)
        return writes
        # return [write for wn in write_names for write in self._writes if write.name == wn]

    def update_valve(self, valve_name, current_value):
        for valve in self._valves:
            if valve.name == valve_name:
                valve.value = current_value

    def update_write(self, write_name, tr_name):
        for write in self._writes:
            if write.name == write_name:
                write.tr_name = tr_name

    def update_acvitiy_variant(self, tr_name, variant_name):
        for variant in self._activity_variants:
            if variant.name == variant_name:
                variant.tr_name = tr_name

    def get_writes_by_transition(self, tr_name):
        return [write for write in self._writes if write.tr_name == tr_name]

    def get_tokens_in_place(self, p: ObjectCentricPetriNet.Place):
        tokens_in_p = set()
        for (pl, oi) in self._marking.tokens:
            if pl == p:
                tokens_in_p.add((pl, oi))
        return tokens_in_p

    def relate_pre_places(self, t):
        results = {}
        results["pre_places"] = set()
        self._relate_pre_places(t, results)
        return results["pre_places"]

    def _relate_pre_places(self, t: ObjectCentricPetriNet.Transition, results: Dict[str, Set[ObjectCentricPetriNet.Place]]) -> None:
        if len(t.preset) == 0:
            return
        for pl in t.preset:
            results["pre_places"].add(pl)
            for pre_tr in pl.preset:
                tr_preset = pre_tr.preset
                results["pre_places"].update(tr_preset)
                self._relate_pre_places(pre_tr, results)
