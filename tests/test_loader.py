"""
Unit tests for src/graph/loader.py
"""

import os

import numpy as np
import pytest

from src.graph.loader import (
    FEATURE_COLUMNS,
    TrackDataset,
    load_and_preprocess_dataset,
    parse_artist_string,
)

SMALL_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "small_spotify_tracks_dataset.csv"
)


def test_parse_artist_string():
    assert parse_artist_string("YUNGBLUD;Charlotte Lawrence") == [
        "YUNGBLUD",
        "Charlotte Lawrence",
    ]
    assert parse_artist_string(" Linkin Park ") == ["Linkin Park"]
    assert parse_artist_string("") == ["Unknown Artist"]
    assert parse_artist_string("  ;  ") == ["Unknown Artist"]


def test_load_and_preprocess_dataset():
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)

    assert isinstance(dataset, TrackDataset)
    assert len(dataset) > 0

    # Verify scaled feature matrix
    assert dataset.X_scaled.shape[0] == len(dataset)
    assert dataset.X_scaled.shape[1] == len(FEATURE_COLUMNS)
    assert dataset.X_scaled.dtype == np.float32

    # Verify ID index lookup maps
    assert len(dataset.id_to_idx) == len(dataset)
    assert len(dataset.idx_to_id) == len(dataset)

    first_track_id = dataset.idx_to_id[0]
    assert dataset.id_to_idx[first_track_id] == 0

    # Verify metadata retrieval
    meta = dataset.get_track_metadata(first_track_id)
    assert "track_id" in meta
    assert "artists" in meta
    assert "primary_artist" in meta
    assert "artist_list" in meta
    assert "album_entity" in meta
    assert "genre_entity" in meta

    # Verify MinMaxScaler properties (all feature values bounded between 0.0 and 1.0)
    assert np.all(dataset.X_scaled >= 0.0)
    assert np.all(dataset.X_scaled <= 1.0)


def test_invalid_track_id():
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    with pytest.raises(KeyError):
        dataset.get_track_metadata("NON_EXISTENT_ID")
