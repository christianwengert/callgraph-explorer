from typing import Any, Dict, List

from dash import dcc
from dash import html
import dash_cytoscape as cyto


def get_layout() -> html.Div:
    return html.Div(
        [
            html.Div([
                dcc.Input(id='filter', className='w50', type='text', placeholder='Search', debounce=True),

            ], id='graph-toolbar'),
            html.Div([
                dcc.Store(id='code-store'),
                dcc.Store(id='session-store', storage_type='memory'),  # Store the session identifier
                dcc.Loading([
                    cyto.Cytoscape(id='callgraph', elements=[],
                                   autoRefreshLayout=True,
                                   layout={
                                       'name': 'dagre',
                                       'spacingFactor': 1.5,
                                       'rankSep': 150,
                                       # 'nodeSep': 200,
                                       'edgeSep': 150,
                                       'padding': 100,
                                   },
                                   stylesheet=get_cyto_stylesheet())
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
                            html.Label('Enter the path'),
                            # /Users/christianwengert/src/llama/llama.cpp/llama.cpp
                            dcc.Input(className='w100', id='path-string',
                                      value='./testfiles',
                                      # value='./testfiles/test.cpp',
                                      # value='/Users/christianwengert/src/llama/llama.cpp/llama.cpp',
                                      # debounce=True
                                      ),
                            html.Label('Compiler flags (e.g. include directories)'),
                            dcc.Input(className='w100', id='include-path-string',
                                      value='-I./testfiles -I/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/15.0.0/include -stdlib=libc++',
                                      placeholder='Enter include directories like this',
                                      # debounce=True
                                      ),
                        ]),
                    ], id='modal-body'),
                    html.Div([
                        html.Button('Load', id='load-project-button')
                    ], id='modal-footer')
                ])
            ], id='modal-background'),
            html.Div(id='main-toolbar', children=[
                html.Button(id='open-project-button', children=[
                    html.I(className='fa-regular fa-folder-open')
                ]),
            ]),
        ], id='dash')


def get_cyto_stylesheet() -> List[Dict[str, Any]]:
    return [
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
                'curve-style': 'bezier',  # 'bezier',
                'target-arrow-color': 'rgb(184, 194, 200)',
                'target-arrow-shape': 'triangle',
                'line-color': 'rgb(184, 194, 200)',
                'width': 1
            }
        },
        {
            'selector': 'edge[highlight = "true"]',
            'style': {
                # The default curve style does not work with certain arrows
                'curve-style': 'bezier',
                'target-arrow-color': 'rgb(59, 127, 180)',
                'target-arrow-shape': 'triangle',
                'line-color': 'rgb(59, 127, 180)'
            }
        },
    ]
