"""
Some utility used to automagically produce ER diagram from a Jupyter NB.
author: b011ldg
"""
import re
from typing import Optional
from graphviz import Digraph
import json
import pandas as pd
import numpy as np
import os
from pathlib import Path
os.environ["PATH"] += os.pathsep + r"E:\Users\b011ldg\AppData\Local\Continuum\Graphviz\bin"

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

def left_right_key_from_stmt(stmt: str):
    """
    Usage :
    >>> left_right_key_from_stmt("table_c = safe_join*(table_a, table_b, 'num_contrat')")
    ['table_a', 'table_b', 'table_c', 'num_contrat']
    >>> left_right_key_from_stmt("table_c = pd.merge*(table_a, table_b, how='left', on='num_contrat')")
    ['table_a', 'table_b', 'table_c', 'num_contrat']
    """
    if stmt.startswith('#'):
        return dict()
    # First attempt with safe_join:
    rgx = r'(?P<res>[\w\d_]+) = safe_join\((?P<left>[\w\d_]+).*, (?P<right>[\w\d_]+).*, \'(?P<key>[\w\d_]+)\'.*\)'
    rgx = re.search(rgx, stmt)
    if rgx:
        return rgx.groupdict()
    # Second try using pd.merge:
    rgx = r'(?P<res>[\w\d_]+) = pd.merge\((?P<left>[\w\d_]+).*, (?P<right>[^(?:how=)][\w\d_]+).*, on=\'(?P<key>[\w\d_]+)\'.*\)'
    rgx = re.search(rgx, stmt)
    if rgx:
        return rgx.groupdict()
    return dict()
    

def show_ER_graph(current_NB_name: str):
    import tempfile
    bdg = BetterDigraph(name="ER_diagram")
    notebook_json = get_current_nb_json(current_NB_name)
    
    for num_cell in range(len(notebook_json['cells'])):
        bloc = notebook_json['cells'][num_cell]['source']
        # print(bloc)
        for stmt in bloc:
            dico = left_right_key_from_stmt(stmt)

            if dico:
                for node_name in ('left', 'right', 'res'):
                    bdg.add_node(dico[node_name])
                bdg.add_edge(dico['left'], dico['res'], label=dico['key'])
                bdg.add_edge(dico['right'], dico['res'])
    bdg.render(tempfile.mktemp('.gv'), view=True)

def safe_join(a, b, cle, fill: Optional[str] = 'non renseigne'):
    import sys
    if b[cle].duplicated().sum() > 0:
        print("Erreur : la jointure n'a pas pu s'effectuer car des doublons "
              "sont présents dans", object_name(b) + '.', file=sys.stderr)
        sys.exit(0)
    if any(a[cle].apply(type).unique() != b[cle].apply(type).unique()):
        if fill is not None:
            print(f'Filling temporaire par {fill!a}')
            a[cle] = a[cle].fillna(fill)
        else:
            err_msg = "Erreur : la jointure n'a pas pu s'effectuer "\
                      "car les cles sont de types différents."
            raise ValueError(err_msg)
    b['_tmp_'] = '_tmp_'
    j = pd.merge(a, b, how='left', on=cle)
    assert len(j) == len(a)
    if type(cle) == str : cle = [cle]
    msg1 = j['_tmp_'].notnull().sum(), 'lignes sur', len(a), 'ont pu être rattachées'
    msg2 = f"({j['_tmp_'].notnull().sum()/len(a):.2%})."
    msg3 = f'{j.shape[1] - a.shape[1] - len(cle)} colonnes ajoutées.'
    print(' '.join(map(str, msg1)), msg2, msg3)
    del j['_tmp_'] ; del b['_tmp_']
    j[cle] = j[cle].replace(fill, np.nan)
    return j