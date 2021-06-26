from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple


@dataclass
class Order(object):
    _oid: str
    _price: float = None
    _customer: str = "Adams"
    placement: bool = None
    invoice: bool = None
    notification: bool = None
    payment: bool = None

    @property
    def oid(self):
        return self._oid

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, price):
        self._price = price

    @property
    def customer(self):
        return self._customer

    def get_info(self):
        return {self._oid: {"ocel:type": "order", "ocel:ovmap": {"price": self._price}}}


@dataclass
class Item(object):
    _oid: str
    _category: str = "S"
    _material: str = "Apple"
    _quantity: int = 3
    approved: bool = None
    picking: bool = None

    @property
    def oid(self):
        return self._oid

    @property
    def category(self):
        return self._category

    @property
    def material(self):
        return self._material

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, quantity):
        self._quantity = quantity

    def get_info(self):
        return {self._oid: {"ocel:type": "item", "ocel:ovmap": {"ocel:quantity": self._quantity}}}


@dataclass
class Route(object):
    _oid: str
    _amount: int = 3
    _area: str = "a"
    start: bool = None
    end: bool = None

    @property
    def oid(self):
        return self._oid

    @property
    def amount(self):
        return self._amount

    @property
    def area(self):
        return self._area

    def get_info(self):
        return {self._oid: {"ocel:type": "route", "ocel:ovmap": {}}}
