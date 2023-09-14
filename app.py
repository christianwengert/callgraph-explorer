#!/usr/bin/env python3
import dataclasses
from pprint import pprint
import dash
from dash import dcc, State, no_update, clientside_callback, ClientsideFunction
from dash import html
import dash_cytoscape as cyto
import clang.cindex
from clang.cindex import CursorKind, Index, Config
from collections import defaultdict
import json
from dash import Output, Input
from networkx import DiGraph


@dataclasses.dataclass(frozen=True)
class Node:
    file: str
    start: int
    end: int
    display_name: str
    mangled_name: str
    spelling: str
    kind: str
    id: str
    label: str
    chain: str = "false"

    @staticmethod
    def from_cursor(cursor: clang.cindex.Cursor):
        return Node(
            file=cursor.location.file.name,
            start=cursor.extent.start.line,
            end=cursor.extent.end.line,
            display_name=cursor.displayname,
            mangled_name=cursor.mangled_name,
            spelling=cursor.spelling,
            kind=str(cursor.kind),
            id=cursor.spelling,
            label=cursor.displayname,
            chain="false"
        )


Config.set_library_path(
    '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib')  # Replace with your Clang library path

CALLGRAPH = defaultdict(list)
FULLNAMES = defaultdict(set)
NODELIST = defaultdict()
# FUNCTIONS = dict()

global graph
# graph = DiGraph()


def get_diag_info(diag):
    return {
        'severity': diag.severity,
        'location': diag.location,
        'spelling': diag.spelling,
        'ranges': list(diag.ranges),
        'fixits': list(diag.fixits)
    }


def fully_qualified(c):
    if c is None:
        return ''
    elif c.kind == CursorKind.TRANSLATION_UNIT:
        return ''
    else:
        res = fully_qualified(c.semantic_parent)
        if res != '':
            return res + '::' + c.spelling
        return c.spelling


def fully_qualified_pretty(c):
    if c is None:
        return ''
    elif c.kind == CursorKind.TRANSLATION_UNIT:
        return ''
    else:
        res = fully_qualified(c.semantic_parent)
        if res != '':
            return res + '::' + c.displayname
        return c.displayname


def is_excluded(node, xfiles, xprefs):
    if not node.extent.start.file:
        return False

    for xf in xfiles:
        if node.extent.start.file.name.startswith(xf):
            return True

    fqp = fully_qualified_pretty(node)

    for xp in xprefs:
        if fqp.startswith(xp):
            return True

    return False

def show_info(node, xfiles, xprefs, cur_fun=None):
    if node.kind == CursorKind.FUNCTION_TEMPLATE:
        if not is_excluded(node, xfiles, xprefs):
            cur_fun = node
            FULLNAMES[fully_qualified(cur_fun)].add(
                fully_qualified_pretty(cur_fun))

    if node.kind == CursorKind.CXX_METHOD or \
            node.kind == CursorKind.FUNCTION_DECL:
        if not is_excluded(node, xfiles, xprefs):
            cur_fun = node
            FULLNAMES[fully_qualified(cur_fun)].add(
                fully_qualified_pretty(cur_fun))

    if node.kind == CursorKind.CALL_EXPR:
        if node.referenced and not is_excluded(node.referenced, xfiles, xprefs):
            CALLGRAPH[fully_qualified_pretty(cur_fun)].append(node.referenced)

    for c in node.get_children():
        show_info(c, xfiles, xprefs, cur_fun)
