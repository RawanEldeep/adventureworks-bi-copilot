import os
import pickle

import networkx as nx


def LoadGraph(Path: str = "data/knowledge_graph.gpickle") -> nx.MultiGraph:
    if not os.path.exists(Path):
        raise FileNotFoundError(
            f'"{Path}" not found. Run GraphBuilder.py first to build and save the knowledge graph.'
        )
    with open(Path, "rb") as F:
        return pickle.load(F)
