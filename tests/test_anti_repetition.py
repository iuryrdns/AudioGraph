"""
Teste: history_size evita repetição de
músicas dentro da janela configurada.
"""

import os

from src.graph.builder import build_graph
from src.graph.loader import load_and_preprocess_dataset
from src.graph.recommender import AdaptiveRadioRecommender

SMALL_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "small_spotify_tracks_dataset.csv"
)


def test_no_repetition_within_history_window():
    dataset = load_and_preprocess_dataset(SMALL_DATASET_PATH)
    graph = build_graph(dataset, threshold=0.3, top_k=50)

    history_size = 8
    recommender = AdaptiveRadioRecommender(
        graph,
        history_size=history_size,
        exploration_prob=0.15,
        random_seed=7,
    )

    seed_id = graph.idx_to_id[0]
    stream = recommender.recommend_stream(seed_id, count=25)
    played_ids = [seed_id] + [rec.recommended_track_id for rec in stream]

    print(f"\nSequência gerada ({len(played_ids)} músicas, history_size={history_size}):")
    for i, tid in enumerate(played_ids):
        name = graph.get_metadata(tid).get("track_name", tid)
        print(f"  {i:2d}. {name}")

    # Dentro de qualquer janela deslizante de tamanho history_size,
    # não pode haver repetição de música
    violations = []
    for i in range(len(played_ids)):
        window = played_ids[max(0, i - history_size + 1): i + 1]
        if len(set(window)) != len(window):
            violations.append(i)

    print("Janelas com repetição:", violations if violations else "nenhuma")
    assert not violations, f"Repetição encontrada dentro da janela em índices {violations}"