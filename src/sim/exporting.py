from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING

from pm4py.objects.log.log import EventLog
from pm4py.write import write_xes, write_petri_net

from sim.utils import PathConstants

if TYPE_CHECKING:
    import sim.simulation


def save_log(log: EventLog, filename: str = 'log.xes'):
    write_xes(log, os.path.join(PathConstants.base_event_log_path, filename))


def save_simulated_log(simulator: sim.simulation.Simulator, filename: str = None):
    save_log(simulator.get_log(),
             filename=f'simulated_log_{datetime.datetime.now()}.xes' if filename is None else filename)


def save_petrinet(net, im, fm, filename: str = 'net.apnml'):
    write_petri_net(net, im, fm, file_path=os.path.join(PathConstants.base_petrinet_path, filename))
