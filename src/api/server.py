"""
FastAPI Server for AudioGraph-AI Graph Engine.
Exposes REST API endpoints for Python-based music recommendation and graph search.
"""

import os
import urllib.parse
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.graph.builder import get_or_build_graph
from src.graph.engine import GraphEngine
from src.graph.recommender import AdaptiveRadioRecommender

ENRICHED_DATASET_PATH = os.path.join("data", "spotify_tracks_dataset_itunes.csv")
RAW_DATASET_PATH = os.path.join("data", "spotify_tracks_dataset.csv")
DEFAULT_DATASET_PATH = (
    ENRICHED_DATASET_PATH if os.path.exists(ENRICHED_DATASET_PATH) else RAW_DATASET_PATH
)
DEFAULT_CACHE_PATH = os.path.join("data", "spotify_graph_cache.pkl")

# Real-audio (librosa) engine: output of `python -m scripts.extract_features`.
# Optional — only built if the CSV has actually been generated.
AUDIO_DATASET_PATH = os.path.join("data", "features_audio.csv")
AUDIO_CACHE_PATH = os.path.join("data", "audio_graph_cache.pkl")

# Global GraphEngine references, one per feature source
graph_engine: Optional[GraphEngine] = None
audio_graph_engine: Optional[GraphEngine] = None

ENGINES: dict[str, str] = {"spotify": "graph_engine", "audio": "audio_graph_engine"}


def _get_engine(name: str) -> Optional[GraphEngine]:
    if name not in ENGINES:
        raise HTTPException(status_code=400, detail=f"Unknown engine '{name}'. Use one of {list(ENGINES)}.")
    return graph_engine if name == "spotify" else audio_graph_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph_engine, audio_graph_engine
    print(f"[*] Starting AudioGraph-AI Python Server...")
    print(f"[*] Loading GraphEngine (Dataset: '{DEFAULT_DATASET_PATH}', Cache: '{DEFAULT_CACHE_PATH}')...")
    graph_engine = get_or_build_graph(
        csv_path=DEFAULT_DATASET_PATH,
        cache_path=DEFAULT_CACHE_PATH,
        force_rebuild=False,
        threshold=0.3,
        top_k=300,
        source="spotify",
    )
    print(f"[+] GraphEngine loaded successfully with {len(graph_engine)} tracks.")

    if os.path.exists(AUDIO_DATASET_PATH):
        print(f"[*] Loading real-audio GraphEngine (Dataset: '{AUDIO_DATASET_PATH}')...")
        from src.config import DEFAULT_AUDIO_FEATURE_WEIGHTS
        audio_graph_engine = get_or_build_graph(
            csv_path=AUDIO_DATASET_PATH,
            cache_path=AUDIO_CACHE_PATH,
            force_rebuild=False,
            threshold=0.3,
            top_k=300,
            source="audio",
            feature_weights=DEFAULT_AUDIO_FEATURE_WEIGHTS,
        )
        print(f"[+] Real-audio GraphEngine loaded successfully with {len(audio_graph_engine)} tracks.")
    else:
        print(
            f"[i] '{AUDIO_DATASET_PATH}' not found — audio engine disabled. "
            f"Run scripts/extract_features.py to generate it."
        )
    yield
    print("[*] Shutting down AudioGraph-AI Python Server...")


app = FastAPI(
    title="AudioGraph-AI Engine API",
    description="Python Graph Recommender API for AudioGraph-AI web client.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=4096)
def fetch_itunes_preview(track_name: str, artist_name: str) -> dict[str, str]:
    """Fallback utility to fetch previewUrl and high-res artwork from iTunes API if missing."""
    try:
        query = f"{track_name} {artist_name}"
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                r = results[0]
                artwork = (r.get("artworkUrl100") or "").replace("100x100bb", "300x300bb")
                return {
                    "previewUrl": r.get("previewUrl", ""),
                    "artwork": artwork,
                    "artistId": str(r.get("artistId", "0")),
                }
    except Exception:
        pass
    return {"previewUrl": "", "artwork": "/placeholder.svg", "artistId": "0"}


def _safe_str(val: Any) -> str:
    """Safely convert metadata values (handling NaN, None, float, int) to clean strings."""
    if val is None:
        return ""
    if isinstance(val, float) and (val != val or str(val).lower() == "nan"):
        return ""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


def is_invalid_or_expired_preview(url: str) -> bool:
    """Check if a preview URL is missing, invalid, or an expired Deezer CDN URL."""
    if not url or not isinstance(url, str):
        return True
    if "dzcdn.net" in url or "deezer.com" in url:
        return True  # Deezer URLs in dataset have expired Akamai tokens
    return False


def enrich_tracks_parallel(tracks: list[dict]) -> None:
    """Enrich missing or expired preview URLs and artwork in parallel using a thread pool."""
    tracks_to_enrich = [
        t for t in tracks
        if is_invalid_or_expired_preview(t.get("previewUrl", "")) or t.get("artwork") == "/placeholder.svg"
    ]
    if not tracks_to_enrich:
        return

    def _enrich(track: dict):
        enriched = fetch_itunes_preview(track["name"], track["artist"])
        if is_invalid_or_expired_preview(track.get("previewUrl", "")) and enriched["previewUrl"]:
            track["previewUrl"] = enriched["previewUrl"]
        if track.get("artwork") == "/placeholder.svg" and enriched["artwork"]:
            track["artwork"] = enriched["artwork"]

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(_enrich, tracks_to_enrich))


