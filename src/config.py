"""
Contains default configuration classes for graph construction (BuilderConfig)
and next-track recommendation (RecommenderConfig).
"""

from dataclasses import dataclass, field


@dataclass
class BuilderConfig:
    """
    Hyperparameters for graph construction (src/graph/builder.py).
    """

    gamma: float = 2.0  # RBF distance scaling hyperparameter
    threshold: float = 0.3  # Similarity pruning threshold
    top_k: int = 300  # Directed degree capping (max outgoing neighbors)
    batch_size: int = (
        1000  # Chunk size for vectorized BLAS similarity matrix calculation
    )
    feature_weights: dict[str, float] = field(
        default_factory=lambda: {
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
    )


@dataclass
class RecommenderConfig:
    """
    Hyperparameters for Adaptive Radio next-track recommendation (src/graph/recommender.py).
    """

    history_size: int = 15  # Anti-repetition circular buffer size
    exploration_prob: float = 0.15  # Probability of triggering 2-hop exploration
    artist_boost: float = (
        1.35  # Multiplier for 1-hop candidates with matching artist (+35%)
    )
    genre_boost: float = (
        1.20  # Multiplier for 1-hop candidates with matching genre (+20%)
    )
    trajectory_alpha: float = 0.6  # Decay rate alpha for Session Trajectory EMA vector
    session_weight: float = (
        0.3  # Weight assigned to global session alignment vs local transition
    )
    metadata_weights: dict[str, float] = field(
        default_factory=lambda: {
            "artist": 0.8,
            "album": 0.7,
            "genre": 0.5,
        }
    )


DEFAULT_BUILDER_CONFIG = BuilderConfig()
DEFAULT_RECOMMENDER_CONFIG = RecommenderConfig()
