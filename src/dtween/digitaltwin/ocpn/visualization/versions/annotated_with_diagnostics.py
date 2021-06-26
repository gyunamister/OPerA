import uuid
import tempfile
from graphviz import Digraph
from pm4py.objects.petri.petrinet import PetriNet
from dtween.digitaltwin.ocpn.objects.obj import ObjectCentricPetriNet
from dtween.digitaltwin.diagnostics.util import equal_arc
from statistics import median, mean

COLORS = ["#05B202", "#A13CCD", "#BA0D39", "#39F6C0", "#E90638", "#07B423", "#306A8A", "#678225", "#2742FE", "#4C9A75",
          "#4C36E9", "#7DB022", "#EDAC54", "#EAC439", "#EAC439", "#1A9C45", "#8A51C4", "#496A63", "#FB9543", "#2B49DD",
          "#13ADA5", "#2DD8C1", "#2E53D7", "#EF9B77", "#06924F", "#AC2C4D", "#82193F", "#0140D3"]


def apply(ocpn, diagnostics, parameters=None):
    if parameters is None:
        parameters = {}

    image_format = "png"
    if "format" in parameters:
        image_format = parameters["format"]

    filename = tempfile.NamedTemporaryFile(suffix='.gv').name
    g = Digraph("", filename=filename, engine='dot',
                graph_attr={'bgcolor': 'transparent'})

    all_objs = {}
    trans_names = {}

    replay = diagnostics["replay"]
    act_count = diagnostics["act_count"]
    place_fitness_per_trace_persp = diagnostics["place_fitness_per_trace"]
    group_size_hist_persp = diagnostics["group_size_hist"]
    aggregated_statistics_performance_min = diagnostics["aggregated_statistics_performance_min"]
    aggregated_statistics_performance_median = diagnostics[
        "aggregated_statistics_performance_median"]
    aggregated_statistics_performance_mean = diagnostics["aggregated_statistics_performance_mean"]
    aggregated_statistics_performance_mean = diagnostics["aggregated_statistics_performance_mean"]

    pl_count = 1
    tr_count = 1
    arc_count = 1

    # color = COLORS[index % len(COLORS)]
    color = "#05B202"
    color_mapping = dict()
    object_types = ocpn.object_types
    for index, ot in enumerate(object_types):
        color_mapping[ot] = COLORS[index % len(COLORS)]

    for pl in ocpn.places:
        # this_uuid = str(uuid.uuid4())
        this_uuid = "p%d" % (pl_count)
        # pl_str = this_uuid
        pl_count += 1
        color = color_mapping[pl.object_type]
        if pl.initial == True:
            g.node("(p)%s" % (pl.name), pl.name, shape="circle", style="filled", fillcolor=color, color=color,
                   fontsize="13.0", labelfontsize="13.0")
        elif pl.final == True:
            g.node("(p)%s" % (pl.name), pl.name, shape="circle", style="filled", color=color, fillcolor=color,
                   fontsize="13.0", labelfontsize="13.0")
        else:
            g.node("(p)%s" % (pl.name), pl.name, shape="circle", color=color,
                   fontsize="13.0", labelfontsize="13.0")
        all_objs[pl] = "(p)%s" % (pl.name)

    for tr in ocpn.transitions:
        # this_uuid = str(uuid.uuid4())
        this_uuid = "t%d" % (tr_count)
        tr_count += 1
        if tr.silent == True:
            g.node(this_uuid, this_uuid, fontcolor="#FFFFFF", shape="box",
                   fillcolor="#000000", style="filled", labelfontsize="18.0")
            all_objs[tr] = this_uuid
        elif tr.name not in trans_names:
            act_count_string = ""
            for obj_type in object_types:
                if obj_type in act_count:
                    if tr.name in act_count[obj_type]:
                        obj_count = act_count[obj_type][tr.name]
                        act_count_string += "%s:%s \n" % (str(obj_type),
                                                          str(obj_count))

            # g.node("(t)%s" % (tr.name), "%s" % (tr.name), shape="box", fontsize="36.0",
                #    labelfontsize="36.0", xlabel='''<<font POINT-SIZE="13">%s</font>>''' % (act_count_string))
            g.node("(t)%s" % (tr.name), "%s" % (tr.name), shape="box", fontsize="36.0",
                   labelfontsize="36.0")
            trans_names[tr.name] = tr.name
            all_objs[tr] = "(t)%s" % (tr.name)
        else:
            all_objs[tr] = trans_names[tr.name]

    for arc in ocpn.arcs:
        # this_uuid = str(uuid.uuid4())
        this_uuid = "a%d" % (arc_count)
        arc_count += 1
        arc_annotation = ""

        source_node = arc.source
        target_node = arc.target

        if type(source_node) == ObjectCentricPetriNet.Place:
            object_type = source_node.object_type
        elif type(target_node) == ObjectCentricPetriNet.Place:
            object_type = target_node.object_type

        color = color_mapping[object_type]

        for k in aggregated_statistics_performance_mean[object_type].keys():
            if equal_arc(k, arc):
                arc_annotation += "\\nperf: median=%s mean=%s" % (
                    aggregated_statistics_performance_median[object_type][k]['label'],
                    aggregated_statistics_performance_mean[object_type][k]['label'])
                break

        if arc.variable == True:
            g.edge(all_objs[source_node], all_objs[target_node],
                   label=arc_annotation, color=color + ":white:" + color, fontsize="13.0")
        else:
            g.edge(all_objs[source_node], all_objs[target_node],
                   label=arc_annotation, color=color, fontsize="13.0")

        all_objs[arc] = this_uuid

    g.attr(overlap='false')
    g.attr(fontsize='11')

    g.format = image_format
    return g
