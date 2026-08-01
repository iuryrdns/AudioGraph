"""
AudioGraph-AI Graph Builder Module

Responsible for constructing the dual-layer heterogeneous recommendation graph.
Computes batch weighted cosine similarity, applies dual-pruning (threshold >= 0.3, top-k <= 300),
builds SciPy CSR similarity matrices and metadata inverted indexes, and provides one-time caching.
"""

import os
from typing import Any

import numpy as np
import scipy.sparse as sp

from src.graph.engine import GraphEngine
from src.graph.loader import (
    FEATURE_COLUMNS,
    TrackDataset,
    load_and_preprocess_dataset,
)
from src.graph.persistence import load_graph, save_graph

# Domain importance weights for audio features (see GRAPH_MODELLING.md)
DEFAULT_FEATURE_WEIGHTS: dict[str, float] = {
    # High Importance (Vibe, Rhythm & Mood)
    "danceability": 1.5,
    "energy": 1.5,
    "valence": 1.3,
    "tempo": 1.2,
    # Moderate Importance (Timbre & Texture)
    "acousticness": 1.0,
    "instrumentalness": 1.0,
    "speechiness": 0.8,
    # Low Importance (Production / Secondary Attributes)
    "loudness": 0.5,
    "liveness": 0.4,
    "duration_ms": 0.1,
    "popularity": 0.2,
}


def build_graph(
    dataset: TrackDataset,
    feature_weights: dict[str, float] | None = None,
    threshold: float = 0.3,
    top_k: int = 300,
    batch_size: int = 1000,
) -> GraphEngine:
    """
    Constructs a GraphEngine instance from a preprocessed TrackDataset.

    Parameters
    ----------
    dataset : TrackDataset
        Preprocessed dataset container from loader.py.
    feature_weights : dict, optional
        Dictionary mapping feature names to numerical weight multipliers.
    threshold : float, default 0.3
        Minimum similarity threshold to retain an edge.
    top_k : int, default 300
        Maximum outgoing similarity neighbors per track.
    batch_size : int, default 1000
        Batch size for matrix multiplication.

    Returns
    -------
    GraphEngine
        Constructed GraphEngine ready for recommendations.
    """
    weights_dict = feature_weights or DEFAULT_FEATURE_WEIGHTS
    N = len(dataset)

    # 1. Prepare Feature Weight Vector
    weight_vector = np.array(
        [weights_dict.get(feat, 1.0) for feat in FEATURE_COLUMNS],
        dtype=np.float32,
    )
    sqrt_weights = np.sqrt(weight_vector)

    # 2. Weighted Feature Matrix & Row L2 Normalization
    X_W = dataset.X_scaled * sqrt_weights
    row_norms = np.linalg.norm(X_W, axis=1, keepdims=True)
    row_norms[row_norms == 0] = 1e-8
    X_hat = X_W / row_norms

    # 3. Chunked Similarity Matrix Calculation & Dual-Pruning
    rows: list[int] = []
    cols: list[int] = []
    values: list[float] = []

    for start_idx in range(0, N, batch_size):
        end_idx = min(start_idx + batch_size, N)
        X_batch = X_hat[start_idx:end_idx]

        # S_batch shape: (batch_len, N)
        S_batch = np.dot(X_batch, X_hat.T)

        for i_local in range(end_idx - start_idx):
            i_global = start_idx + i_local
            sim_row = S_batch[i_local]

            # Exclude self-loop
            sim_row[i_global] = -1.0

            # 1) Threshold pruning
            candidate_indices = np.where(sim_row >= threshold)[0]

            if len(candidate_indices) == 0:
                continue

            candidate_sims = sim_row[candidate_indices]

            # 2) Top-K directed degree capping
            if len(candidate_indices) > top_k:
                top_k_partition = np.argpartition(candidate_sims, -top_k)[-top_k:]
                top_indices = candidate_indices[top_k_partition]
                top_sims = candidate_sims[top_k_partition]
            else:
                top_indices = candidate_indices
                top_sims = candidate_sims

            rows.extend([i_global] * len(top_indices))
            cols.extend(top_indices.tolist())
            values.extend(top_sims.astype(np.float32).tolist())

    # Create SciPy CSR similarity matrix
    similarity_matrix = sp.csr_matrix(
        (values, (rows, cols)),
        shape=(N, N),
        dtype=np.float32,
    )

    # 4. Layer 1 Inverted Metadata Index Extraction
    artist_to_tracks: dict[str, list[str]] = {}
    genre_to_tracks: dict[str, list[str]] = {}
    album_to_tracks: dict[str, list[str]] = {}

    track_to_artist: dict[str, list[str]] = {}
    track_to_genre: dict[str, str] = {}
    track_to_album: dict[str, str] = {}
    track_metadata: dict[str, dict[str, Any]] = {}

    df = dataset.df
    for _, row in df.iterrows():
        track_id = str(row["track_id"])

        # Track Metadata Dict
        meta_dict = row.to_dict()
        track_metadata[track_id] = meta_dict

        # Artist mappings
        artists: list[str] = [str(a) for a in row["artist_list"]]
        track_to_artist[track_id] = artists
        for artist in artists:
            artist_to_tracks.setdefault(artist, []).append(track_id)

        # Genre mappings
        genre = str(row["track_genre"])
        track_to_genre[track_id] = genre
        genre_to_tracks.setdefault(genre, []).append(track_id)

        # Album mappings
        album_entity = str(row["album_entity"])
        track_to_album[track_id] = album_entity
        album_to_tracks.setdefault(album_entity, []).append(track_id)

    return GraphEngine(
        similarity_matrix=similarity_matrix,
        id_to_idx=dataset.id_to_idx,
        idx_to_id=dataset.idx_to_id,
        track_metadata=track_metadata,
        artist_to_tracks=artist_to_tracks,
        genre_to_tracks=genre_to_tracks,
        album_to_tracks=album_to_tracks,
        track_to_artist=track_to_artist,
        track_to_genre=track_to_genre,
        track_to_album=track_to_album,
    )


def get_or_build_graph(
    csv_path: str,
    cache_path: str | None = None,
    force_rebuild: bool = False,
    feature_weights: dict[str, float] | None = None,
    threshold: float = 0.3,
    top_k: int = 300,
    batch_size: int = 1000,
) -> GraphEngine:
    """
    Main entrypoint for obtaining a GraphEngine instance.
    Checks if a cached graph file exists at cache_path. If so, loads it directly.
    Otherwise, builds the graph from csv_path, caches it to cache_path, and returns it.

    Parameters
    ----------
    csv_path : str
        Path to raw dataset CSV file.
    cache_path : str, optional
        Path to save/load pre-built binary graph file (e.g. 'data/spotify_graph.pkl').
    force_rebuild : bool, default False
        If True, forces rebuilding even if cache_path exists.
    feature_weights : dict, optional
        Custom feature weights dictionary.
    threshold : float, default 0.3
        Similarity threshold.
    top_k : int, default 300
        Top-k neighbor cap.
    batch_size : int, default 1000
        Batch size.

    Returns
    -------
    GraphEngine
        Ready-to-use graph engine instance.
    """
    if cache_path and os.path.exists(cache_path) and not force_rebuild:
        return load_graph(cache_path)

    dataset = load_and_preprocess_dataset(csv_path)
    graph = build_graph(
        dataset=dataset,
        feature_weights=feature_weights,
        threshold=threshold,
        top_k=top_k,
        batch_size=batch_size,
    )

    if cache_path:
        save_graph(graph, cache_path)

    return graph
