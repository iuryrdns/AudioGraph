"""
Unit tests for src/graph/recommender.py
"""

import os
import pytest
from src.graph.loader import load_and_preprocess_dataset
from src.graph.builder import build_graph
from src.graph.recommender import (
    AdaptiveRadioRecommender,
    RecommendationResult,
)

SMALL_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "small_spotify_tracks_dataset.csv"
)


@pytest.fixture
def sample_recommender():
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    graph = build_graph(dataset, threshold=0.3, top_k=50)
    return AdaptiveRadioRecommender(
        graph,
        history_size=15,
        exploration_prob=0.15,
        artist_boost=1.25,
        genre_boost=1.15,
        random_seed=42,
    )


def test_recommend_next(sample_recommender):
    seed_id = sample_recommender.graph.idx_to_id[0]
    result = sample_recommender.recommend_next(seed_id)

    assert isinstance(result, RecommendationResult)
    assert isinstance(result.recommended_track_id, str)
    assert result.recommended_track_id != seed_id
    assert "track_name" in result.track_metadata
    assert result.score > 0.0
    assert len(result.explanation) > 0


def test_metadata_boost_parameters(sample_recommender):
    assert sample_recommender.artist_boost == 1.25
    assert sample_recommender.genre_boost == 1.15

    seed_id = sample_recommender.graph.idx_to_id[0]
    result = sample_recommender.recommend_next(seed_id)
    assert isinstance(result.explanation, str)


def test_history_buffer_maintenance(sample_recommender):
    seed_id = sample_recommender.graph.idx_to_id[0]
    history = sample_recommender.get_history()
    assert len(history) == 0

    rec1 = sample_recommender.recommend_next(seed_id)
    history = sample_recommender.get_history()
    assert seed_id in history
    assert rec1.recommended_track_id in history

    # Ensure recommended track is not immediately re-recommended
    rec2 = sample_recommender.recommend_next(rec1.recommended_track_id)
    assert rec2.recommended_track_id != rec1.recommended_track_id
    assert rec2.recommended_track_id != seed_id


def test_recommend_stream(sample_recommender):
    seed_id = sample_recommender.graph.idx_to_id[0]
    stream = sample_recommender.recommend_stream(seed_id, count=10)

    assert len(stream) == 10
    played_ids = [rec.recommended_track_id for rec in stream]

    # Verify no duplicates in small stream
    assert len(set(played_ids)) == len(played_ids)


def test_invalid_track_id(sample_recommender):
    with pytest.raises(KeyError):
        sample_recommender.recommend_next("INVALID_TRACK_ID")


def test_reset_history(sample_recommender):
    seed_id = sample_recommender.graph.idx_to_id[0]
    sample_recommender.recommend_next(seed_id)
    assert len(sample_recommender.get_history()) > 0

    sample_recommender.reset_history()
    assert len(sample_recommender.get_history()) == 0
