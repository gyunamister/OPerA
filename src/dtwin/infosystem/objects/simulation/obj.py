from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from dtwin.infosystem.objects.objects.obj import Order, Item, Route


@dataclass
class ProcessInstance(object):
    _pid: str
    _order: Order
    _items: List[int]
    _route: Route

    @property
    def pid(self):
        return self._pid

    @property
    def order(self):
        return self._order

    @property
    def items(self):
        return self._items

    @property
    def route(self):
        return self._route