# def show_info(node, xfiles, xprefs, cur_fun=None):
#     if node.kind == CursorKind.FUNCTION_TEMPLATE:
#         if not is_excluded(node, xfiles, xprefs):
#             cur_fun = node
#             # FULLNAMES[fully_qualified(cur_fun)].add(
#             #     fully_qualified_pretty(cur_fun))
#             NODELIST[fully_qualified_pretty(cur_fun)] = cur_fun
#
#     if node.kind == CursorKind.CXX_METHOD or \
#             node.kind == CursorKind.FUNCTION_DECL:
#         if not is_excluded(node, xfiles, xprefs):
#             cur_fun = node
#             # FULLNAMES[fully_qualified(cur_fun)].add(
#             #     fully_qualified_pretty(cur_fun))
#             NODELIST[fully_qualified_pretty(cur_fun)] = cur_fun
#             # FUNCTIONS[fully_qualified_pretty(cur_fun)] = cur_fun
#
#     if node.kind == CursorKind.CALL_EXPR:
#         if node.referenced and not is_excluded(node.referenced, xfiles, xprefs):
#             print(fully_qualified_pretty(cur_fun), node.referenced.spelling)
#             CALLGRAPH[fully_qualified_pretty(cur_fun)].append(node.referenced)
#
#     for c in node.get_children():
#         show_info(c, xfiles, xprefs, cur_fun)


def pretty_print(n):
    v = ''
    if n.is_virtual_method():
        v = ' virtual'
    if n.is_pure_virtual_method():
        v = ' = 0'
    return fully_qualified_pretty(n) + v


def print_calls(fun_name, so_far, graph, depth=0):
    if depth >= 15:
        print('...<too deep>...')
        return

    if fully_qualified_pretty(fun_name) in CALLGRAPH:
        for f in CALLGRAPH[fun_name]:
            print('  ' * (depth + 1) + pretty_print(f))
            if f in so_far:
                continue
            so_far.append(f)
            if fully_qualified_pretty(f) in CALLGRAPH:
                print_calls(fully_qualified_pretty(f), so_far, graph, depth + 1)
            else:
                print_calls(fully_qualified(f), so_far, graph, depth + 1)
    if fun_name is None:
        pass

def print_calls_bak(fun_name, so_far, graph, depth=0):
    if depth >= 15:
        print('...<too deep>...')
        return
    if fun_name in CALLGRAPH:
        for f in CALLGRAPH[fun_name]:
            print('  ' * (depth + 1) + pretty_print(f))
            if f in so_far:
                continue
            so_far.append(f)
            if fully_qualified_pretty(f) in CALLGRAPH:
                print_calls(fully_qualified_pretty(f), so_far, graph, depth + 1)
            else:
                print_calls(fully_qualified(f), so_far, graph, depth + 1)
    if fun_name is None:
        for k, v in CALLGRAPH.items():
            if not k:
                continue
            print(k)
            for f in CALLGRAPH[k]:
                if f in so_far:
                    continue
                print('  ' * (depth + 1) + pretty_print(f))

                n = Node.from_cursor(f)
                nn = Node.from_cursor(NODELIST[k])
                graph.add_node(n.spelling, data=dict(id=n.spelling,
                                                     label=n.display_name,
                                                     file=n.file,
                                                     start=n.start,
                                                     end=n.end,
                                                     mangled_name=n.mangled_name,
                                                     kind=str(n.kind),
                                                     chain="false"))  # , data=n
                graph.add_node(nn.spelling, data=dict(id=nn.spelling,
                                                      label=nn.display_name,
                                                      file=nn.file,
                                                      start=nn.start,
                                                      end=nn.end,
                                                      mangled_name=nn.mangled_name,
                                                      kind=str(nn.kind),
                                                      chain="false"))
                graph.add_edge(nn.spelling, n.spelling)
                so_far.append(f)
                if fully_qualified_pretty(f) in CALLGRAPH:
                    print_calls(fully_qualified_pretty(f), so_far, graph, depth + 1)
                else:
                    print_calls(fully_qualified(f), so_far, graph, depth + 1)


def read_compile_commands(filename):
    if filename.endswith('.json'):
        with open(filename) as compdb:
            return json.load(compdb)
    else:
        return [{'command': '', 'file': filename}]


