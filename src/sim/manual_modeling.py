import datetime
from datetime import timedelta, datetime
from numbers import Number
from typing import List, Tuple, Dict, Iterator, Set, Union

from sim import parameter_implementations as pimpls, time_utils
from sim.model_configuration import ArrivalProcessConfig, ActivityConfig, ResourceConfig, DecisionConfig, MappingConfig, \
    ModelConfiguration, ObjectConfig
from sim.sim_graph import ArrivalNode, TerminalNode, ActivityNode, XorSplit, XorJoin, AndSplit, AndJoin, \
    SimulationGraph, LinearNode, SplittingNode, TauNode

splitting_node_suffix = '_split'
joining_node_suffix = '_join'


def base_of(label):
    return label.rsplit('_', 1)[0]


def split_of(label):
    return label + splitting_node_suffix


def join_of(label):
    return label + joining_node_suffix


def gen_suffixed(label):
    return split_of(label), join_of(label)


class GraphBuilder:

    def __init__(self, initial_graph: SimulationGraph = None) -> None:
        self.nodes = {}
        self.activity_nodes = {}
        self.sync_points = {}
        self.decision_points = {}
        self.decision_id = 1
        self.concurrency_id = 1
        self.tau_id = 1

        if initial_graph is not None:
            self.initialize_with_graph(initial_graph)
        else:
            self.add_node('arrival', ArrivalNode())
            self.add_node('terminal', TerminalNode())

    def initialize_with_graph(self, initial_graph):
        node_label_map = {}
        last_added_and, last_added_xor = 1, 1
        revved = {v: k for k, v in initial_graph.decision_map.items()}
        relabel_m = {}
        decisions = {}
        for node in iterate_graph_nodes(initial_graph):
            label = None
            if isinstance(node, AndSplit):
                label = f'parsed_concurrency_{last_added_and}_split'
                self.add_node(label, AndSplit())
                last_added_and += 1
            elif isinstance(node, XorSplit):
                decision_label = revved[node]
                # f'parsed_decision_{last_added_xor}_split'
                label = split_of(decision_label)
                relabel_m[label] = decision_label
                decisions[node] = label
                self.add_node(label, XorSplit(), is_decision=True)
                last_added_xor += 1
            elif isinstance(node, AndJoin):
                label = f'parsed_concurrency_{last_added_and}_join'
                self.add_node(label, AndJoin(
                    parallel_splits=node.parallel_splits), is_synchronizer=True)
                last_added_and += 1
            elif isinstance(node, XorJoin):
                label = f'parsed_decision_{last_added_xor}_join'
                self.add_node(label, XorJoin())
                last_added_xor += 1
            elif isinstance(node, TauNode):
                label = self.add_tau()
            elif isinstance(node, ActivityNode):
                label = self.add_activity(node.label)
            elif isinstance(node, ArrivalNode):
                label = self.add_node('arrival', ArrivalNode())
            elif isinstance(node, TerminalNode):
                label = self.add_node('terminal', TerminalNode())
            if label is not None:
                node_label_map[node] = label

        # relabel_map = {label: revved[node] for node, label in decisions.items()}
        for node in iterate_graph_nodes(initial_graph):
            if isinstance(node, LinearNode):
                self.connect(node_label_map[node],
                             node_label_map[node.successor])
            if isinstance(node, SplittingNode):
                self.connect(node_label_map[node], [
                             node_label_map[s] for s in node.successors])

    def add_node(self, label, node, is_decision=False, is_activity=False, is_synchronizer=False, initial_node=False,
                 final_node=False) -> str:
        assert label not in self.nodes
        self.nodes[label] = node
        if is_decision:
            self.decision_points[base_of(label)] = node
        if is_activity:
            self.activity_nodes[label] = node
        if is_synchronizer:
            self.sync_points[base_of(label)] = node
        if initial_node:
            self.set_as_initial(label)
        if final_node:
            self.set_as_final(label)
        return label

    def add_activity(self, label, **kwargs) -> str:
        return self.add_node(label, ActivityNode(label), is_activity=True, **kwargs)

    def add_activities(self, *labels) -> Iterator[str]:
        for label in labels:
            yield self.add_activity(label)

    def add_decision(self, label=None, initial_node=False, final_node=False) -> str:
        assert label not in self.decision_points
        if label is None:
            label = f'xor{self.decision_id}'
            self.decision_id += 1
        split_label, join_label = gen_suffixed(label)
        split = XorSplit()
        join = XorJoin()
        split.partner = join
        join.partner = split
        self.add_node(split_label, split, is_decision=True,
                      initial_node=initial_node)
        self.add_node(join_label, join, final_node=final_node)
        return label

    def add_concurrency(self, label=None, number_of_splits=2, initial_node=False, final_node=False) -> str:
        assert label not in self.sync_points
        if label is None:
            label = f'and{self.concurrency_id}'
            self.concurrency_id += 1
        split_label, join_label = gen_suffixed(label)
        split = AndSplit()
        join = AndJoin(number_of_splits)
        split.partner = join
        join.partner = split
        self.add_node(split_label, split, initial_node=initial_node)
        self.add_node(join_label, join, is_synchronizer=True,
                      final_node=final_node)
        return label

    def add_tau(self, initial_node=False, final_node=False) -> str:
        label = f'tau_{self.tau_id}'
        self.tau_id += 1
        self.add_node(label, TauNode(), initial_node=initial_node,
                      final_node=final_node)
        return label

    def get_corresponding_node(self, label, as_successor=False):
        # if label not in self.nodes:  # incorrect
        #    label = split_of(label) if as_successor else join_of(label)
        return self.nodes.get(label)

    def connect(self, from_labels, to_labels):
        if isinstance(from_labels, List):
            for f_l in from_labels:
                f_n = self.get_corresponding_node(f_l)
                if isinstance(to_labels, List):
                    f_n.successors = [self.get_corresponding_node(
                        n, as_successor=True) for n in to_labels]
                else:
                    f_n.successor = self.get_corresponding_node(
                        to_labels, as_successor=True)
        else:
            f_n = self.get_corresponding_node(from_labels)
            if isinstance(to_labels, List):
                f_n.successors = [self.get_corresponding_node(
                    n, as_successor=True) for n in to_labels]
            else:
                f_n.successor = self.get_corresponding_node(
                    to_labels, as_successor=True)

    def set_as_initial(self, label):
        self.connect('arrival', label)

    def set_as_final(self, labels):
        self.connect(labels, 'terminal')

    def relabel_decision_points(self, decision_point_spec):
        for k, v in decision_point_spec.items():
            self.decision_points[v] = self.decision_points[k]
            del self.decision_points[k]

    def build(self, decision_point_spec=None) -> SimulationGraph:
        if decision_point_spec is not None:
            self.relabel_decision_points(decision_point_spec)
        # important to fix this if misconfigured by user
        for label, and_join in self.sync_points.items():
            corresponding_node = self.get_corresponding_node(split_of(label))
            if corresponding_node is not None:
                number_of_splits = len(corresponding_node.successors)
                if and_join.parallel_splits is None or number_of_splits > and_join.parallel_splits:
                    and_join.parallel_splits = number_of_splits
        graph = SimulationGraph(self.nodes['arrival'], self.nodes['terminal'], self.activity_nodes,
                                self.decision_points)
        graph_assertions(graph)
        return graph


