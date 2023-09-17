#!/usr/bin/env python3
import uuid
from collections import defaultdict

import dash
import networkx as nx
from dash import dcc, State, no_update, clientside_callback, ClientsideFunction
from dash import html
import dash_cytoscape as cyto
from dash import Output, Input

from backends.clang import build_ast_graph
from utils.networkx import get_parents_recursive

TEMPLATE_STRING = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        <div id="header"></div>
        <div id="container">
            <pre id="code"></pre>
            <div>
            {%app_entry%}
            </div>
        </div>
        
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        <div id="footer">My Custom footer</div>
    </body>
</html>
'''

# Load extra layouts
cyto.load_extra_layouts()

SERVER_STORE = defaultdict(dict)


external_scripts = [
    {'src': 'static/highlight.min.js', 'type': 'module'},
    {'src': 'static/callbacks.js', 'type': 'module'},
]
app = dash.Dash(__name__,
                external_scripts=external_scripts,
                external_stylesheets=['https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/regular.min.css'])  # 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css'

app.index_string = TEMPLATE_STRING

app.layout = html.Div([
    html.Div([
        dcc.Input(id='filter', className='w50', type='text', placeholder='Search', debounce=True),

    ], id='graph-toolbar'),
    html.Div([
        dcc.Store(id='code-store'),
        dcc.Store(id='session-store', storage_type='memory'),  # Store the session identifier
        dcc.Loading([
            cyto.Cytoscape(id='callgraph', elements=[],
                       layout={
                           'name': 'dagre',
                           'spacingFactor': 1.25
                       },
                       stylesheet=[
                           {
                               'selector': 'node',
                               'style': {
                                   'content': 'data(label)',
                                   'shape': 'rectangle',
                                   'text-halign': 'center',
                                   'text-valign': 'center',
                                   'width': 'label',
                                   'height': 'label',
                                   'padding': '10px',
                                   'background-color': 'rgb(86, 91, 94)',
                                   'border-width': 1,
                                   'border-color': 'rgb(184, 194, 200)',
                                   'color': 'rgb(184, 194, 200)',
                                   'font-family': 'monospace'


                               },

                           },
                           {
                               'selector': 'node[selected = "true"]',
                               'style': {
                                   'border-color': 'rgb(241,231,64)',
                                   'border-width': 2
                               }
                           },
                           {
                               'selector': 'node[chain = "true"]',
                               'style': {
                                   'background-color': 'rgb(59, 127, 180)',
                               }
                           },
                           {
                               'selector': 'edge',
                               'style': {
                                   # The default curve style does not work with certain arrows
                                   'curve-style': 'taxi',  # 'bezier',
                                   'target-arrow-color': 'rgb(184, 194, 200)',
                                   'target-arrow-shape': 'triangle',
                                   'line-color': 'rgb(184, 194, 200)',
                                   'width': 1
                               }
                           },
                           {
                               'selector': 'edge[gaga = "true"]',
                               'style': {
                                   # The default curve style does not work with certain arrows
                                   'curve-style': 'bezier',
                                   'target-arrow-color': 'rgb(59, 127, 180)a',
                                   'target-arrow-shape': 'triangle',
                                   'line-color': 'rgb(59, 127, 180)a'
                               }
                           },

                       ],
                       # style={'height': '80vh'},
                       )
        ], className='loading', parent_className='outer-loading', type="circle")
    ]),
    html.Div([
        html.Div(id='modal', children=[
            html.Div([
                html.Div('Hello', id='modal-header-text'),
                html.Button([
                    html.I(className="fa-regular fa-x")
                ], id='modal-header-close')
            ], id='modal-header'),
            html.Div([
                html.Div([
                    'Enter the path',
                    #/Users/christianwengert/src/llama/llama.cpp/llama.cpp
                    dcc.Input(className='w100', id='path-string',
                              value='./testfiles', debounce=True),
                ]),
            ], id='modal-body'),
            html.Div([
                html.Button('Load')
            ], id='modal-footer')
        ])
    ], id='modal-background'),
    html.Div(id='main-toolbar', children=[
        html.Button(id='open-project-button', children=[
            html.I(className='fa-regular fa-folder-open')
        ]),
    ]),
], id='dash')


@app.callback(
    Output('modal-background', 'style'),
    Input('modal-header-close', 'n_clicks'),
    Input('open-project-button', 'n_clicks')
)
def show_hide_modal(n_clicks_1, n_clicks_2):
    context = dash.callback_context
    if len(context.triggered) and context.triggered[0]:
        if context.triggered[0]['prop_id'] == 'modal-header-close.n_clicks':
            return {'display': 'none'}
        if context.triggered[0]['prop_id'] == 'open-project-button.n_clicks':
            return {'display': 'flex'}

    return no_update


clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='hl_code'
    ),
    Output('dash', 'style'),
    Input('code-store', 'data'),
    # Input('in-component2', 'value')
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

    # code = "\n".join(contents.splitlines()[start:end])
    return {'code': contents, 'start': start, 'end': end, 'filename': node_data['file']}



#
#
# @app.callback(
#     Output('session-store', 'data'),
#     Input('session-store', 'modified_timestamp'),
#     State('session-store', 'data')
# )
# def generate_session_id(modified_timestamp, current_session_data):
#     if modified_timestamp:
#         # Generate a unique session identifier (e.g., using UUID)
#         session_id = str(uuid.uuid4())
#         # Store the session identifier in the dcc.Store component
#         current_session_data = session_id
#
#     return current_session_data
@app.callback(
    Output('callgraph', 'elements'),
    Output('session-store', 'data'),
    # Input('filter', 'value'),
    Input('callgraph', 'tapNodeData'),
    Input('filter', 'n_submit'),
    Input('path-string', 'value'),
    # Input('filter', 'n_submit'),
    State('filter', 'value'),
    State('callgraph', 'elements'),
    State('session-store', 'data')


)
def render_network(node_data, _n_sub, path, search_value, prev_elements, session):

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
    else:
        graph = build_ast_graph(path)
        graph_backup = graph.copy()

    context = dash.callback_context
    if len(context.triggered) and context.triggered[0]:
        if search_value:  # do nothing on empty

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
            graph_backup = graph.copy()
            graph = filtered_graph

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

    elements = [
        *[dict(data=graph.nodes[k]['data']) for k in graph.nodes],
        *[dict(data=dict(source=a,
                         target=b,
                         gaga="true" if graph.nodes[a]['data'].get('chain') == "true" and graph.nodes[b]['data'].get('chain') == "true" else "false"
                         )
               ) for a, b in graph.edges],
    ]

    SERVER_STORE[session][path]['graph'] = graph
    SERVER_STORE[session][path]['graph_backup'] = graph_backup

    return elements, session


if __name__ == '__main__':
    app.run_server(debug=True)
