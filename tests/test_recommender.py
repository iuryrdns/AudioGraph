"""
Unit tests for src/graph/recommender.py and src/graph/taxonomy.py
"""

import os

import numpy as np
import pytest

from src.graph.builder import build_graph
from src.graph.loader import load_and_preprocess_dataset
from src.graph.recommender import (
    AdaptiveRadioRecommender,
    RecommendationResult,
)
from src.graph.taxonomy import get_genre_compatibility, get_super_genre

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
        artist_boost=1.35,
        genre_boost=1.20,
        trajectory_alpha=0.6,
        session_weight=0.3,
        random_seed=42,
    )


def test_taxonomy():
    assert get_super_genre("acoustic") == "ACOUSTIC_INDIE"
    assert get_super_genre("sad") == "ACOUSTIC_INDIE"
    assert get_super_genre("folk") == "ACOUSTIC_INDIE"
    assert get_super_genre("indian-folk") == "WORLD_MEDIA"
    assert get_super_genre("música indiana") == "WORLD_MEDIA"
    assert get_super_genre("edm") == "ELECTRONIC_DANCE"
    assert get_super_genre("heavy-metal") == "ROCK_METAL"

    assert get_genre_compatibility("acoustic", "acoustic") == 1.0
    assert get_genre_compatibility("acoustic", "sad") == 0.85
    assert get_genre_compatibility("folk", "folk") == 1.0
    assert get_genre_compatibility("folk", "indian-folk") == 0.15
    assert get_genre_compatibility("indian-folk", "indian") == 0.85
    assert get_genre_compatibility("acoustic", "pop") == 0.50
    assert get_genre_compatibility("acoustic", "heavy-metal") == 0.15
    # Ensure unknown OTHER genres do not get false 0.85 similarity
    assert get_genre_compatibility("unmapped_genre1", "unmapped_genre2") == 0.15


def test_recommend_next(sample_recommender):
    seed_id = sample_recommender.graph.idx_to_id[0]
    result = sample_recommender.recommend_next(seed_id)

    assert isinstance(result, RecommendationResult)
    assert isinstance(result.recommended_track_id, str)
    assert result.recommended_track_id != seed_id
    assert "track_name" in result.track_metadata
    assert result.score > 0.0
    assert len(result.explanation) > 0


def test_session_trajectory_memory(sample_recommender):
    seed_id = sample_recommender.graph.idx_to_id[0]
    assert sample_recommender.session_vector is None

    # First recommendation updates session vector
    rec1 = sample_recommender.recommend_next(seed_id)
    assert sample_recommender.session_vector is not None
    assert isinstance(sample_recommender.session_vector, np.ndarray)

    initial_vec = np.copy(sample_recommender.session_vector)

    # Second recommendation updates EMA session vector
    sample_recommender.recommend_next(rec1.recommended_track_id)
    assert not np.array_equal(sample_recommender.session_vector, initial_vec)

    # Reset session clears vector
    sample_recommender.reset_session()
    assert sample_recommender.session_vector is None


def test_history_buffer_maintenance(sample_recommender):
    seed_id = sample_recommender.graph.idx_to_id[0]
    history = sample_recommender.get_history()
    assert len(history) == 0

    rec1 = sample_recommender.recommend_next(seed_id)
    history = sample_recommender.get_history()
    assert seed_id in history
    assert rec1.recommended_track_id in history

    rec2 = sample_recommender.recommend_next(rec1.recommended_track_id)
    assert rec2.recommended_track_id != rec1.recommended_track_id
    assert rec2.recommended_track_id != seed_id


def test_recommend_stream(sample_recommender):
    seed_id = sample_recommender.graph.idx_to_id[0]
    stream = sample_recommender.recommend_stream(seed_id, count=10)

    assert len(stream) == 10
    played_ids = [rec.recommended_track_id for rec in stream]
    assert len(set(played_ids)) == len(played_ids)


def test_invalid_track_id(sample_recommender):
    with pytest.raises(KeyError):
        sample_recommender.recommend_next("INVALID_TRACK_ID")


def test_recommend_with_exclude_and_feedback(sample_recommender):
    seed_id = str(sample_recommender.graph.idx_to_id[0])
    target_excluded = str(sample_recommender.graph.idx_to_id[1])

    feedback = {
        "liked_artists": ["Genie"],
        "liked_genres": ["pop"],
        "disliked_artists": ["Junk Artist"],
        "disliked_genres": ["metal"],
    }

    stream = sample_recommender.recommend_stream(
        seed_id,
        count=5,
        exclude_ids=[target_excluded],
        feedback=feedback,
    )

    rec_ids = [r.recommended_track_id for r in stream]
    assert target_excluded not in rec_ids
    assert len(stream) == 5

