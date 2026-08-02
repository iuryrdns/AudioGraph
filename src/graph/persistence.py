"""
Provides serialization/deserialization methods for saving and loading GraphEngine
instances to/from disk using high-performance binary pickle files and GraphML exports.
"""

import os
import pickle

import networkx as nx

from src.graph.engine import GraphEngine


def save_graph(graph: GraphEngine, filepath: str) -> None:
    """
    Serializes a GraphEngine instance to a binary pickle file.

    Parameters
    ----------
    graph : GraphEngine
        GraphEngine object to be saved.
    filepath : str
        Target file path (e.g. 'data/spotify_graph.pkl').
    """
    parent_dir = os.path.dirname(filepath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(filepath, "wb") as f:
        pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_graph(filepath: str) -> GraphEngine:
    """
    Loads a serialized GraphEngine instance from a binary pickle file.

    Parameters
    ----------
    filepath : str
        Path to serialized graph file.

    Returns
    -------
    GraphEngine
        Loaded GraphEngine instance.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Graph file '{filepath}' not found.")

    with open(filepath, "rb") as f:
        graph = pickle.load(f)

    if not isinstance(graph, GraphEngine):
        raise TypeError(
            f"Loaded object from '{filepath}' is not a GraphEngine instance."
        )

    return graph


def export_to_graphml(graph: GraphEngine, filepath: str) -> None:
    """
    Exports Layer 2 similarity graph edges and track metadata to NetworkX GraphML (.graphml)
    format for visualization tools like Gephi.

    Parameters
    ----------
    graph : GraphEngine
        GraphEngine instance to export.
    filepath : str
        Target GraphML file path (e.g. 'data/graph.graphml').
    """
    parent_dir = os.path.dirname(filepath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    nx_graph = nx.DiGraph()

    # Add track nodes and metadata
    for track_id, meta in graph.track_metadata.items():
        node_attrs = {
            "name": str(meta.get("track_name", "")),
            "artist": str(meta.get("primary_artist", "")),
            "genre": str(meta.get("track_genre", "")),
            "popularity": int(meta.get("popularity", 0)),
            "duration_ms": int(meta.get("duration_ms", 0)),
            "explicit": bool(meta.get("explicit", False)),
        }
        nx_graph.add_node(track_id, **node_attrs)

    # Add similarity edges
    for u_id in graph.idx_to_id:
        u_str = str(u_id)
        for v_str, weight in graph.get_neighbors(u_str):
            nx_graph.add_edge(u_str, v_str, weight=weight)

    nx.write_graphml(nx_graph, filepath)
