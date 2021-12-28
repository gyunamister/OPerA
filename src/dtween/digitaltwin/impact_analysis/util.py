from __future__ import annotations

from dtween.digitaltwin.digitaltwin.control.obj import Valve, WriteOperation
from typing import List, Set, Any, Optional, Tuple
from ocpa.objects.oc_petri_net.obj import ObjectCentricPetriNet

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dtween.digitaltwin.digitaltwin.action_engine.obj import Action, ActionInstance
    from dtween.digitaltwin.digitaltwin.objects.obj import DigitalTwin
# def compute_changes(dt: DigitalTwin, action: Action) -> Tuple[Set[Valve], Set[WriteOperation]]:
#     changed_valves = [v for v in dt.valves for v_action in action.valve_actions if v.name ==
#                       v_action.name and v.value != v_action.value]
#     changed_write_operations = [
#         w for w in dt.writes for w_action in action.write_operation_actions if w.name == w_action.name and w.tr_name != w_action.tr_name]
#     return changed_valves, changed_write_operations


def compute_effective_actions(action: Action, valves: Set[Valve], writes: Set[WriteOperation]) -> Tuple[Set[Valve], Set[WriteOperation]]:
    effective_valve_actions = set([v_action for v_action in action.valve_actions for v in valves if v.name ==
                                   v_action.name and v.value != v_action.value])
    effective_write_operation_actions = set([
        w_action for w_action in action.write_operation_actions for w in writes if w.name == w_action.name and w.tr_name != w_action.tr_name])
    return effective_valve_actions, effective_write_operation_actions


def compute_impacted_functions(dt: DigitalTwin, effective_valve_actions: Set[Valve], effective_write_operation_actions: Set[WriteOperation]) -> Set[ObjectCentricPetriNet.Transition]:
    rel_tr_v = set()
    for v_action in effective_valve_actions:
        for g in dt.guards:
            if v_action.name in [v.name for v in g.valves]:
                rel_tr_v.add(g.transition)
                print(f'{v_action} is effective -> {g.transition} is affected.')
    # relevant transitions of changes in write operations
    rel_tr_w = set()
    for w_action in effective_write_operation_actions:
        print(f'{w_action} is effective -> {w_action.tr_name} is affected.')
        rel_tr_w.add(dt.ocpn.find_transition(w_action.tr_name))
    # rel_tr_w = set([dt.ocpn.find_transition(
    #     wo.tr_name) for wo in effective_write_operation_actions])
    return rel_tr_v.union(rel_tr_w)


def compute_impacted_objects(dt: DigitalTwin, effective_write_operation_actions: Set[WriteOperation]) -> Set[str]:
    return set([wo.object_type for w_action in effective_write_operation_actions for wo in dt.writes if w_action.name == wo.name])


def compute_impacted_object_instances(dt: DigitalTwin, ai: ActionInstance):
    impacted_object_types = ai.impacted_objects
    impacted_object_instances = set()
    for ot in impacted_object_types:
        for pl in dt.ocpn.places:
            if pl.object_type == ot:
                impacted_object_instances.update(dt.get_tokens_in_place(pl))
    return impacted_object_instances


def compute_impacted_function_instances(dt: DigitalTwin, ai: ActionInstance):
    impacted_function_instances = set()
    impacted_functions = ai.impacted_functions
    for tr in impacted_functions:
        for pl in dt.relate_pre_places(tr):
            impacted_function_instances.update(dt.get_tokens_in_place(pl))
    return impacted_function_instances
