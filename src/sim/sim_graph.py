from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Generic, TypeVar
from typing import TYPE_CHECKING

import sim.sim_model as smodel
from sim.utils import permuted

if TYPE_CHECKING:
    import sim.case
    import sim.utils
    import sim.model_parameters as params


class SimulationNode:

    def __init__(self, **kwargs) -> None:
        super(SimulationNode, self).__init__(**kwargs)

    def accept(self, case: sim.case.OCCase):
        pass


class WithPartner:

    def __init__(self, **kwargs) -> None:
        super(WithPartner, self).__init__(**kwargs)
        self.partner = kwargs.get('partner')


class SplittingNode(WithPartner, SimulationNode):

    def __init__(self, **kwargs):
        super(SplittingNode, self).__init__(**kwargs)
        self.successors = []

    @property
    def successors(self) -> List[SimulationNode]:
        return self._successors

    @successors.setter
    def successors(self, value: List[SimulationNode]):
        self._successors = value


class AndSplit(SplittingNode):

    def accept(self, case: sim.case.OCCase):
        for successor in permuted(self.successors):
            successor.accept(case)


class DecisionNode(SplittingNode):

    def __init__(self, classifier: params.CaseClassifier = None, **kwargs):
        super(DecisionNode, self).__init__(**kwargs)
        self.classifier = classifier

    @property
    def classifier(self) -> params.CaseClassifier:
        return self._classifier

    @classifier.setter
    def classifier(self, value: params.CaseClassifier):
        self._classifier = value


class MultiDecisionNode(SplittingNode):

    def __init__(self, classifier: params.MultiDecisionClassifier = None, **kwargs):
        super(MultiDecisionNode, self).__init__(**kwargs)
        self.classifier = classifier

    @property
    def classifier(self) -> params.MultiDecisionClassifier:
        return self._classifier

    @classifier.setter
    def classifier(self, value: params.MultiDecisionClassifier):
        self._classifier = value


class XorSplit(DecisionNode):

    def __init__(self, classifier: params.CaseClassifier = None, **kwargs):
        super().__init__(classifier, **kwargs)

    def accept(self, case: sim.case.OCCase):
        self.successors[self.classifier.classify(case)].accept(case)


class OrSplit(MultiDecisionNode):

    def __init__(self, multi_classifier: params.MultiDecisionClassifier = None, **kwargs):
        super().__init__(multi_classifier, **kwargs)

    def accept(self, case: sim.case.OCCase):
        for i in self.classifier.classify(case):
            self.successors[i].accept(case)


class LinearNode(SimulationNode):

    def __init__(self, successor: SimulationNode = None, **kwargs) -> None:
        super(LinearNode, self).__init__(**kwargs)
        self.successor = successor

    @property
    def successor(self):
        return self._successor

    @successor.setter
    def successor(self, value):
        self._successor = value

    def accept(self, case: sim.case.OCCase):
        self.submit(case)  # default

    def submit(self, case: sim.case.OCCase):
        self.successor.accept(case)


ModelType = TypeVar('ModelType', bound=smodel.SimulationNodeModel)


class WithModel(ABC, Generic[ModelType]):

    def __init__(self, model: ModelType = None, **kwargs) -> None:
        super(WithModel, self).__init__(**kwargs)
        self.__model = model

    @property
    def model(self) -> ModelType:
        return self.__model

    @model.setter
    def model(self, value: ModelType):
        assert value is not None
        self.__model = value

    @abstractmethod
    def accept_from_model(self, case: sim.case.OCCase):
        pass


class LinearNodeWithModel(LinearNode, WithModel[ModelType]):

    def __init__(self, **kwargs) -> None:
        super(LinearNodeWithModel, self).__init__(**kwargs)

    def accept(self, case: sim.case.OCCase):
        self.model.accept(case)

    def accept_from_model(self, case: sim.case.OCCase):
        self.submit(case)


class TauNode(LinearNode):
    pass


class JoiningNode(WithPartner, LinearNode):
    pass


class AndJoin(JoiningNode):

    def __init__(self, parallel_splits: int, **kwargs) -> None:
        super(AndJoin, self).__init__(**kwargs)
        self.parallel_splits = parallel_splits
        self.arrival_counts = defaultdict(int)

    def accept(self, case: sim.case.OCCase):
        self.arrival_counts[case] += 1
        logging.info(
            f'AndJoin accepted {case.case_id} ({self.arrival_counts[case]}>={self.parallel_splits})')
        if self.arrival_counts[case] >= self.parallel_splits:
            del self.arrival_counts[case]
            logging.info(f'AndJoin submitted {case.case_id}')
            self.submit(case)


class XorJoin(JoiningNode):
    pass


class OrJoin(JoiningNode):

    def __init__(self, **kwargs) -> None:
        super(OrJoin, self).__init__(**kwargs)
        self.arrival_counts = defaultdict(int)
        self.expected_arrivals = {}

    def set_expectation(self, case: sim.case.OCCase, expected_arrivals: int):
        self.expected_arrivals[case] = expected_arrivals

    def accept(self, case: sim.case.OCCase):
        self.arrival_counts[case] += 1
        if self.arrival_counts[case] >= self.expected_arrivals[case]:
            del self.arrival_counts[case]
            del self.expected_arrivals[case]
            self.submit(case)


class DelayNode(LinearNodeWithModel[smodel.DelayModel]):
    pass


class ArrivalNode(LinearNodeWithModel[smodel.ArrivalModel]):
    pass


class TerminalNode(SimulationNode, WithModel[smodel.TerminalModel]):

    def accept(self, case: sim.case.OCCase):
        self.model.accept(case)

    def accept_from_model(self, case: sim.case.OCCase):
        pass


class ActivityNode(LinearNodeWithModel[smodel.ActivityModel]):

    def __init__(self, label: str, **kwargs) -> None:
        super(ActivityNode, self).__init__(**kwargs)
        self.label = label


@dataclass(unsafe_hash=True)
class SimulationGraph:
    arrival: ArrivalNode
    terminal: TerminalNode
    activity_map: Dict[str, ActivityNode]
    decision_map: Dict[str, DecisionNode]
