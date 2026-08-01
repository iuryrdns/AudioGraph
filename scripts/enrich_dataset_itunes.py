"""
AudioGraph-AI Dataset Enrichment & Genre Swapper Script

Queries Deezer API & iTunes API in parallel to extract authoritative real-world primary genres,
30-second audio preview URLs, and album cover art for dataset tracks. Saves a persistent
resumable cache and outputs 'data/spotify_tracks_dataset_itunes.csv'.
"""

import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

import pandas as pd

# Path definitions
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INPUT_CSV_PATH = os.path.join(PROJECT_ROOT, "data", "spotify_tracks_dataset.csv")
OUTPUT_CSV_PATH = os.path.join(PROJECT_ROOT, "data", "spotify_tracks_dataset_itunes.csv")
CACHE_JSON_PATH = os.path.join(PROJECT_ROOT, "data", "itunes_cache.json")


def clean_query_term(text: str) -> str:
    """
    Cleans track titles and artist names for high-precision search API matching.
    """
    if not isinstance(text, str):
        return ""
    text = text.split(";")[0]
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"-.*", "", text)
    return text.strip()


def query_deezer_api(artist: str, track_name: str) -> Optional[Dict[str, str]]:
    """
    Queries Deezer API for authoritative metadata, genres, preview MP3 URLs, and cover art.
    """
    clean_artist = clean_query_term(artist)
    clean_track = clean_query_term(track_name)

    if not clean_track:
        return None

    query = f"{clean_artist} {clean_track}".strip()
    url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )

    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            if items:
                item = items[0]
                preview_url = item.get("preview", "")
                artwork_url = item.get("album", {}).get("cover_medium", "")

                # Query album for explicit genre if available
                genre_name = ""
                album_id = item.get("album", {}).get("id")
                if album_id:
                    alb_url = f"https://api.deezer.com/album/{album_id}"
                    alb_req = urllib.request.Request(alb_url, headers={"User-Agent": "Mozilla/5.0"})
                    try:
                        with urllib.request.urlopen(alb_req, timeout=3) as a_resp:
                            alb_data = json.loads(a_resp.read().decode("utf-8"))
                            genres = alb_data.get("genres", {}).get("data", [])
                            if genres:
                                genre_name = genres[0].get("name", "")
                    except Exception:
                        pass

                return {
                    "itunes_genre": genre_name,
                    "preview_url": preview_url,
                    "artwork_url": artwork_url,
                    "itunes_artist": item.get("artist", {}).get("name", artist),
                    "itunes_track_name": item.get("title", track_name),
                }
    except Exception:
        pass

    return None


def query_itunes_api(artist: str, track_name: str) -> Optional[Dict[str, str]]:
    """
    Fallback query to iTunes Search API.
    """
    clean_artist = clean_query_term(artist)
    clean_track = clean_query_term(track_name)

    if not clean_track:
        return None

    query = f"{clean_artist} {clean_track}".strip()
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )

    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                item = results[0]
                return {
                    "itunes_genre": item.get("primaryGenreName", ""),
                    "preview_url": item.get("previewUrl", ""),
                    "artwork_url": item.get("artworkUrl100", ""),
                    "itunes_artist": item.get("artistName", ""),
                    "itunes_track_name": item.get("trackName", ""),
                }
    except Exception:
        pass

    return None


def query_music_api(artist: str, track_name: str) -> Optional[Dict[str, str]]:
    """
    Combined query: tries Deezer API first, then iTunes API as fallback.
    """
    res = query_deezer_api(artist, track_name)
    if res and (res.get("preview_url") or res.get("itunes_genre")):
        return res

    return query_itunes_api(artist, track_name)


def load_cache() -> Dict[str, Dict[str, str]]:
    if os.path.exists(CACHE_JSON_PATH):
        try:
            with open(CACHE_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache: Dict[str, Dict[str, str]]) -> None:
    tmp_path = CACHE_JSON_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, CACHE_JSON_PATH)


