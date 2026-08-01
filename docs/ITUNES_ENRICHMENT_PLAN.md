# Implementation Plan: iTunes API Dataset Enrichment & Frontend Preparation

**Document Path**: [`docs/ITUNES_ENRICHMENT_PLAN.md`](file:///home/adley/repos/university/AudioGraph-AI/docs/ITUNES_ENRICHMENT_PLAN.md)  
**Target Goal**: Enrich dataset tracks with 30-second audio preview URLs (`previewUrl`), high-res album cover art (`artworkUrl100`), and authoritative real-world primary genres (`primaryGenreName`) for web UI integration.  
**Status**: Proposed / Approved  

---

## 1. Executive Summary & Value Proposition

Integrating the **iTunes Search API** provides three major features for AudioGraph-AI:

1. **30-Second Audio Previews (`previewUrl`)**: Enables interactive audio playback in the web frontend using HTML5 `<audio>` players.
2. **Album Cover Art (`artworkUrl100`)**: Renders rich visual album cards in modern dark-mode web UIs.
3. **Authoritative Real-World Genres (`primaryGenreName`)**: Resolves Kaggle dataset misclassifications (e.g. correcting Emo Rap from `sad` to `Hip-Hop/Rap`), dramatically improving Super-Genre taxonomy clustering.

---

## 2. Technical Architecture & Data Flow

```
   ┌──────────────────────┐
   │ Spotify CSV Dataset  │
   │ (80,749 tracks)      │
   └──────────┬───────────┘
              │
              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ Batch Enrichment Script (scripts/enrich_dataset_itunes.py)  │
   │  - Parallel worker threads with rate-limiting & retries    │
   │  - Auto-resumable local cache (data/itunes_cache.json)      │
   └──────────┬──────────────────────────────────────────────────┘
              │
              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ Enriched DataLoader (src/graph/loader.py)                    │
   │  - Overrides dataset genre with iTunes primaryGenreName     │
   │  - Attaches preview_url & artwork_url to track_metadata     │
   └──────────┬──────────────────────────────────────────────────┘
              │
              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ Web API Server (FastAPI / Flask) & Modern Web UI            │
   │  - Interactive audio player for 30s previews                │
   │  - Album cover art cards & genre badges                     │
   └─────────────────────────────────────────────────────────────┘
```

---

## 3. Data Schema Extension

Track metadata dictionaries will be extended with iTunes metadata attributes:

```json
{
  "track_id": "5SuOikwiRyPMVoIQDJUgSV",
  "track_name": "Comedy",
  "primary_artist": "Gen Hoshino",
  "track_genre": "J-Pop",                      // Real-World iTunes Genre
  "super_genre": "POP",                        // Aligned Super-Genre Family
  "preview_url": "https://audio-ssl.itunes.apple.com/.../preview.m4a",
  "artwork_url": "https://is1-ssl.mzstatic.com/.../100x100bb.jpg",
  "danceability": 0.676,
  "energy": 0.461,
  "valence": 0.715
}
```

---

## 4. Implementation Roadmap

### Phase 1: Persistent Cache Layer & Scraper (`scripts/enrich_dataset_itunes.py`)
* Multi-threaded concurrent worker pool (`concurrent.futures.ThreadPoolExecutor`).
* Local JSON/SQLite storage (`data/itunes_cache.json`).
* Incremental progress tracking: checks if `track_id` is already cached; skips network request if present.
* Exponential backoff retry handling for HTTP rate limits.

### Phase 2: DataLoader Integration ([`src/graph/loader.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/loader.py))
* `load_and_preprocess_dataset()` loads `data/itunes_cache.json` (if available).
* Replaces dataset genre tags with authoritative iTunes `primaryGenreName`.
* Attaches `preview_url` and `artwork_url` to `track_metadata`.
* On-demand fallback: if a recommended track is not in `itunes_cache.json`, fetches iTunes metadata dynamically in ~0.2s.

### Phase 3: REST API Server (`src/api/server.py`)
* Lightweight FastAPI or Flask backend server.
* Endpoints:
  - `GET /api/tracks/search?q=...`: Search tracks by title/artist.
  - `GET /api/recommend?seed_id=...&count=10`: Returns recommendation stream JSON payload with preview URLs, artwork, and explanation strings.

### Phase 4: Modern Web UI Frontend
* Responsive modern web interface (HTML5 + Vanilla CSS/JS or Vite/React).
* Floating audio preview player bar with play/pause controls.
* Visual graph network visualization of 1-hop and 2-hop recommendation paths.

---

## 5. Performance & Strategy Breakdown

| Aspect | Strategy |
| :--- | :--- |
| **Dataset Scale** | 80,749 tracks |
| **Enrichment Rate** | ~10-15 requests/second via multi-threaded worker pool |
| **Estimated Batch Duration** | ~1.5 hours for full dataset; **10 minutes for top 10,000 popular tracks** |
| **On-Demand Fallback** | Instant (~0.2s) for any uncached track during live recommendation query |

---

## 6. Recommended Next Steps

1. Create [`scripts/enrich_dataset_itunes.py`](file:///home/adley/repos/university/AudioGraph-AI/scripts/enrich_dataset_itunes.py) to enrich the top 10,000 most popular tracks first for rapid testing.
2. Update [`src/graph/loader.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/loader.py) to consume the enriched cache.
3. Build a lightweight REST API server in Python to serve recommendation payloads to your frontend.
