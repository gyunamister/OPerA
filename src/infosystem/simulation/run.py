import random
import json
import uuid

import simpy
from datetime import datetime, timedelta

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple

from infosystem.objects.objects.obj import Order, Item, Route
from infosystem.objects.simulation.obj import ProcessInstance
from infosystem.process.control_flow import factory as control_flow_factory
from infosystem.process.activity.obj import ActivityRepository
from infosystem.utils.logging import record_process_instance, record_event
from infosystem.process.config import factory as config_factory
import argparse
from infosystem.input.settings import SimulationConfig


parser = argparse.ArgumentParser(
    description='Simulating A Order Handling Process')
parser.add_argument(
    '-l', '--log', help='Directory of the log file', required=True)
parser.add_argument(
    '-c', '--config', help='Directory of the configuration file', required=True)
args = vars(parser.parse_args())


results = []


def random_process_instance(i):
    order = Order("o"+str(i), _price=random.randint(150, 250))
    items = [Item("i"+str(i)+"a", _quantity=random.randint(5, 10)),
             Item("i"+str(i)+"b", _quantity=random.randint(5, 10))]
    route = Route("r"+str(i))
    process_instance = ProcessInstance("pid"+str(i), order, items, route)
    return process_instance


def setup(env, file_name, t_inter):
    """Create a carwash, a number of initial cars and keep creating cars
    approx. every ``t_inter`` minutes."""

    act_repo = ActivityRepository(env, t_inter)

    for i in range(4):
        process_instance = random_process_instance(i)
        record_process_instance(file_name, process_instance)
        config = config_factory.read_config(args['config'])
        env.process(order_management(
            env, config, act_repo, process_instance, file_name))

    # Create more cars while the simulation is running
    while True:
        # yield env.timeout(random.randint(t_inter - 2, t_inter + 2))
        if 10 < i < 20:
            yield env.timeout(int(t_inter/2))
        elif 30 < i < 40:
            yield env.timeout(int(t_inter/2))
        else:
            yield env.timeout(t_inter)
        i += 1
        process_instance = random_process_instance(i)
        record_process_instance(file_name, process_instance)
        config = config_factory.read_config(args['config'])
        env.process(order_management(
            env, config, act_repo, process_instance, file_name))


def order_management(env, config, act_repo, process_instance, file_name):
    """
    :param env:  The simulation environment
    :param process_instance: Case ID
    :param net: The petrinet representing the process model
    :param initial_marking: The initial marking of the activities of the model
    :param no_traces: Number of traces that needs to be generated, given by the user
    """

    while True:
        obj, next_activity, next_machine, oids = control_flow_factory.apply(
            config, process_instance)
        if next_activity is not None:
            # print("{} - {} - {}".format(next_activity,process_instance.pid, next_machine))
            # with getattr(act_repo, next_machine).request() as request:
            #     yield request
            yield env.process(getattr(act_repo, next_activity)(obj))
            timestamp = (
                datetime.now() + timedelta(seconds=env.now*60*60)).strftime("%Y-%m-%d %H:%M:%S")
            event = {"ocel:activity": next_activity, "ocel:timestamp": timestamp,
                     "ocel:omap": oids, "ocel:vmap": {"resource": next_machine}}
            record = {str(uuid.uuid4()): event}
            # append_list_as_row(file_name, [
            #     process_instance.pid, next_activity, datetime.now() + timedelta(seconds=env.now), oids])
            record_event(file_name, record)
        else:
            break
    # results.append(
    #     [process_instance.pid, "case end", datetime.now() + timedelta(seconds=env.now)])

    # for row in results:
    #     thewriter.writerow(row)


# Setup and start the simulation
random.seed(SimulationConfig.RANDOM_SEED)  # This helps reproducing the results

# Create an environment and start the setup process

env = simpy.rt.RealtimeEnvironment(factor=1, strict=True)
# env = simpy.Environment()

# file_name = './simulated-logs.csv'
# with open(file_name, 'w', newline='') as write_obj:
#     thewriter = csv.writer(write_obj)
#     thewriter.writerow(['case_id', 'activity', 'time:timestamp'])

with open(args['log'], 'w') as fp:
    initial_json = {
        "ocel:global-event": {
            "ocel:activity": "__INVALID__"
        },
        "ocel:global-object": {
            "ocel:type": "__INVALID__"
        },
        "ocel:global-log": {
            "ocel:attribute-names": [
                "type",
                "price"
            ],
            "ocel:object-types": [
                "order",
                "item",
                "route"
            ],
            "ocel:version": "1.0",
            "ocel:ordering": "timestamp"
        },
        "ocel:events": {},
        "ocel:objects": {}
    }
    json.dump(initial_json, fp)

env.process(setup(env, args['log'], SimulationConfig.T_INTER))

# Execute!
try:
    env.run(until=SimulationConfig.SIM_TIME)
except RuntimeError as e:
    print(e)
