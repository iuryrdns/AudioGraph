"""
AudioGraph-AI Graph Builder Module

Responsible for constructing the dual-layer heterogeneous recommendation graph.
Computes batch Gaussian RBF weighted Euclidean similarity with super-genre compatibility anchoring,
applies dual-pruning (threshold >= 0.3, top-k <= 300), builds SciPy CSR matrices and metadata indexes,
and provides one-time caching.
"""

import os
from typing import Any, Optional
import numpy as np
import scipy.sparse as sp

from src.graph.engine import GraphEngine
from src.graph.loader import (
    FEATURE_COLUMNS,
    TrackDataset,
    load_and_preprocess_dataset,
)
from src.graph.persistence import load_graph, save_graph
from src.graph.taxonomy import get_genre_compatibility

# Domain importance weights for pure acoustic features
DEFAULT_FEATURE_WEIGHTS: dict[str, float] = {
    # High Importance (Rhythm, Speed, Energy & Mood)
    "danceability": 2.5,
    "energy": 2.5,
    "valence": 1.5,
    "tempo_norm": 2.5,
    "acousticness": 2.0,
    # Moderate Importance (Timbre & Vocal Presence)
    "instrumentalness": 1.5,
    "speechiness": 1.0,
    "loudness_norm": 1.0,
    "liveness": 0.5,
}


def build_graph(
    dataset: TrackDataset,
    feature_weights: Optional[dict[str, float]] = None,
    threshold: float = 0.3,
    top_k: int = 300,
    batch_size: int = 1000,
) -> GraphEngine:
    """
    Constructs a GraphEngine instance from a preprocessed TrackDataset.
    Applies Gaussian RBF Euclidean Distance and Super-Genre Compatibility Anchoring.
    """
    weights_dict = feature_weights or DEFAULT_FEATURE_WEIGHTS
    N = len(dataset)
    track_genres = dataset.df["track_genre"].values.astype(str)

    # Pre-compute vectorized 2D Super-Genre Compatibility Matrix
    unique_genres = sorted(list(set(track_genres)))
    genre_to_id = {g: i for i, g in enumerate(unique_genres)}
    genre_ids = np.array([genre_to_id[g] for g in track_genres], dtype=np.int32)

    num_unique = len(unique_genres)
    M_compat = np.zeros((num_unique, num_unique), dtype=np.float32)
    for i, g1 in enumerate(unique_genres):
        for j, g2 in enumerate(unique_genres):
            M_compat[i, j] = get_genre_compatibility(g1, g2)

    # 1. Prepare Feature Weight Vector
    weight_vector = np.array(
        [weights_dict.get(feat, 1.0) for feat in FEATURE_COLUMNS],
        dtype=np.float32,
    )
    sqrt_weights = np.sqrt(weight_vector)

    # 2. Weighted Feature Matrix calculation (X_W)
    X_W = dataset.X_scaled * sqrt_weights
    X_W_sq_norms = np.sum(X_W ** 2, axis=1)

    # 3. Chunked Similarity Matrix Calculation via Gaussian RBF & Vectorized Genre Compatibility
    rows: list[int] = []
    cols: list[int] = []
    values: list[float] = []

    gamma = 2.0  # RBF distance scaling hyperparameter

    for start_idx in range(0, N, batch_size):
        end_idx = min(start_idx + batch_size, N)
        X_batch = X_W[start_idx:end_idx]
        batch_sq_norms = X_W_sq_norms[start_idx:end_idx, np.newaxis]
        batch_genre_ids = genre_ids[start_idx:end_idx]

        # Squared Euclidean Distances: ||u - v||^2 = ||u||^2 + ||v||^2 - 2 (u . v)
        dot_prod = np.dot(X_batch, X_W.T)
        dist_sq = batch_sq_norms + X_W_sq_norms[np.newaxis, :] - 2.0 * dot_prod
        dist_sq = np.maximum(0.0, dist_sq)
        dist = np.sqrt(dist_sq)

        # Raw Gaussian RBF similarity: S = exp(-gamma * dist)
        S_raw = np.exp(-gamma * dist)

        # Fast Vectorized Genre Compatibility Matrix Lookup
        G_batch = M_compat[batch_genre_ids][:, genre_ids]

        # Final Anchored Similarity Score
        S_batch = S_raw * G_batch

        batch_len = end_idx - start_idx
        for i_local in range(batch_len):
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
        X_scaled=dataset.X_scaled,
    )


def get_or_build_graph(
    csv_path: str,
    cache_path: Optional[str] = None,
    force_rebuild: bool = False,
    feature_weights: Optional[dict[str, float]] = None,
    threshold: float = 0.3,
    top_k: int = 300,
    batch_size: int = 1000,
) -> GraphEngine:
    """
    Main entrypoint for obtaining a GraphEngine instance.
    Checks if a cached graph file exists at cache_path. If so, loads it directly.
    Otherwise, builds the graph from csv_path, caches it to cache_path, and returns it.
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
