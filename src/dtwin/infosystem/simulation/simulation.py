
import random
import json
import uuid

import simpy
import csv
from datetime import datetime, timedelta

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple


RANDOM_SEED = 42
NUM_MACHINES = 2  # Number of machines in the carwash
WASHTIME = 5      # Minutes it takes to clean a car
T_INTER = 48      # Create a car every ~7 minutes
SIM_TIME = 48    # Simulation time in minutes

results = []


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


# @dataclass
# class Configuration(object):
#     _config: dict[str, float] = field(default_factory=dict)

#     @property
#     def config(self):
#         return self._config

def record_object(file_name, info):
    with open(file_name, 'r+') as file:
        # First we load existing data into a dict.
        file_data = json.load(file)
        # Join new_dat3a with file_data
        file_data["ocel:objects"].update(info)
        # Sets file's current position at offset.
        file.seek(0)
        # convert back to json.
        json.dump(file_data, file, indent=4)


def record_process_instance(file_name, pi):
    order_info = pi.order.get_info()
    record_object(file_name, order_info)
    for item in pi.items:
        item_info = item.get_info()
        record_object(file_name, item_info)
    route_info = pi.route.get_info()
    record_object(file_name, route_info)


def setup(env, file_name, t_inter):
    """Create a carwash, a number of initial cars and keep creating cars
    approx. every ``t_inter`` minutes."""
    # Create the carwash

    # Create 4 initial cars
    config = {
        "po-price": 3,
        "sn-price": 200,
        "ap-quantity": 5
    }

    act_repo = ActivityRepository(env)

    for i in range(4):
        order = Order("o"+str(i), _price=random.randint(150, 250))
        items = [Item("i"+str(i)+"a", _quantity=random.randint(0, 10)),
                 Item("i"+str(i)+"b", _quantity=random.randint(0, 10))]
        route = Route("r"+str(i))
        process_instance = ProcessInstance("pid"+str(i), order, items, route)
        record_process_instance(file_name, process_instance)
        env.process(order_management(env, config, act_repo, process_instance))

    # Create more cars while the simulation is running
    while True:
        yield env.timeout(random.randint(t_inter - 2, t_inter + 2))
        i += 1
        order = Order("o"+str(i), _price=random.randint(150, 250))
        items = [Item("i"+str(i)+"a", _quantity=random.randint(0, 10)),
                 Item("i"+str(i)+"b", _quantity=random.randint(0, 10))]
        route = Route("r"+str(i))
        process_instance = ProcessInstance("pid"+str(i), order, items, route)
        record_process_instance(file_name, process_instance)
        env.process(order_management(env, config, act_repo, process_instance))

# class ActivityRepository(object):


class ActivityRepository(object):
    def __init__(self, env):
        self.env = env
        self.po_machine = simpy.Resource(env, 3)
        self.si_machine = simpy.Resource(env, 3)
        self.sn_machine = simpy.Resource(env, 3)
        self.cp_machine = simpy.Resource(env, 3)
        self.ap_machine = simpy.Resource(env, 3)
        self.pi_machine = simpy.Resource(env, 3)
        self.sr_machine = simpy.Resource(env, 3)
        self.er_machine = simpy.Resource(env, 3)
        self.po_time = 5
        self.ap_time = 5
        self.si_time = 5
        self.pi_time = 3
        self.sn_time = 10
        self.cp_time = 5
        self.sr_time = 3
        self.er_time = 3

    def place_order(self, obj):
        yield self.env.timeout(self.po_time)
        obj.placement = True

    def approve_picking(self, obj):
        yield self.env.timeout(self.ap_time)
        obj.approved = True

    def skip_approve_picking(self, obj):
        yield self.env.timeout(0)
        obj.approved = True

    def send_invoice(self, obj):
        yield self.env.timeout(self.si_time)
        obj.invoice = True

    def pick_item(self, obj):
        yield self.env.timeout(self.pi_time)
        obj.picking = True

    def send_notification(self, obj):
        yield self.env.timeout(self.sn_time)
        obj.notification = True

    def skip_send_notification(self, obj):
        yield self.env.timeout(0)
        obj.notification = True

    def collect_payment(self, obj):
        yield self.env.timeout(self.cp_time)
        obj.payment = True

    def start_route(self, obj):
        yield self.env.timeout(self.sr_time)
        obj.start = True

    def end_route(self, obj):
        yield self.env.timeout(self.er_time)
        obj.end = True


