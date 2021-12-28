from dataclasses import dataclass
# from dtween.digitaltwin.ocpn.objects.obj import Marking
from typing import List, Dict, Any, Set


@dataclass
class Valve(object):
    name: str
    value: Any

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, valve):
        return self.name == valve.name and self.value == valve.value


class NumericalValve(Valve):
    def __init__(self, name, value, r_min=None, r_max=None, default=None, **kwargs):
        self.name = name
        self.value = value
        self.r_min = r_min
        self.r_max = r_max
        self.default = default
        if r_min is None:
            raise ValueError('r_min is missing')
        elif r_max is None:
            raise ValueError('r_max is missing')

    def __repr__(self):
        return "{}: current value: {} in [{},{}]".format(self.name, self.value, self.r_min, self.r_max)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, valve):
        return self.name == valve.name


@dataclass
class WriteOperation(object):
    name: str
    tr_name: str
    object_type: str
    attr_name: str
    default: str

    def __repr__(self):
        return f'{self.name}: {self.attr_name} of {self.object_type} by {self.tr_name}'

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, w):
        return self.name == w.name


@dataclass
class ActivityVariant(object):
    name: str
    writes: Dict[str, Set[str]]
    tr_name: str
    default: str

    def __repr__(self):
        return f'{self.name} is to write {self.writes} - assigned to {self.tr_name}'

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, variant):
        return self.name == variant.name
