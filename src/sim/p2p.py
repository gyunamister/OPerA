import json
from pm4py.objects.conversion.log import converter as log_converter
import pandas as pd
import matplotlib.pyplot as plt
import sys
import pathlib

import sim.viz
import sim.p2p
import sim.manual_modeling as mm
from sim.model_configuration import ResourceConfig, ActivityConfig, ArrivalProcessConfig
from sim.simulation import simulate, create_simulation_model, create_oc_simulation_model, control_simulate
from sim.enums import AvailableLifecycles, ExecutionParameters
from datetime import datetime, timedelta
from ocpa.objects.log.exporter.ocel import factory as export_factory

from datetime import datetime, timedelta

import sim.parameter_implementations as pimpls
import sim.time_utils
from sim.manual_modeling import ModelBuilder, split_of, join_of
from sim.model_configuration import ArrivalProcessConfig, ActivityConfig, ResourceConfig, DecisionConfig, MappingConfig, \
    ModelConfiguration, ObjectConfig


def p2p():
    mb = ModelBuilder()
    mb.set_object_config(ObjectConfig({"Purchase Requisition": [1, 1], "Purchase Order": [
                         1, 1], "Material": [1, 3], "Goods Receipt": [1, 1], "Invoice Receipt": [1, 1]}))
    # mb.set_default_arrival_config(
    #     ArrivalProcessConfig(sim.time_utils.now(), pimpls.ExpSampler(70), pimpls.StandardWorkweek))
    mb.set_arrival_configs({'baseline': ArrivalProcessConfig(sim.time_utils.now(), pimpls.ExpSampler(
        30), pimpls.StandardWorkweek, last_arrival=sim.time_utils.now() + timedelta(days=10))})
    for i in range(1, 25):
        mb.add_resource(f'R{i}', ResourceConfig(1, pimpls.StandardWorkweek))

    ppr = mb.add_activity('Plan Purchase Requisition', ActivityConfig(pimpls.Fifo, pimpls.ExpSampler(
        10), object_type={"Purchase Requisition": {}, "Material": {"planned_delivery_days": pimpls.ValueUniformSampler(1, 10)}}), ['R1', 'R2'], initial_node=True)

    pr = mb.add_activity('Create Purchase Requisition', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(30), object_type={"Purchase Requisition": {}, "Material": {"net_price": pimpls.ValueUniformSampler(190, 202), "effective_price": pimpls.ValueUniformSampler(190, 200), "quantity": pimpls.ValueUniformSampler(0, 5)}}), ['R3', 'R4'])

    po = mb.add_activity('Create Purchase Order', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(30), object_type={"Purchase Requisition": {}, "Material": {"quantity": pimpls.ValueUniformSampler(5, 10)}, "Purchase Order": {}}), ['R5', 'R6'])

    rg = mb.add_activity('Receive Goods', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(20), object_type={"Goods Receipt": {}, "Material": {"diff_quantity": pimpls.ValueUniformSampler(0, 3)}, "Purchase Order": {}}), ['R7', 'R8'])

    igr = mb.add_activity('Issue Goods Receipt', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(20), object_type={"Goods Receipt": {}, "Material": {}, "Purchase Order": {}}), ['R9', 'R10'])

    vm = mb.add_activity('Verify Material', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(20), object_type={"Material": {}}), ['R11', 'R12', 'R23'])

    ri = mb.add_activity('Receive Invoice', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(20), object_type={"Invoice Receipt": {"diff_amount": pimpls.ValueUniformSampler(0, 10)}, "Purchase Order": {}, "Invoice Receipt": {}}), ['R13', 'R14'])

    iir = mb.add_activity('Issue Invoice Receipt', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(20), object_type={"Invoice Receipt": {"diff_assigned_amount": pimpls.ValueUniformSampler(0, 5)}, "Purchase Order": {}}), ['R15', 'R16'])

    pgi = mb.add_activity('Plan Goods Issue', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(20), object_type={"Material": {"diff_issue": pimpls.ValueUniformSampler(0, 5)}}), ['R17', 'R18'])

    gi = mb.add_activity('Goods Issue', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(20), object_type={"Material": {}}), ['R19', 'R20', 'R24'])

    ci = mb.add_activity('Clear Invoice', ActivityConfig(
        pimpls.Fifo, pimpls.ExpSampler(20), object_type={"Invoice Receipt": {}, "Purchase Order": {}, "Goods Receipt": {}}), ['R21', 'R22'])

    or1 = mb.add_decision('decision1', DecisionConfig(
        pimpls.StochasticClassifier([.01, .99])))
    or2 = mb.add_decision('decision2', DecisionConfig(
        pimpls.StochasticClassifier([.01, .99])))
    and1 = mb.add_concurrency(final_node=True)
    mb.connect(ppr, pr)
    mb.connect(pr, po)
    mb.connect(po, rg)
    mb.connect(rg, igr)
    mb.connect(igr, vm)
    mb.connect(vm, split_of(or1))
    mb.connect(split_of(or1), [vm, join_of(or1)])
    mb.connect(join_of(or1), split_of(and1))
    mb.connect(split_of(and1), [ri, pgi])
    mb.connect(pgi, gi)
    mb.connect(gi, split_of(or2))
    mb.connect(ri, iir)
    mb.connect(iir, ci)
    mb.connect(split_of(or2), [gi, join_of(or2)])
    mb.connect([join_of(or2), ci], join_of(and1))
    return mb.build()