class ControlFlow(object):
    def __init__(self):
        pass

    def get_next_activity(self, config, pi):
        if pi.order.placement == None:
            return pi.order, "place_order", "po_machine", [pi.order.oid] + [item.oid for item in pi.items]
        elif any(item.approved == None for item in pi.items):
            for item in pi.items:
                if item.approved == None:
                    if item.quantity >= config["ap-quantity"]:
                        return item, "approve_picking", "ap_machine", [item.oid]
                    else:
                        return item, "skip_approve_picking", None, [item.oid]
        elif pi.order.invoice == None:
            return pi.order, "send_invoice", "si_machine", [pi.order.oid]
        elif any(item.picking == None for item in pi.items):
            for item in pi.items:
                if item.picking == None:
                    return item, "pick_item", "pi_machine", [item.oid]
        elif pi.order.notification == None:
            if pi.order.price >= config["sn-price"]:
                return pi.order, "send_notification", "sn_machine", [pi.order.oid]
            else:
                return pi.order, "skip_send_notification", None, [pi.order.oid]
        elif pi.order.payment == None:
            return pi.order, "collect_payment", "cp_machine", [pi.order.oid]
        elif pi.route.start == None:
            return pi.route, "start_route", "sr_machine", [pi.route.oid] + [item.oid for item in pi.items]
        elif pi.route.end == None:
            return pi.route, "end_route", "er_machine", [pi.route.oid] + [item.oid for item in pi.items]
        else:
            return None, None, None, None


def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='') as write_obj:
        # Create a writer object from csv module
        csv_writer = csv.writer(write_obj)
        # Add contents of list as last row in the csv file
        csv_writer.writerow(list_of_elem)


def record_event(file_name, record):
    with open(file_name, 'r+') as file:
        # First we load existing data into a dict.
        file_data = json.load(file)
        # Join new_dat3a with file_data
        file_data["ocel:events"].update(record)
        # Sets file's current position at offset.
        file.seek(0)
        # convert back to json.
        json.dump(file_data, file, indent=4)


def order_management(env, config, act_repo, process_instance):
    """
    :param env:  The simulation environment
    :param process_instance: Case ID
    :param net: The petrinet representing the process model
    :param initial_marking: The initial marking of the activities of the model
    :param no_traces: Number of traces that needs to be generated, given by the user
    """
    # file_name = './simulated-logs.csv'
    file_name = "./simulated-logs.jsonocel"

    control_flow = ControlFlow()

    while True:
        obj, next_activity, next_machine, oids = control_flow.get_next_activity(
            config, process_instance)
        if next_activity is not None:
            print("{} - {} - {}".format(next_activity,
                                        process_instance.pid, next_machine))
            if next_machine is not None:
                with getattr(act_repo, next_machine).request() as request:
                    yield request
                    timestamp = (
                        datetime.now() + timedelta(seconds=env.now*60*60)).strftime("%Y-%m-%d %H:%M:%S")
                    event = {"ocel:activity": next_activity, "ocel:timestamp": timestamp,
                             "ocel:omap": oids, "ocel:vmap": {"resource": next_machine}}
                    record = {str(uuid.uuid4()): event}
                    # append_list_as_row(file_name, [
                    #     process_instance.pid, next_activity, datetime.now() + timedelta(seconds=env.now), oids])
                    record_event(file_name, record)
                    yield env.process(getattr(act_repo, next_activity)(obj))
            else:
                # append_list_as_row(file_name, [
                #     process_instance.pid, next_activity, datetime.now() + timedelta(seconds=env.now), oids])
                timestamp = (
                    datetime.now() + timedelta(seconds=env.now*60*60)).strftime("%Y-%m-%d %H:%M:%S")
                event = {"ocel:activity": next_activity, "ocel:timestamp": timestamp,
                         "ocel:omap": oids, "ocel:vmap": {"resource": next_machine}}
                record = {str(uuid.uuid4()): event}
                record_event(file_name, record)
                yield env.process(getattr(act_repo, next_activity)(obj))
        else:
            break
    # results.append(
    #     [process_instance.pid, "case end", datetime.now() + timedelta(seconds=env.now)])

    # for row in results:
    #     thewriter.writerow(row)


# Setup and start the simulation
print('Carwash')
print('Check out http://youtu.be/fXXmeP9TvBg while simulating ... ;-)')
random.seed(RANDOM_SEED)  # This helps reproducing the results

# Create an environment and start the setup process
env = simpy.rt.RealtimeEnvironment(factor=1)
# env = simpy.Environment()

# conf = Configuration()
config = {
    "po-price": 3,
    "sn-price": 200,
    "ap-quantity": 5
}

# file_name = './simulated-logs.csv'
# with open(file_name, 'w', newline='') as write_obj:
#     thewriter = csv.writer(write_obj)
#     thewriter.writerow(['case_id', 'activity', 'time:timestamp'])

file_name = "./simulated-logs.jsonocel"
with open(file_name, 'w') as fp:
    json.dump({"ocel:events": {}, "ocel:objects": {}}, fp)

env.process(setup(env, file_name, T_INTER))

# Execute!
env.run(until=SIM_TIME)
