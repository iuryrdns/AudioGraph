# AudioGraph-AI: Parameter Tuning & Evaluation Guide

This guide details how to iteratively tune the AudioGraph-AI recommendation pipeline based on manual verification, listening test evaluation, and desired playback characteristics.

---

## 1. Overview of Tunable Parameters

| Parameter | Location | Default | Primary Effect |
| :--- | :--- | :--- | :--- |
| `feature_weights` | [`src/graph/builder.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/builder.py#L20-L34) | Dict | Controls acoustic distance metric (e.g. mood vs. tempo) |
| `threshold` | [`src/graph/builder.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/builder.py#L39) | `0.3` | Controls edge strictness (higher = tighter acoustic match) |
| `top_k` | [`src/graph/builder.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/builder.py#L40) | `300` | Limits max outgoing similarity edges per track |
| `artist_boost` | [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py#L47) | `1.25` | 1-hop multiplier for same-artist tracks (+25% probability weight) |
| `genre_boost` | [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py#L49) | `1.15` | 1-hop multiplier for same-genre tracks (+15% probability weight) |
| `exploration_prob` | [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py#L45) | `0.15` | Controls frequency of multi-hop exploration (15% vs 85%) |
| `history_size` | [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py#L43) | `15` | Size of anti-repeat circular history buffer |
| `METADATA_WEIGHTS` | [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py#L14-L18) | Dict | Relative importance of shared Artist, Album, or Genre in 2-hop exploration |

> [!NOTE]
> When updating builder parameters (`feature_weights`, `threshold`, or `top_k`), pass `force_rebuild=True` to `get_or_build_graph()` or run `python main.py --rebuild` to invalidate the cached `.pkl` file and re-compute the similarity matrix.
> You can also run `python main.py --clear-cache` to delete the existing cache file from disk.
> Changing recommender runtime parameters (`artist_boost`, `genre_boost`, `exploration_prob`, `history_size`) does **not** require rebuilding the graph matrix.

---

## 2. Symptom-Driven Tuning Matrix

### Scenario A: "Recommendations ignore artist/genre context or jump genres too wildly"
* **Diagnosis**: 1-hop sampling is relying purely on raw acoustic features without metadata context.
* **Action**:
  1. Increase `artist_boost` in [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py#L47) from `1.25` to `1.40` or `1.50` to favor tracks by the same artist.
  2. Increase `genre_boost` in [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py#L49) from `1.15` to `1.30` to favor tracks within the same genre.

---

### Scenario B: "The mood or energy jumps too drastically between consecutive tracks"
* **Diagnosis**: Acoustic feature weights are not heavily penalizing tempo or energy mismatches, or the similarity threshold is too low.
* **Action**:
  1. Increase weights for `energy`, `valence`, `tempo`, and `danceability` in [`src/graph/builder.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/builder.py#L20-L34):
     ```python
     CUSTOM_FEATURE_WEIGHTS = {
         "energy": 2.0,  # Increased from 1.5
         "tempo": 1.8,  # Increased from 1.2
         "valence": 1.5,  # Increased from 1.3
         "danceability": 1.5,
         "acousticness": 1.0,
         "instrumentalness": 1.0,
         "speechiness": 0.8,
         "loudness": 0.5,
         "liveness": 0.4,
         "duration_ms": 0.1,  # Decreased to prevent duration biasing
         "popularity": 0.1,  # Decreased to prevent popularity biasing
     }
     ```
  2. Increase `threshold` from `0.3` to `0.4` or `0.45` to enforce stricter similarity requirements.

---

### Scenario C: "The radio stream feels monotonous or gets stuck in repetitive acoustic loops"
* **Diagnosis**: The recommendation walk is over-exploiting local 1-hop similarity neighbors and rarely branching out.
* **Action**:
  1. Increase `exploration_prob` in [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py#L45) from `0.15` to `0.25` or `0.30` (e.g., 30% exploration rate).
  2. Increase `history_size` from `15` to `25` or `30` to force the walk away from recent tracks.
  3. Increase `top_k` in [`src/graph/builder.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/builder.py#L40) from `50` to `300` to allow more outgoing branch options.

---

### Scenario D: "Recommendations jump to unrelated tracks or fallback mode triggers too often"
* **Diagnosis**: The similarity threshold is set too high ($S \ge 0.5$) or the graph is overly pruned, leaving tracks with 0 valid 1-hop neighbors.
* **Action**:
  1. Lower `threshold` in [`src/graph/builder.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/builder.py#L39) from `0.4` down to `0.25` or `0.20`.
  2. Increase `METADATA_WEIGHTS` in [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py#L14-L18) so 2-hop fallback paths prioritize same-artist or same-genre tracks:
     ```python
     METADATA_WEIGHTS = {
         "artist": 1.2,  # Increased from 0.8
         "album": 0.9,  # Increased from 0.7
         "genre": 0.7,  # Increased from 0.5
     }
     ```

---

## 3. Workflow for Iterative Tuning & Evaluation

To test different parameter sets cleanly in Python, write a tuning script or pass arguments to `get_or_build_graph()` and `AdaptiveRadioRecommender`:

```python
from src.graph.builder import get_or_build_graph
from src.graph.recommender import AdaptiveRadioRecommender

# 1. Define custom candidate parameters
custom_weights = {
    "energy": 2.0,
    "tempo": 1.8,
    "valence": 1.5,
    "danceability": 1.5,
    "acousticness": 1.0,
    "instrumentalness": 1.0,
    "speechiness": 0.5,
    "loudness": 0.3,
    "liveness": 0.2,
    "duration_ms": 0.05,
    "popularity": 0.05,
}

# 2. Load / rebuild graph
graph = get_or_build_graph(
    csv_path="data/spotify_tracks_dataset.csv",
    cache_path="data/tuned_graph.pkl",
    force_rebuild=True,  # Re-computes matrix with new weights
    feature_weights=custom_weights,
    threshold=0.35,  # Stricter threshold
    top_k=200,
)

# 3. Test recommender with tuned metadata boost parameters
recommender = AdaptiveRadioRecommender(
    graph=graph,
    history_size=20,
    exploration_prob=0.20,
    artist_boost=1.35,  # +35% boost for same-artist tracks
    genre_boost=1.20,  # +20% boost for same-genre tracks
)

# 4. Generate stream and manually verify vibe continuity
stream = recommender.recommend_stream(seed_track_id=graph.idx_to_id[0], count=10)
for rec in stream:
    print(
        f"{rec.recommendation_type} | {rec.track_metadata['track_name']} by {rec.track_metadata['primary_artist']} ({rec.explanation})"
    )
```
