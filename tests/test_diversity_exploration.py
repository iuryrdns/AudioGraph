"""
Teste comparativo: efeito do parâmetro `exploration_prob` na diversidade
das sequências geradas pelo AdaptiveRadioRecommender.
"""
import os
from src.graph.builder import build_graph
from src.graph.loader import load_and_preprocess_dataset
from src.graph.recommender import AdaptiveRadioRecommender

SMALL_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "small_spotify_tracks_dataset.csv"
)


def _build_recommender(exploration_prob: float) -> AdaptiveRadioRecommender:
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    graph = build_graph(dataset, threshold=0.3, top_k=50)
    return AdaptiveRadioRecommender(
        graph,
        history_size=15,
        exploration_prob=exploration_prob,
        artist_boost=1.35,
        genre_boost=1.20,
        trajectory_alpha=0.6,
        session_weight=0.3,
        random_seed=42,  # mesma seed para comparação justa
    )


def _summarize_stream(recommender, seed_id, count=15):
    stream = recommender.recommend_stream(seed_id, count=count)
    artists, genres, types, sequence = set(), set(), {}, []
    for rec in stream:
        meta = rec.track_metadata
        artists.add(meta.get("primary_artist", "unknown"))
        genres.add(meta.get("track_genre", "unknown"))
        types[rec.recommendation_type] = types.get(rec.recommendation_type, 0) + 1
        sequence.append(
            f"{meta.get('track_name', rec.recommended_track_id)}"
            f" — {meta.get('primary_artist', '?')} ({rec.recommendation_type})"
        )
    return {
        "sequence": sequence,
        "n_unique_artists": len(artists),
        "n_unique_genres": len(genres),
        "types": types,
    }


def test_diversity_increases_with_exploration_prob():
    seed_dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    seed_graph = build_graph(seed_dataset, threshold=0.3, top_k=50)
    seed_id = seed_graph.idx_to_id[0]

    low = _build_recommender(exploration_prob=0.0)
    high = _build_recommender(exploration_prob=0.9)

    low_summary = _summarize_stream(low, seed_id, count=15)
    high_summary = _summarize_stream(high, seed_id, count=15)

    print("\nexploration_prob = 0.0")
    for line in low_summary["sequence"]:
        print(" ", line)
    print("Gêneros únicos:", low_summary["n_unique_genres"])
    print("Tipos de recomendação:", low_summary["types"])

    print("\nexploration_prob = 0.9")
    for line in high_summary["sequence"]:
        print(" ", line)
    print("Gêneros únicos:", high_summary["n_unique_genres"])
    print("Tipos de recomendação:", high_summary["types"])

    assert high_summary["n_unique_genres"] >= low_summary["n_unique_genres"]
    assert "2-hop multi-hop" in high_summary["types"] or "fallback" in high_summary["types"]