#!/usr/bin/env python3
import uuid
from collections import defaultdict

import dash
import networkx as nx
from dash import State, no_update, clientside_callback, ClientsideFunction
import dash_cytoscape as cyto
from dash import Output, Input

from backends.clang import build_ast_graph
from ui import TEMPLATE_STRING
from ui.layout import get_layout
from utils.networkx import get_parents_recursive

# Load extra layouts
cyto.load_extra_layouts()

SERVER_STORE = defaultdict(dict)  # semi-persistent store of user projects

external_scripts = [
    {'src': 'static/highlight.min.js', 'type': 'module'},
    {'src': 'static/callbacks.js', 'type': 'module'},
]
external_stylesheets = [
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/regular.min.css'
]
app = dash.Dash(__name__,
                external_scripts=external_scripts,
                external_stylesheets=external_stylesheets,
                index_string=TEMPLATE_STRING)
app.layout = get_layout()


@app.callback(
    Output('modal-background', 'style'),
    Input('modal-header-close', 'n_clicks'),
    Input('open-project-button', 'n_clicks'),
    Input('load-project-button', 'n_clicks'),
)
def show_hide_modal(*_args):
    context = dash.callback_context
    if len(context.triggered) and context.triggered[0]:
        if context.triggered[0]['prop_id'] == 'modal-header-close.n_clicks':
            return {'display': 'none'}
        if context.triggered[0]['prop_id'] == 'open-project-button.n_clicks':
            return {'display': 'flex'}
        if context.triggered[0]['prop_id'] == 'load-project-button.n_clicks':
            return {'display': 'none'}
    return no_update


clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='hl_code'
    ),
    Output('dash', 'style'),
    Input('code-store', 'data'),
)


@app.callback(
    Output('code-store', 'data'),
    Input('callgraph', 'tapNodeData'),
    State('session-store', 'data')
)
def store_code(node_data, session):
    # Code will be stored in local memory
    # this local memory store then calls the clientside callback (see static/callbacks.js:hl_code)
    if not node_data:
        return no_update
    if not session:
        return no_update

    with open(node_data['file'], 'r') as f:
        contents = f.read()
    start = node_data['start']
    end = node_data['end']

    return {'code': contents, 'start': start, 'end': end, 'filename': node_data['file']}


@app.callback(
    Output('callgraph', 'elements'),
    Output('session-store', 'data'),
    Input('callgraph', 'tapNodeData'),
    Input('filter', 'n_submit'),
    Input('load-project-button', 'n_clicks'),
    State('path-string', 'value'),
    State('include-path-string', 'value'),
    State('filter', 'value'),
    State('session-store', 'data')

)
def render_callgraph(node_data, _n_sub, _n_load, path, include_path, search_value, session):
    graph = graph_backup = None
    elements = []
    if session is None:
        # Generate a unique session identifier (e.g., using UUID)
        session_id = str(uuid.uuid4())
        # Store the session identifier in the dcc.Store component
        session = session_id

    # prepare persistent storage
    if session not in SERVER_STORE:
        SERVER_STORE[session] = dict()
        SERVER_STORE[session][path] = dict()
    if path in SERVER_STORE[session] and SERVER_STORE[session][path]:
        graph = SERVER_STORE[session][path]['graph']
        graph_backup = SERVER_STORE[session][path]['graph_backup']

    # build graph if load-project-button has been clicked
    context = dash.callback_context
    if len(context.triggered) and context.triggered[0]:
        if context.triggered[0]['prop_id'] == 'load-project-button.n_clicks':
            graph = build_ast_graph(path, include_path)
            graph_backup = graph.copy()

        if context.triggered[0]['prop_id'] == 'filter.n_submit':
            if search_value:  # do nothing on empty
                # filter and do not forget to take the backup
                for n in graph.nodes:
                    graph_backup.nodes[n]['data']['filtered'] = "false"
                graph = get_filtered_subgraph(graph_backup.copy(), search_value)
            else:
                # just restore the full graph
                if graph_backup is not None:
                    graph = graph_backup.copy()
                    for n in graph.nodes:
                        graph_backup.nodes[n]['data']['filtered'] = "false"

    if graph is not None:
        # reset all nodes to clean nodes (no highlight, no selection)

        for n in graph.nodes:
            graph.nodes[n]['data']['chain'] = 'false'
            graph.nodes[n]['data']['selected'] = 'false'
        #
        # filter nodes by text

        if node_data and 'id' in node_data and node_data['id'] in graph.nodes and graph.nodes[node_data['id']]:
            graph.nodes[node_data['id']]['data']['selected'] = "true"
            # now highlight
            graph.nodes[node_data['id']]['data']['chain'] = "true"  # include it
            for p in get_parents_recursive(graph, node_data['id']):  # G.predecessors(node_data['id']):
                graph.nodes[p]['data']['chain'] = "true"
                graph.nodes[p]['data']['relationship'] = "parent"

        # build cytoscape
        nodes = [dict(data=graph.nodes[k]['data']) for k in graph.nodes if k]
        node_names = [n['data']['id'] for n in nodes]
        edges = []
        for a, b in graph.edges:

            highlight = "true" if graph.nodes[a]['data'].get('chain') == "true" and graph.nodes[b]['data'].get('chain') == "true" else "false"
            if not a or not b:
                continue

            elif a in node_names and b in node_names:
                edges.append(
                    dict(data=dict(source=a,
                                   target=b,
                                   highlight=highlight))
                )
            else:
                a_ok = a in node_names
                b_ok = b in node_names
                print(f'Some edges are wrong {a} ({a_ok}) and {b} ({b_ok})')

        elements = [
            *nodes,
            *edges,
        ]

        if path and path not in SERVER_STORE[session]:
            SERVER_STORE[session][path] = dict()
        SERVER_STORE[session][path]['graph'] = graph
        SERVER_STORE[session][path]['graph_backup'] = graph_backup

    return elements, session


def get_filtered_subgraph(graph, search_value):
    target_nodes = set()
    for n in graph.nodes:
        if search_value.lower() in n.lower():
            target_nodes.add(n)
            graph.nodes[n]['data']['filtered'] = "true"

    reachable_nodes = set()
    # Perform a breadth-first search from each target node
    for node in target_nodes:
        reachable_nodes.update(nx.descendants(graph, node))
        reachable_nodes.update(nx.ancestors(graph, node))
    # Include the target nodes themselves
    reachable_nodes.update(target_nodes)
    if reachable_nodes:
        filtered_graph = graph.subgraph(reachable_nodes).copy()
    else:
        filtered_graph = nx.DiGraph()  # empty
    # graph_backup = graph.copy()
    graph = filtered_graph
    return graph


if __name__ == '__main__':
    app.run_server(debug=True)
