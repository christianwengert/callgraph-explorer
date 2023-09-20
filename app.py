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

SERVER_STORE = defaultdict(dict)

external_scripts = [
    {'src': 'static/highlight.min.js', 'type': 'module'},
    {'src': 'static/callbacks.js', 'type': 'module'},
]
external_stylesheets = [
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/regular.min.css'
]
app = dash.Dash(__name__,
                external_scripts=external_scripts,
                external_stylesheets=external_stylesheets)

app.index_string = TEMPLATE_STRING

app.layout = get_layout()


@app.callback(
    Output('modal-background', 'style'),
    Input('modal-header-close', 'n_clicks'),
    Input('open-project-button', 'n_clicks'),
    Input('load-project-button', 'n_clicks'),
)
def show_hide_modal(_n_clicks_1, _n_clicks_2, _n_clicks_3):
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
def show_code(node_data, session):
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
    # Input('filter', 'value'),
    Input('callgraph', 'tapNodeData'),
    Input('filter', 'n_submit'),
    Input('load-project-button', 'n_clicks'),
    State('path-string', 'value'),
    State('include-path-string', 'value'),
    # Input('filter', 'n_submit'),
    State('filter', 'value'),
    # State('callgraph', 'elements'),
    State('session-store', 'data')

)
def render_network(node_data, _n_sub, _n_load, path, include_path, search_value, session):
    graph = graph_backup = None
    elements = []
    if session is None:
        # Generate a unique session identifier (e.g., using UUID)
        session_id = str(uuid.uuid4())
        # Store the session identifier in the dcc.Store component
        session = session_id

    if session not in SERVER_STORE:
        SERVER_STORE[session] = dict()
        SERVER_STORE[session][path] = dict()

    if path in SERVER_STORE[session] and SERVER_STORE[session][path]:
        graph = SERVER_STORE[session][path]['graph']
        graph_backup = SERVER_STORE[session][path]['graph_backup']

    context = dash.callback_context
    if len(context.triggered) and context.triggered[0]:
        if context.triggered[0]['prop_id'] == 'load-project-button.n_clicks':
            graph = build_ast_graph(path, include_path)
            graph_backup = graph.copy()

    if graph:
        if len(context.triggered) and context.triggered[0]:
            if search_value:  # do nothing on empty
                graph = graph_backup.copy()  # Restore
                target_nodes = set()
                for n in graph.nodes:
                    if search_value.lower() in n.lower():
                        target_nodes.add(n)

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
            else:
                graph = graph_backup.copy()

        # clean up
        for n in graph.nodes:
            graph.nodes[n]['data']['chain'] = 'false'
            graph.nodes[n]['data']['selected'] = 'false'
        if node_data and graph.nodes[node_data['id']]:
            graph.nodes[node_data['id']]['data']['selected'] = "true"

        # highlight
        if node_data and 'id' in node_data:
            graph.nodes[node_data['id']]['data']['chain'] = "true"  # include it
            for p in get_parents_recursive(graph, node_data['id']):  # G.predecessors(node_data['id']):
                graph.nodes[p]['data']['chain'] = "true"
                graph.nodes[p]['data']['relationship'] = "parent"
            # for s in get_successors_recursive(graph, node_data['id']):  # G.successors(node_data['id']):
            #     graph.nodes[s]['data']['chain'] = "true"
            #     graph.nodes[s]['data']['relationship'] = "child"

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


if __name__ == '__main__':
    app.run_server(debug=True)
