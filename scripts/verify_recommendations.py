"""
AudioGraph-AI Ground-Truth Verification Script

Queries external authoritative music metadata APIs (iTunes Search API) to fetch
real-world primary genres for recommendations and compares dataset genres against ground-truth.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from typing import Dict, Optional

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.graph.builder import get_or_build_graph
from src.graph.recommender import AdaptiveRadioRecommender

DEFAULT_DATASET_PATH = os.path.join("data", "spotify_tracks_dataset.csv")
DEFAULT_CACHE_PATH = os.path.join("data", "spotify_graph_cache.pkl")


def fetch_itunes_metadata(artist: str, track_name: str) -> Optional[Dict[str, str]]:
    """
    Queries iTunes Search API for authoritative track metadata and real-world primary genre.
    """
    clean_artist = artist.split(";")[0].split(" feat")[0].strip()
    clean_track = track_name.split("(")[0].split("-")[0].strip()
    query = f"{clean_artist} {clean_track}"

    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
    req = urllib.request.Request(url, headers={"User-Agent": "AudioGraph-AI/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                item = results[0]
                return {
                    "artist_name": item.get("artistName", artist),
                    "track_name": item.get("trackName", track_name),
                    "primary_genre": item.get("primaryGenreName", "Unknown"),
                    "album_name": item.get("collectionName", "Unknown"),
                }
    except Exception:
        pass
    return None


def verify_recommendation_stream(seed_track_id: str, count: int = 10):
    print("=" * 95)
    print("       AudioGraph-AI Ground-Truth Verification Report (iTunes Search API)")
    print("=" * 95)

    graph = get_or_build_graph(
        csv_path=DEFAULT_DATASET_PATH,
        cache_path=DEFAULT_CACHE_PATH,
    )

    recommender = AdaptiveRadioRecommender(
        graph=graph,
        history_size=15,
        exploration_prob=0.15,
        artist_boost=1.35,
        genre_boost=1.20,
        random_seed=42,
    )

    # 1. Fetch seed track metadata
    seed_meta = graph.get_metadata(seed_track_id)
    seed_name = seed_meta.get("track_name", seed_track_id)
    seed_artist = seed_meta.get("primary_artist", "Unknown")
    dataset_seed_genre = seed_meta.get("track_genre", "Unknown")

    print(f"\n[*] Fetching ground-truth data for seed track: '{seed_name}' by {seed_artist}...")
    itunes_seed = fetch_itunes_metadata(seed_artist, seed_name)
    real_seed_genre = itunes_seed.get("primary_genre") if itunes_seed else "Unknown"

    print("\n" + "-" * 95)
    print(f" SEED TRACK       : '{seed_name}' by {seed_artist}")
    print(f" DATASET GENRE    : {dataset_seed_genre} (Assigned in Kaggle CSV)")
    print(f" REAL-WORLD GENRE : {real_seed_genre} (Authoritative iTunes Search API)")
    print("-" * 95 + "\n")

    if dataset_seed_genre.lower() != real_seed_genre.lower():
        print(
            f"[!] DATASET DISCREPANCY CONFIRMED: Track '{seed_name}' was tagged as '{dataset_seed_genre}' "
            f"in the Kaggle CSV dataset, but its real-world authoritative genre is '{real_seed_genre}'!\n"
        )

    # 2. Generate recommendations
    stream = recommender.recommend_stream(seed_track_id, count=count)

    print(f"[*] Verifying {count} recommendations against real-world ground-truth API...\n")
    print(f"{'#':<3} | {'TRACK NAME':<28} | {'ARTIST':<18} | {'DATASET GENRE':<14} | {'REAL-WORLD GENRE':<20}")
    print("-" * 95)

    for idx, rec in enumerate(stream, 1):
        meta = rec.track_metadata
        t_name = str(meta.get("track_name", ""))[:27]
        t_artist = str(meta.get("primary_artist", ""))[:17]
        ds_genre = str(meta.get("track_genre", ""))[:13]

        itunes_info = fetch_itunes_metadata(t_artist, t_name)
        real_genre = itunes_info.get("primary_genre", "N/A") if itunes_info else "N/A"

        print(f"{idx:02d}  | {t_name:<28} | {t_artist:<18} | {ds_genre:<14} | {real_genre:<20}")
        time.sleep(0.15)

    print("-" * 95)
    print("[✓] Ground-truth verification report generated successfully.\n")


if __name__ == "__main__":
    seed = sys.argv[1] if len(sys.argv) > 1 else "4lghbrxf9haQUp6BuRjAEq"  # Default 'big talk'
    verify_recommendation_stream(seed, count=10)
