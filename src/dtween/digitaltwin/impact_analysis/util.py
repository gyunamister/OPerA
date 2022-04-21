from __future__ import annotations

from dtween.digitaltwin.digitaltwin.control.obj import Valve, WriteOperation, ActivityVariant
from typing import List, Set, Any, Optional, Tuple
from ocpa.objects.oc_petri_net.obj import ObjectCentricPetriNet

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dtween.digitaltwin.digitaltwin.action_engine.obj import Action, ActionInstance, ActivityVariantAction, ValveAction
    from dtween.digitaltwin.digitaltwin.objects.obj import DigitalTwin


def old_compute_effective_actions(action: Action, valves: Set[Valve], writes: Set[WriteOperation]) -> Tuple[Set[Valve], Set[WriteOperation]]:
    effective_valve_actions = set([v_action for v_action in action.valve_actions for v in valves if v.name ==
                                   v_action.name and v.value != v_action.value])
    effective_write_operation_actions = set([
        w_action for w_action in action.write_operation_actions for w in writes if w.name == w_action.name and w.tr_name != w_action.tr_name])
    return effective_valve_actions, effective_write_operation_actions


def compute_effective_actions(action: Action, valves: Set[Valve], activity_variants: Set[ActivityVariant]) -> Tuple[Set[Valve], Set[WriteOperation]]:
    effective_valve_actions = set([v_action for v_action in action.valve_actions for v in valves if v.name ==
                                   v_action.name and v.value != v_action.value])
    effective_activity_variant_actions = set([
        av_action for av_action in action.activity_variant_actions for variant in activity_variants if variant.name == av_action.variant_name and variant.tr_name != av_action.tr_name])
    print(
        f'effective_valve_actions: {effective_valve_actions} \n effective_activity_variant_actions: {effective_activity_variant_actions}')
    return effective_valve_actions, effective_activity_variant_actions


def compute_impacted_functions(dt: DigitalTwin, effective_valve_actions: Set[ValveAction], effective_activity_variant_actions: Set[ActivityVariantAction]) -> Set[ObjectCentricPetriNet.Transition]:
    rel_tr_v = set()
    for v_action in effective_valve_actions:
        for g in dt.guards:
            if v_action.name in [v.name for v in g.valves]:
                rel_tr_v.add(g.transition)
                print(f'{v_action} is effective -> {g.transition} is affected.')
    # relevant transitions of changes in write operations
    rel_tr_w = set()
    for av_action in effective_activity_variant_actions:
        print(f'{av_action} is effective -> {av_action.tr_name} is affected.')
        rel_tr_w.add(dt.ocpn.find_transition(av_action.tr_name))
    # rel_tr_w = set([dt.ocpn.find_transition(
    #     wo.tr_name) for wo in effective_write_operation_actions])
    return rel_tr_v.union(rel_tr_w)


def compute_impacted_objects(dt: DigitalTwin, effective_activity_variant_actions: Set[ActivityVariantAction]) -> Set[str]:
    impacted_objects = set()
    for av_action in effective_activity_variant_actions:
        for variant in dt.activity_variants:
            if av_action.variant_name == variant.name:
                new_variant = variant
        for variant in dt.activity_variants:
            if av_action.tr_name == variant.tr_name:
                cur_variant = variant
        if cur_variant is None:
            cur_variant_writes = dict()
        else:
            cur_variant_writes = cur_variant.writes
        if new_variant is None:
            new_variant_writes = new_variant.writes
        else:
            new_variant_writes = new_variant.writes
    # if new_variant is None:
    #     raise ValueError(f'{av_action.variant_name} does not exist')
    # if cur_variant is None:
    #     raise ValueError(f'Variant assigned to {av_action.tr_name} does not exist')
        impacts = compute_symmetric_difference(
            cur_variant_writes, new_variant_writes)
        print(f'{av_action} is effective -> {impacts} is affected.')
        impacted_objects.update(impacts)
    return impacted_objects

    # return set([wo.object_type for w_action in effective_activity_variant_actions for variant in dt.activity_variants if w_action.name == variant.name])


def compute_symmetric_difference(writes_a, writes_b):
    object_types = [ot for ot in writes_a.keys()] + \
        [ot for ot in writes_b.keys()]
    symmetric_difference = set()
    for ot in object_types:
        if ot in writes_a and ot in writes_b:
            if writes_a[ot] == writes_b[ot]:
                continue
        symmetric_difference.add(ot)
    return symmetric_difference


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
