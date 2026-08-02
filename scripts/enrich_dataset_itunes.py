"""
Queries Deezer API & iTunes API in parallel to extract authoritative real-world primary genres,
30-second audio preview URLs, and album cover art for dataset tracks. Saves a persistent
resumable cache and outputs 'data/spotify_tracks_dataset_itunes.csv'.
"""

import argparse
import concurrent.futures
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

console = Console()

# Path definitions
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INPUT_CSV_PATH = os.path.join(PROJECT_ROOT, "data", "spotify_tracks_dataset.csv")
OUTPUT_CSV_PATH = os.path.join(
    PROJECT_ROOT, "data", "spotify_tracks_dataset_itunes.csv"
)
CACHE_JSON_PATH = os.path.join(PROJECT_ROOT, "data", "itunes_cache.json")

# In-memory album genre cache & lock
ALBUM_GENRE_CACHE: dict[int, str] = {}
ALBUM_CACHE_LOCK = threading.Lock()


def clean_query_term(text: str) -> str:
    """
    Cleans track titles and artist names for high-precision search API matching.
    Preserves hyphenated words while removing metadata suffixes, feat/ft clauses,
    and normalizing unicode dashes (en-dash, em-dash).
    """
    if not isinstance(text, str):
        return ""
    text = text.split(";")[0]
    # Normalize unicode dashes to standard ASCII hyphen
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+-\s+.*$", "", text)
    text = re.sub(r"\b(feat|ft)\.?\s+.*$", "", text, flags=re.IGNORECASE)
    return text.strip()


def is_valid_match(
    query_artist: str, query_track: str, candidate_artist: str, candidate_track: str
) -> bool:
    """
    Validates that candidate search API results match query artist or track title tokens,
    preventing unrelated top search results from corrupting dataset metadata.
    """
    q_track_clean = clean_query_term(query_track).lower()
    c_track_clean = candidate_track.lower()

    # Extract non-trivial words (ignoring common stop words)
    stop_words = {"the", "a", "an", "and", "feat", "ft", "remix", "version", "edit", "live", "audio"}
    q_words = set(re.findall(r"\w+", q_track_clean)) - stop_words
    c_words = set(re.findall(r"\w+", c_track_clean)) - stop_words

    if not q_words:
        return True

    # Check for word overlap between target track title and candidate track title
    if q_words & c_words:
        return True

    # Fallback: check if artist match is strong
    q_artist_clean = clean_query_term(query_artist).lower()
    c_artist_clean = candidate_artist.lower()
    q_art_words = set(re.findall(r"\w+", q_artist_clean)) - stop_words
    c_art_words = set(re.findall(r"\w+", c_artist_clean)) - stop_words

    return bool(q_art_words and q_art_words & c_art_words)