def analyze_source_files(cfg):
    print('reading source files...')
    for cmd in read_compile_commands(cfg['db']):
        index = Index.create()
        c = cfg['clang_args']
        tu = index.parse(cmd['file'], c)
        print(cmd['file'])
        if not tu:
            print("unable to load input")

        for d in tu.diagnostics:
            if d.severity == d.Error or d.severity == d.Fatal:
                print(' '.join(c))
                pprint(('diags', list(map(get_diag_info, tu.diagnostics))))
                return
        show_info(tu.cursor, cfg['excluded_paths'], cfg['excluded_prefixes'])



external_scripts = [
    {'src': 'static/highlight.min.js', 'type': 'module'},
    {'src': 'static/callbacks.js', 'type': 'module'},
]
app = dash.Dash(__name__, external_scripts=external_scripts)

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
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
        <div>My Custom footer</div>
    </body>
</html>
'''


def build_ast_graph(filename) -> DiGraph:
    cfg = {'db': filename,
           'clang_args': [],
           'excluded_prefixes': ['std::', '__libcpp', 'operator', '__builtin', '__c11_atomic'],
           'excluded_paths': ['/usr', '/Applications'],
           'config_filename': None,
           }

    analyze_source_files(cfg)
    graph = DiGraph()
    print_calls(None, [], graph)
    print(graph)

    return graph


app.layout = html.Div([
    html.Div([
        dcc.Input(id='filter', type='text', placeholder='Search')
    ]),
    html.Div([
        dcc.Store(id='code-store'),
        cyto.Cytoscape(id='callgraph', elements=[],
                       layout={'name': 'breadthfirst'},
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
                                   'padding': '10px'
                               },

                           },
                           {
                               'selector': 'node[selected = "true"]',
                               'style': {
                                   'border-color': 'blue',
                               }
                           },
                           # {
                           #     'selector': 'node[id = "three"]',  # works
                           #     'style': {
                           #         'background-color': 'green',
                           #     }
                           # },
                           {
                               'selector': 'node[chain = "true"]',
                               'style': {
                                   'background-color': 'pink',
                               }
                           },
                           {
                               'selector': 'edge',
                               'style': {
                                   # The default curve style does not work with certain arrows
                                   'curve-style': 'bezier',
                                   'target-arrow-color': 'red',
                                   'target-arrow-shape': 'triangle',
                                   'line-color': 'red'
                               }
                           },
                           {
                               'selector': 'edge[gaga = "true"]',
                               'style': {
                                   # The default curve style does not work with certain arrows
                                   'curve-style': 'bezier',
                                   'target-arrow-color': 'yellow',
                                   'target-arrow-shape': 'triangle',
                                   'line-color': 'yellow'
                               }
                           },

                       ]
                       )
    ], id='dash')

])


def get_parents_recursive(graph, node, parents=None):
    if parents is None:
        parents = []

    for parent in graph.predecessors(node):
        parents.append(parent)
        get_parents_recursive(graph, parent, parents)

    return parents


def get_successors_recursive(graph, node, successors=None):
    if successors is None:
        successors = []

    for successor in graph.successors(node):
        successors.append(successor)
        get_successors_recursive(graph, successor, successors)

    return successors


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
)
def show_code(node_data):
    global graph
    if not node_data:
        return no_update

    with open(node_data['file'], 'r') as f:
        contents = f.read()
    start = node_data['start']
    end = node_data['end']

    # code = "\n".join(contents.splitlines()[start:end])
    return {'code': contents, 'start': start, 'end': end, 'filename': node_data['file']}


@app.callback(
    Output('callgraph', 'elements'),
    # Input('filter', 'value'),
    Input('callgraph', 'tapNodeData'),
    State('callgraph', 'elements')
)
def render_network(node_data, prev_elements):
    global graph
    if node_data is None and not prev_elements:
        graph = build_ast_graph('/Users/christianwengert/src/minimal-c-test/test.cpp')

    # clean up
    for n in graph.nodes:
        graph.nodes[n]['data']['chain'] = 'false'

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

    return elements


if __name__ == '__main__':
    app.run_server(debug=True)
