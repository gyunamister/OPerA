from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Set, Tuple, Dict
from dtween.digitaltwin.digitaltwin.control.obj import Valve, NumericalValve, ActivityVariant

from dtween.digitaltwin.impact_analysis.factory import analyze_pre_impact, analyze_post_impact, analyze_impacted_run_entities, analyze_impacted_conf_entities
from dtween.available.available import AvailableObjPerformanceMetric, AvailableFuncPerformanceMetric
from dtween.util.util import REPLAY_DIAGNOSTICS_MAP

from ocpa.algo.enhancement.token_replay_based_performance import algorithm as diagnostics_factory

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dtween.digitaltwin.digitaltwin.objects.obj import DigitalTwin


class ActionType(object):
    ...


@dataclass
class ValveAction(object):
    name: str
    value: object

    def __repr__(self):
        return "Change value of {} to {}".format(self.name, self.value)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, action):
        return self.name == action.name and self.value == action.value


@dataclass
class WriteOperationAction(object):
    name: str
    tr_name: str

    def __repr__(self):
        return f'Now {self.tr_name} writes {self.name})'

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, action):
        return self.name == action.name and self.tr_name == action.tr_name


@dataclass
class ActivityVariantAction(object):
    tr_name: str
    variant_name: str

    def __repr__(self):
        return f'Now {self.tr_name} uses {self.variant_name})'

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, action):
        return self.variant_name == action.variant_name and self.tr_name == action.tr_name


@dataclass
class Action(object):
    name: str

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, action):
        return self.name == action.name


@dataclass
class StaticAction(Action):
    name: str
    valve_actions: List[ValveAction] = None
    # write_operation_actions: List[WriteOperationAction] = None
    activity_variant_actions: List[ActivityVariantAction] = None

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, action):
        return self.name == action.name


@dataclass
class Constraint(object):
    name: str

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, constraint):
        return self.name == constraint.name


@dataclass
class ActionInstance(object):
    action: Action
    start: int
    end: int
    name: str = None
    pre_impact: Dict[str, float] = None
    post_obj_impact: Dict[str, Dict[str, float]] = None
    post_func_impact: Dict[str, Dict[str, float]] = None
    impacted_objects: Set[str] = None
    impacted_functions: Set[str] = None
    impacted_obj_instances: Set[str] = None
    impacted_func_instances: Set[str] = None
    _pre_action_obj_diagnostics = None
    _pre_action_func_diagnostics = None
    _post_action_obj_diagnostics = None
    _post_action_func_diagnostics = None

    def __post_init__(self):
        self.name = self.action.name + \
            '[' + str(self.start) + ',' + str(self.end) + ']'

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, ai):
        return self.action == ai.action, self.start == ai.start, self.end == ai.end

    def extract_diagnostics(self, diagnostics_data, selected_diagnostics, entities):
        diagnostics = {}
        for diag in selected_diagnostics:
            # for diag in diagnostics_data:
            replay_diag = selected_diagnostics[diag]
            if replay_diag in diagnostics_data.keys():
                # change the name of diagnostics
                diagnostics[diag] = {}
                for element in diagnostics_data[replay_diag]:
                    for entity in entities:
                        if entity in element:
                            diagnostics[diag][element] = diagnostics_data[replay_diag][element]
        print(diagnostics)
        return diagnostics

    @property
    def pre_action_obj_diagnostics(self):
        return self._pre_action_obj_diagnostics

    @pre_action_obj_diagnostics.setter
    def pre_action_obj_diagnostics(self, diagnostics_data):
        selected_diagnostics = {opm.value: REPLAY_DIAGNOSTICS_MAP[opm.value]
                                for opm in AvailableObjPerformanceMetric}
        entities = self.impacted_objects
        self._pre_action_obj_diagnostics = self.extract_diagnostics(
            diagnostics_data, selected_diagnostics, entities)

    @property
    def pre_action_func_diagnostics(self):
        return self._pre_action_func_diagnostics

    @pre_action_func_diagnostics.setter
    def pre_action_func_diagnostics(self, diagnostics_data):
        selected_diagnostics = {opm.value: REPLAY_DIAGNOSTICS_MAP[opm.value]
                                for opm in AvailableFuncPerformanceMetric}
        entities = [tr.name for tr in self.impacted_functions]
        self._pre_action_func_diagnostics = self.extract_diagnostics(
            diagnostics_data, selected_diagnostics, entities)

    @property
    def post_action_obj_diagnostics(self):
        return self._post_action_obj_diagnostics

    @post_action_obj_diagnostics.setter
    def post_action_obj_diagnostics(self, diagnostics_data):
        selected_diagnostics = {opm.value: REPLAY_DIAGNOSTICS_MAP[opm.value]
                                for opm in AvailableObjPerformanceMetric}
        entities = self.impacted_objects
        self._post_action_obj_diagnostics = self.extract_diagnostics(
            diagnostics_data, selected_diagnostics, entities)

    @property
    def post_action_func_diagnostics(self):
        return self._post_action_func_diagnostics

    @post_action_func_diagnostics.setter
    def post_action_func_diagnostics(self, diagnostics_data):
        selected_diagnostics = {opm.value: REPLAY_DIAGNOSTICS_MAP[opm.value]
                                for opm in AvailableFuncPerformanceMetric}
        entities = [tr.name for tr in self.impacted_functions]
        self._post_action_func_diagnostics = self.extract_diagnostics(
            diagnostics_data, selected_diagnostics, entities)

    def get_obj_impact_diagnostics(self, entity_name, diag_name):
        if diag_name not in self.post_obj_impact:
            return []
        obj_impact_diagnostics = [
            d for d in self.post_obj_impact[diag_name] if entity_name in d]
        return obj_impact_diagnostics

    def get_func_impact_diagnostics(self, entity_name, diag_name):
        if diag_name not in self.post_func_impact:
            return []
        func_impact_diagnostics = [
            str(d) for d in self.post_func_impact[diag_name] if entity_name in str(d)]
        return func_impact_diagnostics