class SeedTrack(BaseModel):
    trackId: Optional[Any] = None
    name: Optional[str] = None
    artist: Optional[str] = None
    artistId: Optional[Any] = None
    genre: Optional[str] = None


class FeedbackData(BaseModel):
    likedArtists: list[str] = Field(default_factory=list)
    likedGenres: list[str] = Field(default_factory=list)
    dislikedArtists: list[str] = Field(default_factory=list)
    dislikedGenres: list[str] = Field(default_factory=list)


class RecommendRequest(BaseModel):
    seed: Optional[SeedTrack] = None
    seed_id: Optional[str] = None
    feedback: Optional[FeedbackData] = None
    exclude: list[Any] = Field(default_factory=list)
    count: int = 4
    source: str = "spotify"


@app.get("/health")
@app.get("/api/py/health")
def health_check():
    loaded = graph_engine is not None
    return {
        "status": "online" if loaded else "initializing",
        "engine": "Python Graph Matrix",
        "total_tracks": len(graph_engine) if graph_engine else 0,
        "audio_engine": {
            "available": audio_graph_engine is not None,
            "total_tracks": len(audio_graph_engine) if audio_graph_engine else 0,
        },
    }


@app.get("/api/py/search")
def search_tracks(q: str = Query(..., min_length=1), limit: int = 20, source: str = "spotify"):
    active_engine = _get_engine(source)
    if not active_engine:
        raise HTTPException(
            status_code=503,
            detail=f"'{source}' engine is initializing or unavailable (run scripts/extract_features.py for 'audio').",
        )

    query = q.lower().strip()
    matches = []

    for idx, track_id in enumerate(active_engine.idx_to_id):
        meta = active_engine.get_metadata(str(track_id))
        track_name = _safe_str(meta.get("track_name"))
        artist_name = _safe_str(meta.get("primary_artist") or meta.get("artists"))
        genre = _safe_str(meta.get("track_genre"))

        if query in track_name.lower() or query in artist_name.lower() or query in genre.lower():
            raw_artwork = _safe_str(meta.get("artwork_url") or meta.get("artwork"))
            artwork = raw_artwork.replace("100x100bb", "300x300bb") if raw_artwork else ""
            preview_url = _safe_str(meta.get("preview_url") or meta.get("previewUrl"))

            matches.append({
                "trackId": str(track_id),
                "name": track_name or "Unknown Track",
                "artist": artist_name or "Unknown Artist",
                "artistId": _safe_str(meta.get("artist_id")) or "0",
                "genre": genre or "Unknown",
                "artwork": artwork or "/placeholder.svg",
                "previewUrl": preview_url,
                "album": _safe_str(meta.get("album_name")),
                "year": _safe_str(meta.get("year")),
            })
            if len(matches) >= limit:
                break

    enrich_tracks_parallel(matches)
    return {"results": matches}


