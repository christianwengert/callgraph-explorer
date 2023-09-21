import networkx as nx


def get_parents_recursive(graph: nx.DiGraph, node, parents=None):
    if parents is None:
        parents = []

    for parent in graph.predecessors(node):
        parents.append(parent)
        get_parents_recursive(graph, parent, parents)

    return parents


def get_successors_recursive(graph: nx.DiGraph, node, successors=None):
    if successors is None:
        successors = []

    for successor in graph.successors(node):
        successors.append(successor)
        get_successors_recursive(graph, successor, successors)

    return successors
