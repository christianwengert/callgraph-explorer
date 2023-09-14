import dataclasses
import json
from collections import defaultdict
from pprint import pprint

import clang.cindex
from clang.cindex import CursorKind, Index, Config

from networkx import DiGraph


Config.set_library_path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib')  # Replace with your Clang library path


def get_callgraph():
    graph = DiGraph()
    for f, ff in CALLGRAPH.items():
        # get the caller
        node_info = NODELIST[f]
        data = dict(id=node_info.display_name,
                    label=node_info.display_name,
                    file=node_info.file,
                    start=node_info.start,
                    end=node_info.end,
                    mangled_name=node_info.mangled_name,
                    kind=str(node_info.kind),
                    chain="false")
        graph.add_node(f, data=data)
        # get the callees
        for n in ff:
            try:
                nn = DECLARATIONS[fully_qualified(n)]
            except KeyError:
                nn = {'start': n.extent.start.line, 'end': n.extent.end.line}

            # nr = Node.from_cursor(n)
            data = dict(id=fully_qualified_pretty(n),
                        label=n.displayname,
                        file=n.location.file.name,
                        start=nn['start'],
                        end=nn['end'],
                        mangled_name=n.mangled_name,
                        kind=str(n.kind),
                        chain="false")

            graph.add_node(fully_qualified_pretty(n), data=data)
            graph.add_edge(f, fully_qualified_pretty(n))
    return graph


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
            NODELIST[fully_qualified_pretty(cur_fun)] = Node.from_cursor(cur_fun)

    if node.kind == CursorKind.CXX_METHOD or \
            node.kind == CursorKind.FUNCTION_DECL or \
            node.kind == CursorKind.CONSTRUCTOR:
        if not is_excluded(node, xfiles, xprefs):
            cur_fun = node
            FULLNAMES[fully_qualified(cur_fun)].add(
                fully_qualified_pretty(cur_fun))
            NODELIST[fully_qualified_pretty(cur_fun)] = Node.from_cursor(cur_fun)
            DECLARATIONS[fully_qualified(cur_fun)] = dict(start=node.extent.start.line, end=node.extent.end.line)

    if node.kind == CursorKind.CALL_EXPR:
        if node.referenced and not is_excluded(node.referenced, xfiles, xprefs):
            CALLGRAPH[fully_qualified_pretty(cur_fun)].append(node.referenced)

    for c in node.get_children():
        show_info(c, xfiles, xprefs, cur_fun)


def pretty_print(n):
    v = ''
    if n.is_virtual_method():
        v = ' virtual'
    if n.is_pure_virtual_method():
        v = ' = 0'
    return fully_qualified_pretty(n) + v


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

        show_info(tu.cursor, cfg['excluded_paths'], cfg['excluded_prefixes'])


def build_ast_graph(filename) -> DiGraph:
    cfg = {'db': filename,
           'clang_args': [],
           'excluded_prefixes': ['std::', '__libcpp', 'operator', '__builtin', '__c11_atomic'],
           'excluded_paths': ['/usr', '/Applications'],
           'config_filename': None,
           }

    analyze_source_files(cfg)

    graph = get_callgraph()
    print(graph)

    return graph


CALLGRAPH = defaultdict(list)
FULLNAMES = defaultdict(set)
NODELIST = defaultdict()
DECLARATIONS = defaultdict()
