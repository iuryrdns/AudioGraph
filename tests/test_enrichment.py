"""
Unit tests for the dataset enrichment script (scripts/enrich_dataset_itunes.py).
"""

import json
import os

import pandas as pd
import pytest

from scripts.enrich_dataset_itunes import (
    clean_query_term,
    enrich_dataset,
    is_valid_match,
    load_cache,
    save_cache,
)


def test_clean_query_term_hyphenated_names():
    # Hyphenated names should be preserved
    assert clean_query_term("Jay-Z") == "Jay-Z"
    assert clean_query_term("Spider-Man") == "Spider-Man"
    assert clean_query_term("T-Pain") == "T-Pain"
    assert clean_query_term("Alt-J") == "Alt-J"
    assert clean_query_term("Post-Rock") == "Post-Rock"


def test_clean_query_term_metadata_suffixes():
    # Metadata suffixes separated by space hyphen space should be removed
    assert clean_query_term("Track Title - 2011 Remaster") == "Track Title"
    assert clean_query_term("Track Title - Live at Wembley") == "Track Title"
    assert clean_query_term("Track Title (feat. Artist)") == "Track Title"
    assert clean_query_term("Track Title [Deluxe Edition]") == "Track Title"


def test_clean_query_term_multi_artist():
    # Multi-artist strings separated by semicolon
    assert clean_query_term("Taylor Swift; Kendrick Lamar") == "Taylor Swift"


def test_is_valid_match():
    # Exact or token match should pass
    assert is_valid_match("Paramore", "Misery Business", "Paramore", "Misery Business")
    assert is_valid_match("Jay-Z", "Empire State of Mind", "Jay-Z", "Empire State of Mind (Remastered)")
    
    # Completely unrelated track should fail
    assert not is_valid_match("Katy Perry", "Firework", "Iron Maiden", "The Number of the Beast")


def test_cache_load_and_save(tmp_path):
    cache_file = os.path.join(tmp_path, "test_cache.json")
    data = {"track_123": {"itunes_genre": "Pop", "preview_url": "http://example.com/audio.mp3", "status": "success"}}
    
    save_cache(data, cache_path=cache_file)
    assert os.path.exists(cache_file)
    
    loaded = load_cache(cache_path=cache_file)
    assert loaded == data


def test_enrich_dataset_with_mock(tmp_path):
    # Create temporary input CSV
    df = pd.DataFrame([
        {"track_id": "t1", "track_name": "Jay-Z", "artists": "Jay-Z", "track_genre": "hip-hop"},
        {"track_id": "t2", "track_name": "Test Song - Live", "artists": "Test Artist", "track_genre": "rock"},
    ])
    input_csv = os.path.join(tmp_path, "input.csv")
    output_csv = os.path.join(tmp_path, "output.csv")
    cache_json = os.path.join(tmp_path, "cache.json")
    df.to_csv(input_csv, index=False)

    # Populate cache with mock result for t1 and not_found for t2
    mock_cache = {
        "t1": {
            "itunes_genre": "Hip-Hop",
            "preview_url": "http://example.com/p1.mp3",
            "artwork_url": "http://example.com/a1.jpg",
            "itunes_artist": "Jay-Z",
            "itunes_track_name": "Jay-Z",
            "status": "success",
        },
        "t2": {
            "itunes_genre": "",
            "preview_url": "",
            "artwork_url": "",
            "itunes_artist": "",
            "itunes_track_name": "",
            "status": "not_found",
        }
    }
    save_cache(mock_cache, cache_path=cache_json)

    # Run dataset enrichment (it will use existing cache and not re-fetch t2 since force_rebuild=False)
    enrich_dataset(
        max_workers=2,
        input_path=input_csv,
        output_path=output_csv,
        cache_path=cache_json,
        force_rebuild=False,
    )

    assert os.path.exists(output_csv)
    enriched_df = pd.read_csv(output_csv)
    assert "raw_dataset_genre" in enriched_df.columns
    assert "preview_url" in enriched_df.columns
    assert "artwork_url" in enriched_df.columns
    assert enriched_df.loc[enriched_df["track_id"] == "t1", "track_genre"].values[0] == "Hip-Hop"
    assert enriched_df.loc[enriched_df["track_id"] == "t2", "track_genre"].values[0] == "rock"  # fallback
