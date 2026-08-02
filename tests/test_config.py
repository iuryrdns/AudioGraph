"""
Unit tests for src/config.py centralized configuration module
"""

import os

from src.config import BuilderConfig, RecommenderConfig
from src.graph.builder import build_graph
from src.graph.loader import load_and_preprocess_dataset
from src.graph.recommender import AdaptiveRadioRecommender

SMALL_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "small_spotify_tracks_dataset.csv"
)


def test_builder_config_defaults():
    cfg = BuilderConfig()
    assert cfg.gamma == 2.0
    assert cfg.threshold == 0.3
    assert cfg.top_k == 300
    assert cfg.batch_size == 1000
    assert "danceability" in cfg.feature_weights


def test_recommender_config_defaults():
    cfg = RecommenderConfig()
    assert cfg.history_size == 15
    assert cfg.exploration_prob == 0.15
    assert cfg.artist_boost == 1.35
    assert cfg.genre_boost == 1.20
    assert cfg.trajectory_alpha == 0.6
    assert cfg.session_weight == 0.3
    assert cfg.metadata_weights["artist"] == 0.8


def test_build_graph_with_custom_config():
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    custom_cfg = BuilderConfig(threshold=0.5, top_k=20)
    graph = build_graph(dataset, config=custom_cfg)
    assert len(graph) == len(dataset)


def test_recommender_with_custom_config():
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    graph = build_graph(dataset, threshold=0.3, top_k=50)
    custom_rec_cfg = RecommenderConfig(history_size=5, artist_boost=2.0)
    recommender = AdaptiveRadioRecommender(graph, config=custom_rec_cfg)

    assert recommender.history_size == 5
    assert recommender.artist_boost == 2.0