graph, config = p2p()

# print(config)
gg = sim.viz.visualize_sim_graph(graph, label_decision_points=True)
# sim.viz.save_horizontal(gg, 'par_net')


def p2p_execution_parameters():
    execution_parameters = {ExecutionParameters.CasesToGenerate: 1000,
                            ExecutionParameters.GenerationCutoffDate: None,
                            ExecutionParameters.SimStartDate: None,
                            ExecutionParameters.SimCutoffDate: None,
                            ExecutionParameters.RealtimeLimit: timedelta(seconds=600),
                            ExecutionParameters.Pause: {"step": timedelta(hours=24), "length": 5}}
    return execution_parameters


model = create_oc_simulation_model(
    graph, config, execution_parameters=p2p_execution_parameters())
print("give me an order")
# for message in iter(sys.stdin.readline, ''):
#     print(message)
#     message = message[:-1]
#     print(message)
#     simulation = control_simulate(model, message=message)
for message in iter(sys.stdin.readline, ''):
    message = message[:-1]
    print(f'input: {message}')
    if message == "start":
        break

path = pathlib.Path().resolve().parent.parent.absolute()
output_path = f"{path}/example-files/p2p-example/p2p-streaming-ocel.jsonocel"

simulation = control_simulate(model, streaming_output_log=output_path)
# log = simulation.get_log()
# oc_log = simulation.get_oc_log(AvailableLifecycles.StartOnly)

# parameters = {
#     log_converter.Variants.TO_DATA_FRAME.value.Parameters.CASE_ATTRIBUTE_PREFIX: 'case:'}
# df = log_converter.apply(log, parameters=parameters,
#                          variant=log_converter.Variants.TO_DATA_FRAME)

# print(df)
# df.to_csv("../event_logs/log1.csv")

# raw_output_path = "../event_logs/ocel-raw.json"
# export = export_factory.apply(oc_log, output_path)
# print(export)
# with open(meta_output_path, 'w', encoding='utf-8') as f:
#     json.dump(oc_log.meta, f, ensure_ascii=False, indent=4)
# with open(raw_output_path, 'w', encoding='utf-8') as f:
#     json.dump(oc_log.raw, f, ensure_ascii=False, indent=4)
# print(oc_log.meta)
# print(oc_log.raw)
