from __future__ import annotations

import graphviz
import pydotplus
from pm4py.visualization.petrinet import visualizer as petri_visualizer

from sim.sim_graph import ArrivalNode, TerminalNode, LinearNode, ActivityNode, AndJoin, TauNode, AndSplit, XorSplit, \
    XorJoin, SplittingNode, SimulationGraph, DelayNode


def visualize_petrinet(petrinet_model):
    return petri_visualizer.apply(petrinet_model.net, petrinet_model.im, petrinet_model.fm)

def save_petrinet(gviz, filename):
    gc = gviz.copy()
    gc.attr('graph', {'rankdir': 'TB'})
    return petri_visualizer.save(gc, filename)

def visualize_sim_graph(graph: SimulationGraph, label_decision_points=False):
    arrival_node = graph.arrival

    gg = graphviz.Digraph()
    # g = pydotplus.Dot() alternative

    reverse_decision_map = {v: k for k, v in graph.decision_map.items()}

    seen = set()
    node_map = {}
    name_map = {}
    todo = [arrival_node]

    todo_edges = []

    count = 0
    while len(todo) > 0:
        current = todo.pop()
        seen.add(current)

        node = None
        name = None
        if type(current) is ArrivalNode:
            name = 'Arrival'
            node = pydotplus.Node(name=name)
            gg.node(name)
        elif type(current) is TerminalNode:
            name = 'Terminal'
            node = pydotplus.Node(name=name)
            gg.node(name=name)
        elif type(current) is AndSplit:
            name = 'AndSplit' + str(count)
            node = pydotplus.Node(name=name, shape='diamond', label='+')
            gg.node(name=name, shape='diamond', label='+')
        elif type(current) is AndJoin:
            name = 'AndJoin' + str(count)
            node = pydotplus.Node(name=name, shape='diamond', label='+')
            gg.node(name=name, shape='diamond', label='+')
        elif type(current) is XorSplit:
            label = 'X'
            if label_decision_points:
                decision_label = reverse_decision_map[current]
                label = f'X ({decision_label})'
            name = 'XorSplit' + str(count)
            node = pydotplus.Node(name=name, shape='diamond', label=label)
            gg.node(name=name, shape='diamond', label=label)
        elif type(current) is XorJoin:
            name = 'XorJoin' + str(count)
            node = pydotplus.Node(name=name, shape='diamond', label='X')
            gg.node(name=name, shape='diamond', label='X')
        elif type(current) is ActivityNode:
            name = current.label
            if ':' in name:
                name = str.replace(name, ':', 'semicolon')
            node = pydotplus.Node(name=name, shape='box', style='rounded', label=name)
            gg.node(name=name, shape='box', style='rounded', label=name)
        elif type(current) is TauNode:
            name = 'tau' + str(count)
            node = pydotplus.Node(name=name, shape='box', label='tau', color='black')
            gg.node(name=name, shape='box', label='tau', fillcolor='gray', style='filled')
        elif type(current) is DelayNode:
            name = 'delay' + str(count)
            node = pydotplus.Node(name=name, shape='box', label='D')
            gg.node(name=name, shape='box', label='D')
        else:
            print(current)
        assert node is not None
        count += 1
        node_map[current] = node
        name_map[current] = name
        # g.add_node(node)

        if isinstance(current, LinearNode):
            succ = current.successor
            if succ not in seen:
                todo.append(succ)
            todo_edges.append((current, succ))
        elif isinstance(current, SplittingNode):
            for succ in current.successors:
                if succ not in seen:
                    todo.append(succ)
                todo_edges.append((current, succ))

    for n1, n2 in todo_edges:
        # e = pydotplus.Edge(node_map[n1], node_map[n2])
        # g.add_edge(e)
        gg.edge(name_map[n1], name_map[n2])

    return gg


def view(gg: graphviz.Digraph):
    return gg


def view_horizontal(gg: graphviz.Digraph):
    gc = gg.copy()
    gc.attr('graph', {'rankdir': 'LR'})
    return gc


def save(gg: graphviz.Digraph, filename):
    gg.render(filename, format='pdf')


def save_horizontal(gg: graphviz.Digraph, filename):
    gc = gg.copy()
    gc.attr('graph', {'rankdir': 'LR'})
    return gc.render(filename, format='pdf')
