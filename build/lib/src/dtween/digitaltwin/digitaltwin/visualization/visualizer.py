from dtween.digitaltwin.digitaltwin.visualization.versions import graphviz_based
from pm4py.visualization.common import gview
from pm4py.visualization.common import save as gsave


GRAPHVIZ_BASED = "graphviz_based"

VERSIONS = {GRAPHVIZ_BASED: graphviz_based.apply}


def apply(obj, variant=GRAPHVIZ_BASED, parameters=None):
    return VERSIONS[variant](obj, parameters=parameters)


def save(gviz, output_file_path):
    """
    Save the diagram

    Parameters
    -----------
    gviz
        GraphViz diagram
    output_file_path
        Path where the GraphViz output should be saved
    """
    gsave.save(gviz, output_file_path)


def view(gviz):
    """
    View the diagram

    Parameters
    -----------
    gviz
        GraphViz diagram
    """
    return gview.view(gviz)
