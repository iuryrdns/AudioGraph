"""
AudioGraph-AI Main CLI Demonstration Script
"""

import os
import time

from src.graph.builder import get_or_build_graph
from src.graph.recommender import AdaptiveRadioRecommender

DATASET_PATH = os.path.join("data", "spotify_tracks_dataset.csv")
CACHE_PATH = os.path.join("data", "spotify_graph_cache.pkl")


def main():
    print("AudioGraph-AI: recomendação de músicas")
    print()

    start_time = time.time()
    print(f"[*] Carregando graph engine (Dataset: '{DATASET_PATH}', Cache: '{CACHE_PATH}')...")

    graph = get_or_build_graph(
        csv_path=DATASET_PATH,
        cache_path=CACHE_PATH,
        threshold=0.3,
        top_k=300,
    )
    elapsed = time.time() - start_time
    print(f"[+] Graph engine carregado com {len(graph)} músicas em {elapsed:.3f} segundos.")

    # 2. Initialize Recommender Engine
    recommender = AdaptiveRadioRecommender(
        graph=graph,
        history_size=15,
        exploration_prob=0.15,
        random_seed=42,
    )

    # 3. Select Seed Track
    seed_track_id = graph.idx_to_id[0]
    seed_meta = graph.get_metadata(seed_track_id)

    print()
    print(f" Semente : '{seed_meta.get('track_name')}'")
    print(f" Artista(s)   : {seed_meta.get('artists')}")
    print(f" Gênero      : {seed_meta.get('track_genre')}")
    print()

    # 4. Generate Recommendation Queue
    stream_count = 10
    print(f"[*] Gerando fila com {stream_count} músicas...\n")
    stream = recommender.recommend_stream(seed_track_id, count=stream_count)

    for idx, rec in enumerate(stream, 1):
        meta = rec.track_metadata
        print(f" #{idx:02d} | [{rec.recommendation_type.upper()}] (Correlação: {rec.score:.2f})")
        print(f"     Nome  : {meta.get('track_name')}")
        print(f"     Artista : {meta.get('primary_artist')}")
        print(f"     Gênero  : {meta.get('track_genre')}")
        print(f"     Razão : {rec.explanation}\n")

    print()
    print("Fila completa sem nenhum loop")
    print()

if __name__ == "__main__":
    main()
