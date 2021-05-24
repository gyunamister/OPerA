from dataclasses import dataclass
from typing import Any


@dataclass
class Valve(object):
    name: str
    cur: Any


class NumericalValve(Valve):
    def __init__(self, name, cur, r_min=None, r_max=None, **kwargs):
        self.name = name
        self.cur = cur
        self.r_min = r_min
        self.r_max = r_max
        if r_min is None:
            raise ValueError('r_min is missing')
        elif r_max is None:
            raise ValueError('r_max is missing')

    def __repr__(self):
        return "{}: current value: {} in [{},{}]".format(self.name, self.cur, self.r_min, self.r_max)


class TestValve(Valve):
    def __init__(self, name, cur, test=None, **kwargs):
        self.name = name
        self.cur = cur
        self.r_min = r_min
        self.r_max = r_max
        if test is None:
            raise ValueError('test is missing')
