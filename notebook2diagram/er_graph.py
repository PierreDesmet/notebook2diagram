"""
Some utility used to automagically produce ER diagram from a Jupyter NB.
author: b011ldg
"""
import sys
import re
from typing import Optional
from graphviz import Digraph
import json
import pandas as pd
import numpy as np
import os
from pathlib import Path
from .exceptions import MergeStatementIncorrect
#os.environ["PATH"] += os.pathsep + r"E:\Users\b011ldg\AppData\Local\Continuum\Graphviz\bin"

class MergeStatement:
    """
    Given a merge statement (`pd.merge(...)`), stores the tables to be joined, as
    well as some metadata.
    Usage:
    >>> stmt = \"""pd.merge(t1.drop(['useless'], 1),
                            right=t2[['siren', 'col2']],
                            left_index=True, on = 'id_key')\"""
    >>> ms = MergeStatement(stmt)
    >>> ms.params
    {'left': 't1', 'right': 't2', 'on': "'id_key'", 'left_index': 'True'}
    """
    def __init__(self, stmt: str):
        self.cellnumber = 'todo'
        self.stmt = stmt
        cleaned_stmt = self.clean_stmt(self.stmt)
        self._parsed_kwargs = self.parse_kwargs(cleaned_stmt)
        self._parsed_args = self.parse_args(cleaned_stmt)
        self._resulting_table = self.parse_resulting_table()
        self.params = {**self._parsed_args, **self._parsed_kwargs, **self._resulting_table}

    @staticmethod
    def parse_kwargs(stmt: str) -> dict:
        """
        Usage:
        >>> parse_kwargs("pd.merge(t1, right=t2, how= 'left', on = 'id_key')")
        {'right': 't2', 'how': "'left'", 'on': "'id_key'"}
        """
        kwargs = dict()
        for attr in pd.merge.__code__.co_varnames:
            pat = attr + rf' ?= ?(?P<{attr}>[^,\)]*)'
            if rgx := re.search(pat, stmt):
                kwargs.update(rgx.groupdict())
        return kwargs

    def parse_args(self, cleaned_stmt: str) -> dict:
        """
        Usage:
        >>> parse_args("pd.merge(t1, right=t2, how= 'left', on = 'id_key')")
        {'left': 't1'}
        """
        args = list()
        for part in re.split(r', ?', cleaned_stmt):
            if '=' not in (arg := self.clean_varname(part)):
                args.append(arg)
        not_found_args = self.not_found_args(self._parsed_kwargs)
        return dict(zip(not_found_args, args))

    @staticmethod
    def clean_stmt(stmt: str) -> str:
        """
        Usage:
        >>> clean_stmt("pd.merge(t1.drop(['useless'], 1), right=t2, left_index=True, on = 'id_key')")
        "t1.drop, right=t2, left_index=True, on = 'id_key'"
        """
        stmt = stmt[stmt.index('pd.merge(') + len('pd.merge('):-1]
        stmt = re.sub(r'\(.*\)', '', stmt)
        stmt = re.sub(r'\[\[.*\]\]', '', stmt)
        return stmt

    @staticmethod
    def clean_varname(stmt: str) -> str:
        """
        Usage:
        >>> clean_varname("df.drop('id', 1)")
        'df'
        >>> clean_varname("df[['siren', 'company_name']]")
        'df'
        """
        for pat in ('.', '[', '('):
            if pat in stmt:
                stmt = stmt[:stmt.index(pat)]
        return stmt

    @staticmethod
    def not_found_args(parsed_kwargs: dict):
        """
        Yields args that are not kwargs, i.e.: the unamed args.
        """
        for attr in pd.merge.__code__.co_varnames:
            if attr not in parsed_kwargs:
                yield attr

    def parse_resulting_table(self):
        if not (rgx := re.search(r'(?P<res>\w+) ?= ?pd\.merge', self.stmt)):
            raise MergeStatementIncorrect(self.cellnumber, self.stmt)
        return rgx.groupdict()

class BetterDigraph(Digraph):
    """
    Pretty much the same as Digraph, only except I store my attrs, me.
    @b011ldg
    """
    def __init__(self, name: str, rankdir: str = 'LR'):
        super(BetterDigraph, self).__init__()
        self.list_edges = []
        self.list_nodes = []
        self.attr(rankdir=rankdir)

    def add_edge(self, from_: str, to_: str, label: Optional[str] = None):
        if (from_, to_) not in self.list_edges:
            self.edge(from_, to_, label=label)
            self.list_edges.append((from_, to_))
    def add_node(self, node_name: str, shape: str = 'egg'):
        if node_name not in self.list_nodes:
            self.node(node_name, shape=shape, style="rounded, filled, bold", color="#BD2027", fillcolor="#e8e8e8")
            self.list_nodes.append(node_name)

def assert_python_version_sup(version='3.8'):
    major, minor = sys.version_info.major, sys.version_info.minor
    required_major, required_minor = (int(_) for _ in version.split('.'))
    if major < required_major or minor < required_minor:
        raise NotImplementedError('Python >=3.8 must be installed')

def get_current_nb_json(current_NB_name: str):
    if current_NB_name is None:
        try:
            import ipyparams
            current_NB_name = ipyparams.notebook_name.replace('%20', ' ')
        except:
            raise NotImplementedError("Please `!pip install ipyparams` :-)")
    notebook_content = Path(current_NB_name).read_text(encoding='utf-8')
    notebook_json = json.loads(notebook_content)
    return notebook_json

def show_ER_graph(current_NB_name: str):
    import tempfile
    bdg = BetterDigraph(name="ER_diagram")
    notebook_json = get_current_nb_json(current_NB_name)

    for num_cell in range(len(notebook_json['cells'])):
        bloc = notebook_json['cells'][num_cell]['source']

        for stmt in bloc:
            cond1 = 'pd.merge' not in stmt
            cond2 = stmt.startswith('#')
            cond3 = '>>>' in stmt
            if any([cond1, cond2, cond3]):
                continue
            dico = MergeStatement(stmt).params

            if dico:
                for node_name in ('left', 'right', 'res'):
                    bdg.add_node(dico[node_name])
                bdg.add_edge(dico['left'], dico['res'],
                             label=choose_key(dico, 'left'))
                bdg.add_edge(dico['right'], dico['res'],
                             label=choose_key(dico, 'right'))
    bdg.render(tempfile.mktemp('.gv'), view=True)

def choose_key(dico: dict, how: str = 'left') -> str:
    """
    Given a merge statement, returns the desired keys.
    Usage:
    >>> dico = {'left': 'policies',
                'right': 'companies',
                'how': "'left'",
                'left_on': "'SIREN'",
                'right_index': True,
                'res': 'policies_and_companies'}
    >>> choose_key(dico, 'left')
    'SIREN'
    """
    if how == 'left' and 'left_on' in dico:
        return dico['left_on']
    if how == 'right' and 'right_on' in dico:
        return dico['right_on']
    return dico['on']