@app.post("/api/py/recommend")
def recommend_tracks(req: RecommendRequest):
    active_engine = _get_engine(req.source)
    if not active_engine:
        raise HTTPException(
            status_code=503,
            detail=f"'{req.source}' engine is initializing or unavailable (run scripts/extract_features.py for 'audio').",
        )

    # 1. Resolve Seed Track ID
    seed_id: Optional[str] = None
    if req.seed_id and str(req.seed_id) in active_engine:
        seed_id = str(req.seed_id)
    elif req.seed and req.seed.trackId and str(req.seed.trackId) in active_engine:
        seed_id = str(req.seed.trackId)
    elif req.seed and req.seed.name:
        # Search graph for closest track match
        target_name = req.seed.name.lower().strip()
        target_artist = (req.seed.artist or "").lower().strip()
        for tid in active_engine.idx_to_id:
            meta = active_engine.get_metadata(str(tid))
            t_name = _safe_str(meta.get("track_name")).lower().strip()
            t_artist = _safe_str(meta.get("primary_artist")).lower().strip()
            if target_name in t_name and (not target_artist or target_artist in t_artist):
                seed_id = str(tid)
                break

    if not seed_id:
        import re
        import random
        target_name = (req.seed.name if req.seed else "")
        target_artist = (req.seed.artist if req.seed else "")
        clean_target = re.sub(r"\(.*?\)|\[.*?\]", "", target_name).lower().strip() if target_name else ""
        clean_artist = target_artist.lower().strip() if target_artist else ""

        if clean_target:
            # 1st pass: match clean name and artist
            for tid in active_engine.idx_to_id:
                meta = active_engine.get_metadata(str(tid))
                t_name = re.sub(r"\(.*?\)|\[.*?\]", "", _safe_str(meta.get("track_name"))).lower().strip()
                t_artist = _safe_str(meta.get("primary_artist")).lower().strip()
                if clean_target in t_name and (not clean_artist or clean_artist in t_artist):
                    seed_id = str(tid)
                    break

        if not seed_id:
            seed_id = str(random.choice(active_engine.idx_to_id))

    # 2. Instantiate Recommender
    recommender = AdaptiveRadioRecommender(
        graph=active_engine,
        history_size=15,
        exploration_prob=0.20,
        artist_boost=1.35,
        genre_boost=1.20,
    )

    # 3. Generate Recommendations with Feedback and Exclude filtering
    count = max(1, min(req.count, 8))
    exclude_ids = [str(x) for x in req.exclude] if req.exclude else []
    feedback_dict = None
    if req.feedback:
        feedback_dict = {
            "liked_artists": req.feedback.likedArtists,
            "liked_genres": req.feedback.likedGenres,
            "disliked_artists": req.feedback.dislikedArtists,
            "disliked_genres": req.feedback.dislikedGenres,
        }

    stream = recommender.recommend_stream(
        seed_id,
        count=count,
        exclude_ids=exclude_ids,
        feedback=feedback_dict,
    )

    results = []
    for rec in stream:
        meta = rec.track_metadata
        tid = rec.recommended_track_id
        raw_artwork = _safe_str(meta.get("artwork_url") or meta.get("artwork"))
        artwork = raw_artwork.replace("100x100bb", "300x300bb") if raw_artwork else ""
        preview_url = _safe_str(meta.get("preview_url") or meta.get("previewUrl"))

        track_dict = {
            "trackId": str(tid),
            "name": _safe_str(meta.get("track_name")) or "Unknown",
            "artist": _safe_str(meta.get("primary_artist") or meta.get("artists")) or "Unknown",
            "artistId": _safe_str(meta.get("artist_id")) or "0",
            "genre": _safe_str(meta.get("track_genre")) or "Unknown",
            "artwork": artwork or "/placeholder.svg",
            "previewUrl": preview_url,
            "album": _safe_str(meta.get("album_name")),
            "year": _safe_str(meta.get("year")),
            "explanation": rec.explanation,
            "score": float(rec.score) if rec.score is not None else 0.0,
        }
        results.append(track_dict)

    # 4. Enrich missing or expired preview URLs & artwork from iTunes in parallel
    enrich_tracks_parallel(results)
    return {"results": results}


@app.get("/api/py/graph/neighbors")
def get_graph_neighbors(track_id: str = Query(...), limit: int = Query(10, ge=1, le=50), source: str = "spotify"):
    active_engine = _get_engine(source)
    if not active_engine:
        raise HTTPException(
            status_code=503,
            detail=f"'{source}' engine is initializing or unavailable (run scripts/extract_features.py for 'audio').",
        )
    if track_id not in active_engine:
        raise HTTPException(status_code=404, detail=f"Track ID '{track_id}' not found in graph engine")

    neighbors = active_engine.get_neighbors(track_id)[:limit]
    res = []
    for nid, w in neighbors:
        meta = active_engine.get_metadata(nid)
        res.append({
            "trackId": str(nid),
            "name": _safe_str(meta.get("track_name")) or "Unknown",
            "artist": _safe_str(meta.get("primary_artist") or meta.get("artists")) or "Unknown",
            "genre": _safe_str(meta.get("track_genre")) or "Unknown",
            "weight": float(w),
        })
    return {"track_id": track_id, "neighbors": res}


@app.get("/api/py/graph/stats")
def get_graph_stats(source: str = "spotify"):
    active_engine = _get_engine(source)
    if not active_engine:
        raise HTTPException(
            status_code=503,
            detail=f"'{source}' engine is initializing or unavailable (run scripts/extract_features.py for 'audio').",
        )
    return {
        "total_tracks": len(active_engine),
        "total_edges": int(active_engine.similarity_matrix.nnz),
        "genres": list(active_engine.genre_to_tracks.keys()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)