class ActionEngine(object):
    action_repo: Set[Action] = []
    constraint_repo: Set[Constraint]
    action_pattern_repo: Set[Tuple[Set[Constraint], Set[Action]]]
    action_instances: Set[ActionInstance]

    def __init__(self, action_repo=set(), constraint_repo=set(), action_pattern_repo=set(), action_instances=set()):
        self._action_repo = action_repo
        self._constraint_repo = constraint_repo
        self._action_pattern_repo = action_pattern_repo
        self._action_instances = action_instances

    @property
    def action_repo(self):
        return self._action_repo

    @property
    def constraint_repo(self):
        return self._constraint_repo

    @property
    def action_instances(self):
        return self._action_instances

    def add_action_instance(self, action_name: str, start: int, end: int) -> ActionInstance:
        for action in self._action_repo:
            if action_name == action.name:
                action_instance = ActionInstance(action, start, end)
                self._action_instances.add(action_instance)
                print(f'{action_instance} is added to action engine.')
                return action_instance
        raise ValueError(
            f'{action_name} does not exist in the action repository')

    def add_constraint(self, constraint):
        self._constraint_repo.add(constraint)

    def add_action(self, action):
        self._action_repo.add(action)

    def apply_default_configuration(self, valves: Set[Valve], activity_variants: Set[ActivityVariant]):
        for v in valves:
            v.value = v.default
        for av in activity_variants:
            av.tr_name = av.default
        print(
            f'Set default configuration. \n Valve: \n {valves} \n Activity Variant: \n {activity_variants}')
        return valves, activity_variants

    def get_action_instance(self, name):
        for action_instance in self._action_instances:
            if action_instance.name == name:
                # if action_name == action_instance.action.name and time >= action_instance.start and time <= action_instance.end:
                return action_instance

    def apply_action(self, action, valves: Set[Valve], activity_variants: Set[ActivityVariant]):
        for v_action in action.valve_actions:
            for v in valves:
                if v_action.name == v.name:
                    v.value = v_action.value

        for av_action in action.activity_variant_actions:
            # cancel previous activity variant mapping
            for av in activity_variants:
                if av_action.tr_name == av.tr_name:
                    av.tr_name = None
            # assign new activity variant mapping
            for av in activity_variants:
                if av_action.variant_name == av.name:
                    av.tr_name = av_action.tr_name
        print(
            f'Apply action. \n Valve: \n {valves} \n Activity Variants: \n {activity_variants}')

    def apply_action_instance(self, dt: DigitalTwin, time: int, ocel):
        print(f'Apply action instances at {time}')
        dt.valves, dt.activity_variants = self.apply_default_configuration(
            dt.valves, dt.activity_variants)

        action_instances_at_t = [
            action_instance for action_instance in self._action_instances if action_instance.start <= time and action_instance.end >= time]
        for ai in action_instances_at_t:
            if ai.start == time:
                ai.impacted_objects, ai.impacted_functions = analyze_impacted_conf_entities(
                    dt, ai)
                ai.impacted_obj_instances, ai.impacted_func_instances = analyze_impacted_run_entities(
                    dt, ai)
                ai.pre_impact = analyze_pre_impact(
                    dt, ai)
                print(f'Pre-impact score: {ai.pre_impact}')
                # FIXME: conceptually digital twin must contain all diagnostics, but it is infeasible. Thus, we store diagnostics to each action instances as pre and post diagnostics.
                diagnostics = diagnostics_factory.apply(dt.ocpn, ocel)
                ai.pre_action_obj_diagnostics = diagnostics
                ai.pre_action_func_diagnostics = diagnostics

            elif ai.end == time:
                diagnostics = diagnostics_factory.apply(dt.ocpn, ocel)
                ai.post_action_obj_diagnostics = diagnostics
                ai.post_action_func_diagnostics = diagnostics
                ai.post_obj_impact, ai.post_func_impact = analyze_post_impact(
                    ai)
            self.apply_action(ai.action, dt.valves, dt.activity_variants)

    def clear_action_instances(self):
        self._action_instances = set()