def enrich_dataset(
    max_workers: int = 20,
    batch_size: int = 200,
    limit_tracks: Optional[int] = None,
):
    print("=" * 80)
    print("      AudioGraph-AI API Dataset Enrichment & Genre Swapper (Deezer + iTunes)")
    print("=" * 80)

    # 1. Load CSV
    print(f"[*] Loading dataset CSV from '{INPUT_CSV_PATH}'...")
    df = pd.read_csv(INPUT_CSV_PATH)
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    df = df.dropna(subset=["track_id", "track_name", "artists"]).drop_duplicates(subset=["track_id"]).reset_index(drop=True)

    if limit_tracks:
        print(f"[*] Limiting processing to first {limit_tracks} tracks (for quick testing)...")
        df = df.iloc[:limit_tracks].copy()

    total_tracks = len(df)
    print(f"[+] Dataset loaded: {total_tracks} tracks.\n")

    # 2. Load existing cache
    cache = load_cache()
    print(f"[*] Persistent cache status: {len(cache)} / {total_tracks} tracks already in cache.")

    # Filter out empty cache markers from previous failed attempts
    uncached_indices = []
    for idx, row in df.iterrows():
        tid = str(row["track_id"])
        if tid not in cache or not cache[tid].get("preview_url"):
            uncached_indices.append(idx)

    print(f"[*] Tracks remaining to enrich: {len(uncached_indices)}\n")

    if uncached_indices:
        print(f"[*] Starting parallel API enrichment ({max_workers} worker threads)...")
        start_time = time.time()
        processed_count = 0
        matches_found = 0

        for batch_start in range(0, len(uncached_indices), batch_size):
            batch_idx = uncached_indices[batch_start : batch_start + batch_size]

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_tid = {
                    executor.submit(
                        query_music_api,
                        str(df.loc[i, "artists"]),
                        str(df.loc[i, "track_name"]),
                    ): str(df.loc[i, "track_id"])
                    for i in batch_idx
                }

                for future in concurrent.futures.as_completed(future_to_tid):
                    tid = future_to_tid[future]
                    res = future.result()
                    if res and (res.get("preview_url") or res.get("itunes_genre")):
                        cache[tid] = res
                        matches_found += 1
                    else:
                        cache[tid] = {
                            "itunes_genre": "",
                            "preview_url": "",
                            "artwork_url": "",
                        }
                    processed_count += 1

            save_cache(cache)
            elapsed = time.time() - start_time
            rate = processed_count / (elapsed if elapsed > 0 else 1.0)
            overall_progress = len(cache) / total_tracks * 100.0

            print(
                f"    -> Enriched {len(cache)} / {total_tracks} ({overall_progress:.1f}%) | "
                f"Batch matches: {matches_found} | Speed: {rate:.1f} tracks/sec"
            )

        print(f"\n[+] API enrichment complete in {time.time() - start_time:.1f} seconds!")

    # 4. Map enriched metadata back to DataFrame
    print("\n[*] Swapping dataset genres and attaching preview MP3 & cover art URLs...")

    itunes_genres = []
    preview_urls = []
    artwork_urls = []

    swapped_count = 0
    fallback_count = 0

    for idx, row in df.iterrows():
        tid = str(row["track_id"])
        orig_genre = str(row["track_genre"])
        info = cache.get(tid, {})

        new_genre = info.get("itunes_genre", "").strip()
        p_url = info.get("preview_url", "")
        a_url = info.get("artwork_url", "")

        if new_genre:
            itunes_genres.append(new_genre)
            swapped_count += 1
        else:
            itunes_genres.append(orig_genre)
            fallback_count += 1

        preview_urls.append(p_url)
        artwork_urls.append(a_url)

    df["raw_dataset_genre"] = df["track_genre"]
    df["track_genre"] = itunes_genres
    df["preview_url"] = preview_urls
    df["artwork_url"] = artwork_urls

    # 5. Save Enriched CSV
    print(f"[*] Saving enriched dataset to '{OUTPUT_CSV_PATH}'...")
    df.to_csv(OUTPUT_CSV_PATH, index=False)

    valid_previews = sum(1 for u in preview_urls if u)
    valid_artworks = sum(1 for a in artwork_urls if a)

    print("\n" + "=" * 80)
    print(" ENRICHMENT & GENRE SWAPPING SUMMARY")
    print("=" * 80)
    print(f" Total Tracks Processed  : {total_tracks}")
    print(f" Swapped Real Genres    : {swapped_count} ({swapped_count / total_tracks * 100.0:.1f}%)")
    print(f" Fallback Dataset Genres : {fallback_count} ({fallback_count / total_tracks * 100.0:.1f}%)")
    print(f" Audio Preview URLs     : {valid_previews} ({valid_previews / total_tracks * 100.0:.1f}%)")
    print(f" Album Cover Art URLs   : {valid_artworks} ({valid_artworks / total_tracks * 100.0:.1f}%)")
    print(f" Output File            : '{OUTPUT_CSV_PATH}'")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    enrich_dataset(max_workers=20, limit_tracks=limit)
