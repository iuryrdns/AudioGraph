"""
AudioGraph-AI Main CLI Demonstration Script
"""

import argparse
import os
import random
import time
from typing import Optional

from src.graph.builder import get_or_build_graph
from src.graph.recommender import AdaptiveRadioRecommender

ENRICHED_DATASET_PATH = os.path.join("data", "spotify_tracks_dataset_itunes.csv")
RAW_DATASET_PATH = os.path.join("data", "spotify_tracks_dataset.csv")
DEFAULT_DATASET_PATH = ENRICHED_DATASET_PATH if os.path.exists(ENRICHED_DATASET_PATH) else RAW_DATASET_PATH
DEFAULT_CACHE_PATH = os.path.join("data", "spotify_graph_cache.pkl")


def load_env_file(filepath: str = ".env") -> None:
    """Lightweight zero-dependency .env file parser."""
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val


def parse_args():
    parser = argparse.ArgumentParser(
        description="AudioGraph-AI: Adaptive Radio Music Recommender Engine"
    )
    parser.add_argument(
        "--rebuild",
        "--force-rebuild",
        action="store_true",
        help="Force rebuild graph matrix, invalidating any existing cache file.",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Delete existing graph cache file from disk.",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=DEFAULT_DATASET_PATH,
        help=f"Path to dataset CSV file (default: {DEFAULT_DATASET_PATH}).",
    )
    parser.add_argument(
        "--cache",
        type=str,
        default=DEFAULT_CACHE_PATH,
        help=f"Path to graph cache pickle file (default: {DEFAULT_CACHE_PATH}).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of recommendations to generate in stream (default: 10).",
    )
    parser.add_argument(
        "--seed-id",
        type=str,
        default=None,
        help="Specific track ID to use as starting seed.",
    )
    parser.add_argument(
        "--seed-index",
        type=int,
        default=None,
        help="Specific track index (0 to N-1) to use as starting seed.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="RNG seed integer for reproducible recommendation sampling.",
    )

    return parser.parse_args()


def main():
    # Load .env file if present
    load_env_file(".env")
    args = parse_args()

    # Handle --clear-cache
    if args.clear_cache:
        if os.path.exists(args.cache):
            os.remove(args.cache)
            print(f"[✓] Cache file '{args.cache}' removed successfully.")
        else:
            print(f"[*] Cache file '{args.cache}' does not exist.")

        if not args.rebuild:
            return

    print("AudioGraph-AI: recomendação de músicas")
    print()

    start_time = time.time()
    rebuild_msg = " (FORCING REBUILD)" if args.rebuild else ""
    print(
        f"[*] Carregando graph engine (Dataset: '{args.dataset}', Cache: '{args.cache}'){rebuild_msg}..."
    )

    graph = get_or_build_graph(
        csv_path=args.dataset,
        cache_path=args.cache,
        force_rebuild=args.rebuild,
        threshold=0.3,
        top_k=300,
    )
    elapsed = time.time() - start_time
    print(f"[+] Graph engine carregado com {len(graph)} músicas em {elapsed:.3f} segundos.")

    # 1. Determine RNG Random Seed (from CLI or .env)
    env_random_seed = os.getenv("RANDOM_SEED") or os.getenv("RECOMMENDER_SEED")
    if args.random_seed is not None:
        rng_seed: Optional[int] = args.random_seed
    elif env_random_seed and env_random_seed.lower() not in ("random", "none", ""):
        try:
            rng_seed = int(env_random_seed)
        except ValueError:
            rng_seed = None
    else:
        rng_seed = None

    # 2. Initialize Recommender Engine
    recommender = AdaptiveRadioRecommender(
        graph=graph,
        history_size=15,
        exploration_prob=0.15,
        artist_boost=1.35,
        genre_boost=1.20,
        random_seed=rng_seed,
    )

    # 3. Determine Starting Seed Track (from CLI, .env, or random)
    env_track_id = os.getenv("SEED_TRACK_ID") or os.getenv("SEED_ID")
    env_index = os.getenv("SEED_INDEX")
    unified_seed = os.getenv("SEED")

    target_seed_id = args.seed_id or env_track_id
    target_seed_index = (
        args.seed_index
        if args.seed_index is not None
        else (int(env_index) if env_index and env_index.isdigit() else None)
    )

    # Unified SEED fallback parsing
    if not target_seed_id and target_seed_index is None and unified_seed:
        if unified_seed.lower() not in ("random", "none", ""):
            if unified_seed in graph:
                target_seed_id = unified_seed
            elif unified_seed.isdigit() and int(unified_seed) < len(graph):
                target_seed_index = int(unified_seed)

    if target_seed_id and target_seed_id in graph:
        seed_track_id = target_seed_id
    elif target_seed_index is not None and 0 <= target_seed_index < len(graph):
        seed_track_id = str(graph.idx_to_id[target_seed_index])
    else:
        seed_track_id = str(random.choice(graph.idx_to_id))

    seed_meta = graph.get_metadata(seed_track_id)

    print()
    print(f" Semente : '{seed_meta.get('track_name')}'")
    print(f" Artista(s)   : {seed_meta.get('artists')}")
    print(f" Gênero      : {seed_meta.get('track_genre')}")
    print()

    # 4. Generate Recommendation Queue
    stream_count = args.count
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
