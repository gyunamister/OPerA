from ocpa.objects.oc_petri_net.obj import ObjectCentricPetriNet
from ocpa.objects.oc_petri_net.obj import Marking
import pandas as pd
from ocpa.objects.log.importer.mdl.util import succint_mdl_to_exploded_mdl


def apply(ocpn, log, marking=None, parameters=None):
    if parameters is None:
        parameters = {}

    if marking is None:
        marking = Marking()

    if len(log) == 0:
        return marking

    log = succint_mdl_to_exploded_mdl(log)

    object_types = [x for x in log.columns if not x.startswith("event_")]

    for i, row in log.iterrows():
        activity = row["event_activity"]
        for tr in ocpn.transitions:
            if tr.name == activity:
                for arc in tr.out_arcs:
                    pl = arc.target
                    oi = row[pl.object_type]
                    if not pd.isna(oi):
                        marking.add_token(pl, oi)
                break

    return marking
