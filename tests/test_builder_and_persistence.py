"""
Unit tests for src/graph/builder.py, engine.py, and persistence.py
"""

import os
import tempfile

import scipy.sparse as sp

from src.graph.builder import build_graph, get_or_build_graph
from src.graph.engine import GraphEngine
from src.graph.loader import load_and_preprocess_dataset
from src.graph.persistence import export_to_graphml, load_graph, save_graph

SMALL_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "small_spotify_tracks_dataset.csv"
)


def test_build_graph_and_engine():
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    graph = build_graph(dataset, threshold=0.3, top_k=50)

    assert isinstance(graph, GraphEngine)
    assert len(graph) == len(dataset)
    assert isinstance(graph.similarity_matrix, sp.csr_matrix)

    # Test track query
    first_track_id = dataset.idx_to_id[0]
    assert first_track_id in graph

    # Test neighbors query
    neighbors = graph.get_neighbors(first_track_id)
    assert isinstance(neighbors, list)
    for nbr_id, weight in neighbors:
        assert isinstance(nbr_id, str)
        assert weight >= 0.3

    # Test 2-hop metadata candidates query
    candidates = graph.get_2hop_metadata_candidates(first_track_id)
    assert isinstance(candidates, list)

    # Test NetworkX duck typing
    assert first_track_id in graph.nodes
    meta = graph.nodes[first_track_id]
    assert "track_name" in meta
    assert isinstance(graph[first_track_id], dict)


def test_persistence_save_load():
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    graph = build_graph(dataset, threshold=0.3, top_k=20)

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, "test_graph.pkl")

        # Save
        save_graph(graph, cache_file)
        assert os.path.exists(cache_file)

        # Load
        loaded_graph = load_graph(cache_file)
        assert isinstance(loaded_graph, GraphEngine)
        assert len(loaded_graph) == len(graph)

        # Verify edge equivalence
        first_track_id = dataset.idx_to_id[0]
        orig_neighbors = graph.get_neighbors(first_track_id)
        loaded_neighbors = loaded_graph.get_neighbors(first_track_id)
        assert orig_neighbors == loaded_neighbors


def test_get_or_build_graph_caching():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, "cached_graph.pkl")
        assert not os.path.exists(cache_file)

        # First call builds and caches
        graph1 = get_or_build_graph(SMALL_DATASET_PATH, cache_path=cache_file)
        assert os.path.exists(cache_file)

        # Second call loads from cache
        graph2 = get_or_build_graph(SMALL_DATASET_PATH, cache_path=cache_file)
        assert len(graph1) == len(graph2)

        first_track_id = graph1.idx_to_id[0]
        assert graph1.get_neighbors(first_track_id) == graph2.get_neighbors(
            first_track_id
        )


def test_graphml_export():
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    graph = build_graph(dataset, threshold=0.3, top_k=10)

    with tempfile.TemporaryDirectory() as tmpdir:
        graphml_file = os.path.join(tmpdir, "test_graph.graphml")
        export_to_graphml(graph, graphml_file)
        assert os.path.exists(graphml_file)
        assert os.path.getsize(graphml_file) > 0
