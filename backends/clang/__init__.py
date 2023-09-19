import dataclasses
import json
import os.path
from collections import defaultdict
from pathlib import Path
from pprint import pprint
from typing import Union

import clang.cindex
from clang.cindex import CursorKind, Index, Config

from networkx import DiGraph


Config.set_library_path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib')  # Replace with your Clang library path


def get_callgraph():
    graph = DiGraph()
    for f, ff in CALLGRAPH.items():
        # get the caller
        node_info = NODELIST.get(f, None)
        if node_info is None:
            continue
        data = dict(id=f,
                    label=f,
                    file=node_info.file,
                    start=node_info.start,
                    end=node_info.end,
                    mangled_name=node_info.mangled_name,
                    kind=str(node_info.kind),
                    chain="false")
        graph.add_node(f, data=data)
        # get the callees
        for n in ff:
            definition = n.get_definition()
            try:
                data = dict(id=fully_qualified_pretty(definition),
                            label=fully_qualified_pretty(definition),
                            file=definition.location.file.name,
                            start=definition.extent.start.line,
                            end=definition.extent.end.line,
                            mangled_name=definition.mangled_name,
                            kind=str(definition.kind),
                            chain="false")
            except:  # todo fallback for classes?
                try:
                    nn = DECLARATIONS[fully_qualified(n)]
                except KeyError:
                    nn = {'start': n.extent.start.line, 'end': n.extent.end.line, 'file': n.location.file.name}

                # nr = Node.from_cursor(n)
                data = dict(id=fully_qualified_pretty(n),
                            label=fully_qualified_pretty(n),
                            file=nn['file'],
                            start=nn['start'],
                            end=nn['end'],
                            mangled_name=n.mangled_name,
                            kind=str(n.kind),
                            chain="false")
            graph.add_node(fully_qualified_pretty(n), data=data)
            graph.add_edge(f, fully_qualified_pretty(n))
            if f == 'llama_model_loader::llama_model_loader(const std::string &, bool)' and fully_qualified_pretty(n) == 'gguf_get_n_kv(struct gguf_context *)':
                return graph
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
        if res != '' and c.kind != CursorKind.VAR_DECL:
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
    if node.kind in [CursorKind.MEMBER_REF_EXPR, CursorKind.CALL_EXPR, CursorKind.DECL_REF_EXPR]:
        if node.referenced and not is_excluded(node.referenced, xfiles, xprefs):
            print(f'FN {node.kind}: {fully_qualified_pretty(cur_fun)}, {fully_qualified_pretty(node.referenced)}, {fully_qualified_pretty(node.lexical_parent)}')
    if not is_excluded(node, xfiles, xprefs):
        if node.kind == CursorKind.FUNCTION_TEMPLATE:
            cur_fun = node
            FULLNAMES[fully_qualified(cur_fun)].add(
                fully_qualified_pretty(cur_fun))
            NODELIST[fully_qualified_pretty(cur_fun)] = Node.from_cursor(cur_fun)

        if node.kind == CursorKind.CXX_METHOD or \
                node.kind == CursorKind.FUNCTION_DECL or \
                node.kind == CursorKind.CONSTRUCTOR or \
                node.kind == CursorKind.STRUCT_DECL:
            # if not is_excluded(node, xfiles, xprefs):
            cur_fun = node
            FULLNAMES[fully_qualified(cur_fun)].add(
                fully_qualified_pretty(cur_fun))
            NODELIST[fully_qualified_pretty(cur_fun)] = Node.from_cursor(cur_fun)
            DECLARATIONS[fully_qualified(cur_fun)] = dict(start=node.extent.start.line, end=node.extent.end.line, file=node.location.file.name)

        if node.kind in [CursorKind.CALL_EXPR]:

            if node.referenced:  # and not is_excluded(node.referenced, xfiles, xprefs):
            #     print(f'CALL_EXPR: {fully_qualified_pretty(cur_fun)}, {fully_qualified_pretty(node.referenced)}')



                CALLGRAPH[fully_qualified_pretty(cur_fun)].append(node.referenced)
            # SECONDARY_CALLGRAPH[fully_qualified_pretty(cur_fun)].append(node.)
            # print(node.def)

    # if not is_excluded(node, xfiles, xprefs):
    # if node.kind == CursorKind.CALL_EXPR or node.kind == CursorKind.UNEXPOSED_EXPR:
    #     print(fully_qualified_pretty(node), fully_qualified_pretty(node.referenced))
    #     a = 2

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
    if filename.suffix == '.json':
        with open(filename) as compdb:
            return json.load(compdb)
    else:
        return [{'command': '', 'file': filename}]


def analyze_source_files(file: Union[str, Path], cfg, index):
    print('reading source files...')
    for cmd in read_compile_commands(file):

        c = cfg['clang_args']
        tu = index.parse(cmd['file'], [
            '-I./testfiles',
            '-I/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/15.0.0/include',
            '-stdlib=libc++'
        ])  # , '-x c++','-std=c++11'
        print(cmd['file'])
        if not tu:
            print("unable to load input")

        for d in tu.diagnostics:
            if d.severity == d.Error or d.severity == d.Fatal:
                # print(' '.join(c))
                pprint(('diags', list(map(get_diag_info, tu.diagnostics))))

        show_info(tu.cursor, cfg['excluded_paths'], cfg['excluded_prefixes'])


def build_ast_graph(path) -> DiGraph:

    if os.path.isfile(path):
        files = [Path(path)]
    else:
        files = []
        for p in Path(path).rglob('*'):
            if p.suffix in ['c.', '.cpp', '.h', '.hpp']:
                files.append(p)

    cfg = {'db': None,
           'clang_args': [],
           'excluded_prefixes': ['std::', '__libcpp', 'operator', '__builtin', '__c11_atomic'],
           'excluded_paths': ['/usr', '/Applications'],
           'config_filename': None,
           }
    index = Index.create()
    for file in files:
        analyze_source_files(file, cfg, index)

    graph = get_callgraph()
    print(graph)

    return graph


CALLGRAPH = defaultdict(list)
SECONDARY_CALLGRAPH = defaultdict(list)
FULLNAMES = defaultdict(set)
NODELIST = defaultdict()
DECLARATIONS = defaultdict()