def make_api_request(url: str, timeout: float = 2.5, max_retries: int = 1) -> dict | None:
    """
    Makes an HTTP GET request with retry backoff and handles API quota errors.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        },
    )

    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # Detect Deezer rate limit error JSON response
                if isinstance(data, dict) and "error" in data:
                    err = data.get("error", {})
                    if isinstance(err, dict) and err.get("code") in (4, 429):
                        time.sleep(0.2 * (attempt + 1))
                        continue
                return data
        except Exception:  # noqa: BLE001
            if attempt < max_retries:
                time.sleep(0.15 * (attempt + 1))

    return None



def get_deezer_album_genre(album_id: int) -> str:
    """
    Queries Deezer album metadata with thread-safe caching to avoid N+1 duplicate HTTP calls.
    """
    with ALBUM_CACHE_LOCK:
        if album_id in ALBUM_GENRE_CACHE:
            return ALBUM_GENRE_CACHE[album_id]

    url = f"https://api.deezer.com/album/{album_id}"
    data = make_api_request(url, timeout=3.0, max_retries=1)

    genre_name = ""
    if data and isinstance(data, dict):
        genres = data.get("genres", {}).get("data", [])
        if genres:
            genre_name = genres[0].get("name", "")

    with ALBUM_CACHE_LOCK:
        ALBUM_GENRE_CACHE[album_id] = genre_name

    return genre_name


def query_deezer_api(artist: str, track_name: str) -> dict[str, str] | None:
    """
    Queries Deezer API for authoritative metadata, genres, preview MP3 URLs, and cover art.
    """
    clean_artist = clean_query_term(artist)
    clean_track = clean_query_term(track_name)

    if not clean_track:
        return None

    query = f"{clean_artist} {clean_track}".strip()
    url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}"

    data = make_api_request(url, timeout=4.0, max_retries=2)
    if not data or not isinstance(data, dict):
        return None

    items = data.get("data", [])
    if not items:
        return None

    # Check top candidate match
    item = items[0]
    cand_artist = item.get("artist", {}).get("name", "")
    cand_track = item.get("title", "")

    if not is_valid_match(artist, track_name, cand_artist, cand_track):
        return None

    preview_url = item.get("preview", "")
    artwork_url = item.get("album", {}).get("cover_medium", "")

    genre_name = ""
    album_id = item.get("album", {}).get("id")
    if album_id:
        genre_name = get_deezer_album_genre(album_id)

    return {
        "itunes_genre": genre_name,
        "preview_url": preview_url,
        "artwork_url": artwork_url,
        "itunes_artist": cand_artist or artist,
        "itunes_track_name": cand_track or track_name,
        "status": "success",
    }


def query_itunes_api(artist: str, track_name: str) -> dict[str, str] | None:
    """
    Fallback query to iTunes Search API.
    """
    clean_artist = clean_query_term(artist)
    clean_track = clean_query_term(track_name)

    if not clean_track:
        return None

    query = f"{clean_artist} {clean_track}".strip()
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"

    data = make_api_request(url, timeout=4.0, max_retries=2)
    if not data or not isinstance(data, dict):
        return None

    results = data.get("results", [])
    if not results:
        return None

    item = results[0]
    cand_artist = item.get("artistName", "")
    cand_track = item.get("trackName", "")

    if not is_valid_match(artist, track_name, cand_artist, cand_track):
        return None

    artwork = (item.get("artworkUrl100") or "").replace("100x100bb", "600x600bb")

    return {
        "itunes_genre": item.get("primaryGenreName", ""),
        "preview_url": item.get("previewUrl", ""),
        "artwork_url": artwork,
        "itunes_artist": cand_artist,
        "itunes_track_name": cand_track,
        "status": "success",
    }


def query_music_api(artist: str, track_name: str) -> dict[str, str] | None:
    """
    Combined query: tries iTunes API first for authoritative primary genre and non-expiring preview URLs,
    then uses Deezer API as fallback.
    """
    res_itunes = query_itunes_api(artist, track_name)
    if res_itunes and res_itunes.get("itunes_genre") and res_itunes.get("preview_url"):
        return res_itunes

    res_deezer = query_deezer_api(artist, track_name)
    if res_deezer:
        if res_itunes:
            if not res_deezer.get("itunes_genre") and res_itunes.get("itunes_genre"):
                res_deezer["itunes_genre"] = res_itunes["itunes_genre"]
            if not res_deezer.get("preview_url") and res_itunes.get("preview_url"):
                res_deezer["preview_url"] = res_itunes["preview_url"]
        return res_deezer

    return res_itunes or res_deezer


def load_cache(cache_path: str = CACHE_JSON_PATH) -> dict[str, dict[str, str]]:
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001, S110
            pass
    return {}


def save_cache(cache: dict[str, dict[str, str]], cache_path: str = CACHE_JSON_PATH) -> None:
    tmp_path = cache_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, cache_path)


def enrich_dataset(
    max_workers: int = 25,
    batch_size: int = 500,
    limit_tracks: int | None = None,
    force_rebuild: bool = False,
    retry_missing: bool = False,
    input_path: str = INPUT_CSV_PATH,
    output_path: str = OUTPUT_CSV_PATH,
    cache_path: str = CACHE_JSON_PATH,
):

    console.print(
        Panel.fit(
            "[bold cyan]AudioGraph-AI API Dataset Enrichment & Genre Swapper[/bold cyan]\n"
            "[dim]Parallel Metadata Extractor (Deezer + iTunes APIs)[/dim]",
            border_style="cyan",
        )
    )

    # 1. Load CSV
    console.print(f"[bold yellow][*][/bold yellow] Loading dataset CSV from '[bold]{input_path}[/bold]'...")
    df = pd.read_csv(input_path)
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    df = (
        df.dropna(subset=["track_id", "track_name", "artists"])
        .drop_duplicates(subset=["track_id"])
        .reset_index(drop=True)
    )

    if limit_tracks:
        console.print(
            f"[bold yellow][*][/bold yellow] Limiting processing to first [bold]{limit_tracks}[/bold] tracks..."
        )
        df = df.iloc[:limit_tracks].copy()

    total_tracks = len(df)
    console.print(f"[bold green][+][/bold green] Dataset loaded: [bold green]{total_tracks:,}[/bold green] tracks.\n")

    # 2. Load existing cache
    cache = {} if force_rebuild else load_cache(cache_path)
    console.print(
        f"[bold yellow][*][/bold yellow] Persistent cache status: [bold cyan]{len(cache):,}[/bold cyan] / [bold]{total_tracks:,}[/bold] tracks present in cache."
    )

    # Determine uncached tracks
    uncached_indices = []
    for idx, row in df.iterrows():
        tid = str(row["track_id"])
        if force_rebuild or tid not in cache or (retry_missing and not cache[tid].get("preview_url") and not cache[tid].get("itunes_genre")):
            uncached_indices.append(idx)

    console.print(f"[bold yellow][*][/bold yellow] Tracks remaining to enrich: [bold magenta]{len(uncached_indices):,}[/bold magenta]\n")

    if uncached_indices:
        console.print(f"[bold yellow][*][/bold yellow] Starting parallel API enrichment ([bold cyan]{max_workers}[/bold cyan] worker threads)...")
        start_time = time.time()

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}[/bold cyan]"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            TextColumn("[dim]•[/dim]"),
            TextColumn("[bold green]{task.fields[rate]:.1f} trk/s[/bold green]"),
            console=console,
            transient=False,
        )

        with progress:
            task_id = progress.add_task(
                "Enriching Tracks",
                total=len(uncached_indices),
                rate=0.0,
            )

            processed_count = 0
            matches_found = 0

            for batch_start in range(0, len(uncached_indices), batch_size):
                batch_idx = uncached_indices[batch_start : batch_start + batch_size]

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=max_workers
                ) as executor:
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
                                "itunes_artist": "",
                                "itunes_track_name": "",
                                "status": "not_found",
                            }
                        processed_count += 1
                        elapsed = time.time() - start_time
                        current_rate = processed_count / (elapsed if elapsed > 0 else 1.0)
                        progress.update(task_id, advance=1, rate=current_rate)

                save_cache(cache, cache_path)
                elapsed = time.time() - start_time
                rate = processed_count / (elapsed if elapsed > 0 else 1.0)
                overall_progress = len(cache) / total_tracks * 100.0

                console.print(
                    f"    [bold cyan]-> Enriched {len(cache):,}/{total_tracks:,} ({overall_progress:.1f}%) | "
                    f"Processed: {processed_count:,}/{len(uncached_indices):,} | "
                    f"Velocity: [bold green]{rate:.1f} musics/sec[/bold green][/bold cyan]"
                )

        console.print(
            f"\n[bold green][+][/bold green] API enrichment complete in [bold cyan]{time.time() - start_time:.1f}[/bold cyan] seconds!\n"
        )


    # 4. Map enriched metadata back to DataFrame
    console.print("[bold yellow][*][/bold yellow] Swapping dataset genres and attaching preview MP3 & cover art URLs...")

    # Build primary artist dominant real-world genre map across cache
    artist_genres: dict[str, list[str]] = {}
    for idx, row in df.iterrows():
        tid = str(row["track_id"])
        info = cache.get(tid, {})
        g = info.get("itunes_genre", "").strip()
        if g:
            artists_str = str(row["artists"])
            for a in artists_str.split(";"):
                a_clean = a.strip()
                if a_clean:
                    artist_genres.setdefault(a_clean, []).append(g)

    artist_dominant_genre: dict[str, str] = {}
    for a, g_list in artist_genres.items():
        if g_list:
            from collections import Counter
            artist_dominant_genre[a] = Counter(g_list).most_common(1)[0][0]

    itunes_genres = []
    preview_urls = []
    artwork_urls = []

    swapped_count = 0
    propagated_count = 0
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
            # Try artist dominant real-world genre propagation
            primary_art = str(row["artists"]).split(";")[0].strip()
            inferred_g = artist_dominant_genre.get(primary_art)
            if inferred_g:
                itunes_genres.append(inferred_g)
                propagated_count += 1
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
    console.print(f"[bold yellow][*][/bold yellow] Saving enriched dataset to '[bold]{output_path}[/bold]'...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    valid_previews = sum(1 for u in preview_urls if u)
    valid_artworks = sum(1 for a in artwork_urls if a)

    # Render Rich Summary Table
    table = Table(title="AudioGraph-AI Enrichment & Genre Swapping Summary", title_style="bold green", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="bold white")
    table.add_column("Percentage", justify="right", style="bold yellow")

    table.add_row("Total Tracks Processed", f"{total_tracks:,}", "100.0%")
    table.add_row("Swapped API Genres", f"{swapped_count:,}", f"{swapped_count / total_tracks * 100.0:.1f}%")
    table.add_row("Inferred Artist Genres", f"{propagated_count:,}", f"{propagated_count / total_tracks * 100.0:.1f}%")
    table.add_row("Fallback Kaggle Genres", f"{fallback_count:,}", f"{fallback_count / total_tracks * 100.0:.1f}%")
    table.add_row("Audio Preview URLs", f"{valid_previews:,}", f"{valid_previews / total_tracks * 100.0:.1f}%")
    table.add_row("Album Cover Art URLs", f"{valid_artworks:,}", f"{valid_artworks / total_tracks * 100.0:.1f}%")

    console.print()
    console.print(table)
    console.print(f"\n[bold green][✓] Output Dataset Saved:[/bold green] [bold white]{output_path}[/bold white]\n")



def parse_args():
    parser = argparse.ArgumentParser(
        description="AudioGraph-AI API Dataset Enrichment & Genre Swapper"
    )
    parser.add_argument(
        "-n", "--limit", type=int, default=None, help="Limit processing to N tracks."
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=25, help="Number of worker threads (default: 25)."
    )
    parser.add_argument(
        "-b", "--batch-size", type=int, default=500, help="Batch size for progress saving (default: 500)."
    )


    parser.add_argument(
        "--force", action="store_true", help="Force re-query API for all tracks, ignoring cache."
    )
    parser.add_argument(
        "--retry-missing", action="store_true", help="Re-query API only for tracks missing preview URL/genre in cache."
    )
    parser.add_argument(
        "--input", type=str, default=INPUT_CSV_PATH, help=f"Input dataset CSV path (default: {INPUT_CSV_PATH})."
    )
    parser.add_argument(
        "--output", type=str, default=OUTPUT_CSV_PATH, help=f"Output enriched CSV path (default: {OUTPUT_CSV_PATH})."
    )
    parser.add_argument(
        "--cache", type=str, default=CACHE_JSON_PATH, help=f"Cache JSON path (default: {CACHE_JSON_PATH})."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    enrich_dataset(
        max_workers=args.workers,
        batch_size=args.batch_size,
        limit_tracks=args.limit,
        force_rebuild=args.force,
        retry_missing=args.retry_missing,
        input_path=args.input,
        output_path=args.output,
        cache_path=args.cache,
    )
