# AudioGraph-AI: Execution Plan

## 1. System Architecture

```
src/graph/
├── loader.py        # CSV ingestion, track deduplication & feature scaling (StandardScaler)
├── builder.py       # Dual-layer matrix builder, weighted cosine sim & pruning (see GRAPH_MODELLING.md)
├── engine.py        # GraphEngine API wrapper (NetworkX duck-typing, microsecond CSR lookups)
├── recommender.py   # Adaptive Radio next-track traversal (see ALGORITHM.md)
└── persistence.py   # Pickle (.pkl) load/save & SciPy NPZ / GraphML export

data/
├── small_spotify_tracks_dataset.csv
└── spotify_tracks_dataset.csv
```

---

## 2. Core Specifications

* **Graph Topology & Matrix Building**: [`GRAPH_MODELLING.md`](file:///home/adley/repos/university/AudioGraph-AI/GRAPH_MODELLING.md)
* **Next-Track Recommendation Algorithm**: [`ALGORITHM.md`](file:///home/adley/repos/university/AudioGraph-AI/ALGORITHM.md)
* **Parameter Tuning & Evaluation Guide**: [`TUNING.md`](file:///home/adley/repos/university/AudioGraph-AI/TUNING.md)

---

## 3. Implementation Roadmap

- [x] **Phase 1: Architecture & Specifications**
  - Technical design specs (`PLAN.md`, `ALGORITHM.md`, `GRAPH_MODELLING.md`).

- [x] **Phase 2: Data Loader (`src/graph/loader.py`)**
  - Load dataset CSVs, clean missing data, parse multi-artist strings, merge duplicates, and scale audio features (`StandardScaler`).

- [x] **Phase 3: Graph Builder & Engine (`src/graph/builder.py`, `src/graph/engine.py`)**
  - Construct dual-layer SciPy CSR similarity matrix (threshold $\ge 0.3$, $k \le 300$ cap, 1,000-track batching) and wrap in high-performance `GraphEngine` API with NetworkX duck typing (~279.3 MB RAM).


- [x] **Phase 4: Recommender Engine (`src/graph/recommender.py`)**
  - Implement Adaptive Radio engine (History Buffer $N=15$, 85% 1-hop weighted sampling, 15% 2-hop metadata fallback).

- [x] **Phase 5: Persistence (`src/graph/persistence.py`)**
  - High-performance `pickle` (.pkl) / SciPy NPZ save/load and GraphML (.graphml) export adapter.

- [x] **Phase 6: Verification & Testing (`tests/`, `main.py`)**
  - Unit tests (`pytest`) and CLI demonstration in `main.py`.