def config_assertions(graph: SimulationGraph, config: ModelConfiguration):
    assert graph.activity_map.keys() == config.activities.keys()
    assert graph.decision_map.keys() == config.decisions.keys()


class ModelBuilder(GraphBuilder):

    def __init__(self, initial_graph: SimulationGraph = None, initial_config: ModelConfiguration = None) -> None:
        self.arrival_configs: Dict[str,
                                   ArrivalProcessConfig] = ModelBuilder.default_arrival_config()
        self.activity_configs: Dict[str, ActivityConfig] = {}
        self.resource_configs: Dict[str, ResourceConfig] = {}
        self.decision_configs: Dict[str, DecisionConfig] = {}
        self.object_configs: Dict[str, ObjectConfig] = {}
        self.working_assignments = {}
        self.working_propensities = None
        super(ModelBuilder, self).__init__(initial_graph)

        if initial_config is not None:
            self.initialize_with_config(initial_config)
        elif initial_graph is not None:
            for decision, node in initial_graph.decision_map.items():
                i = len(node.successors)
                self.decision_configs[decision] = DecisionConfig(
                    pimpls.StochasticClassifier([1 / i] * i))

    def initialize_with_config(self, config: ModelConfiguration):
        self.arrival_configs = config.arrivals
        self.decision_configs = dict(config.decisions)
        self.activity_configs = dict(config.activities)
        self.resource_configs = dict(config.resources)
        self.working_assignments = dict(config.mapping.assignable_resources)
        if config.mapping.propensities is not None:
            self.working_propensities = dict(config.mapping.propensities)
        if config.objects is not None:
            self.object_configs = dict(config.objects)

    @staticmethod
    def default_arrival_config():
        return {'default': ArrivalProcessConfig(time_utils.now(), pimpls.StaticSampler(timedelta(hours=1)))}

    @staticmethod
    def default_activity_config():
        return ActivityConfig(pimpls.Fifo, pimpls.StaticSampler(timedelta(hours=1)))

    @staticmethod
    def default_resource_config():
        return ResourceConfig(1)

    def add_activity(self, label, config=None, assignable_resources=None, resource_propensities=None,
                     initial_node=False, final_node=False,
                     **kwargs) -> str:
        super().add_activity(label, initial_node=initial_node, final_node=final_node, **kwargs)
        self.activity_configs[label] = config if config is not None else ModelBuilder.default_activity_config(
        )
        if assignable_resources is not None:
            if isinstance(assignable_resources, str):
                assignable_resources = {assignable_resources}
            resource_propensities_ = resource_propensities
            if resource_propensities is None:
                resource_propensities_ = [
                    1.0 / len(assignable_resources)] * len(assignable_resources)
            elif isinstance(resource_propensities, Number):
                resource_propensities_ = [resource_propensities]
            s = set()
            props = {}
            for r, p in zip(assignable_resources, resource_propensities_):
                if r not in self.resource_configs:
                    self.add_resource(r)
                s.add(r)
                props[r] = p
            if resource_propensities is not None:  # TODO inefficient as it is computed anyways
                if self.working_propensities is None:
                    self.working_propensities = {}
                self.working_propensities[label] = props
            self.working_assignments[label] = s
        return label

    def add_activities(self, *labels) -> Iterator[str]:
        for label in labels:
            yield self.add_activity(label)

    def set_object_config(self, config: ObjectConfig) -> None:
        self.object_configs = config

    def set_default_arrival_config(self, config: ArrivalProcessConfig) -> None:
        self.arrival_configs['default'] = config

    def add_arrival_config(self, label: str, config: ArrivalProcessConfig) -> None:
        assert label not in self.arrival_configs
        self.arrival_configs[label] = config

    def set_arrival_configs(self, configs: Dict[str, ArrivalProcessConfig]) -> None:
        self.arrival_configs = configs

    def set_assignments(self, config: Union[MappingConfig, Dict[str, Set[str]]]):
        if isinstance(config, MappingConfig):
            self.working_assignments = config.assignable_resources
            self.working_propensities = config.propensities
        else:
            self.working_assignments = config

    def set_assignment_propensities(self, config):
        self.working_propensities = config.propensities

    def set_config(self, label, config):
        if label == 'arrival':
            self.set_default_arrival_config(config)
        if label == 'arrivals':
            self.set_arrival_configs(config)
        elif label == 'propensities':
            self.set_assignment_propensities(config)
        elif label == 'assignments':
            self.set_assignments(config)
        elif label in self.activity_nodes:
            self.activity_configs[label] = config
        elif label in self.decision_points:
            self.decision_configs[label] = config
        elif label in self.resource_configs:
            self.resource_configs[label] = config

    def add_decision(self, label=None, config=None, **kwargs) -> str:
        label = super().add_decision(label, **kwargs)
        if config is not None:
            self.decision_configs[label] = config
        return label

    def add_resource(self, label, config=None, assignable_activities=None) -> str:
        assert label not in self.resource_configs
        self.resource_configs[label] = config if config is not None else ModelBuilder.default_resource_config(
        )
        if assignable_activities is not None:
            if isinstance(assignable_activities, str):
                assignable_activities = [assignable_activities]
            for a in assignable_activities:
                if a not in self.activity_configs:
                    self.add_activity(a)
                if a not in self.working_assignments:
                    self.working_assignments[a] = {}
                self.working_assignments[a].add(label)
        return label

    def relabel_decision_points(self, decision_point_spec):
        super().relabel_decision_points(decision_point_spec)
        for k, v in decision_point_spec.items():
            self.decision_configs[v] = self.decision_configs[k]
            del self.decision_configs[k]

    def __get_mapping_config(self):
        return MappingConfig(self.working_assignments, propensities=self.working_propensities)

    def build(self, decision_point_spec=None) -> Tuple[SimulationGraph, ModelConfiguration]:
        graph = super().build(decision_point_spec)
        config = ModelConfiguration(self.arrival_configs, self.activity_configs, self.resource_configs,
                                    self.decision_configs, self.__get_mapping_config(), self.object_configs)
        config_assertions(graph, config)
        return graph, config


def iterate_graph_nodes(graph: SimulationGraph):
    todo = [graph.arrival]
    seen = set()

    while len(todo) > 0:
        current = todo.pop()

        yield current

        seen.add(current)

        if isinstance(current, LinearNode):
            succ = current.successor
            if succ not in seen:
                todo.append(succ)
        elif isinstance(current, SplittingNode):
            for succ in current.successors:
                if succ not in seen:
                    todo.append(succ)


def graph_assertions(graph: SimulationGraph):
    for node in iterate_graph_nodes(graph):
        if isinstance(node, LinearNode):
            assert node.successor is not None
        elif isinstance(node, SplittingNode):
            assert node.successors is not None
        # if isinstance(node, WithModel):
        #    assert node.model is not None
        # if isinstance(node, DecisionNode):
        #    assert node.classifier is not None
