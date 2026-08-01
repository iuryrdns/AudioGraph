# AudioGraph-AI: Graph Engine & Modelling Specification

This document defines the mathematical, structural, and technical specification for constructing and serving the music recommendation graph in AudioGraph-AI via the high-performance `GraphEngine` class (`src/graph/engine.py` and `src/graph/builder.py`).

---

## 1. System Architecture & Topology

AudioGraph-AI utilizes a **Directed Dual-Layer Heterogeneous Network** served through the **`GraphEngine`** API wrapper. The underlying data model separates categorical metadata from continuous acoustic similarity while presenting a clean, developer-friendly interface.

```
                         DEVELOPER-FACING API INTERFACE (GraphEngine)
   ┌────────────────────────────────────────────────────────────────────────┐
   │ graph[track_id]              len(graph)          track_id in graph     │
   │ graph.get_neighbors(id)      graph.nodes[id]     graph.has_edge(u, v)  │
   │ graph.get_metadata(id)       graph.get_2hop_metadata_candidates(id)   │
   └───────────────────────────────────┬────────────────────────────────────┘
                                       │
                         ZERO-OVERHEAD BRIDGE LAYER
   ┌───────────────────────────────────▼────────────────────────────────────┐
   │ _id_to_idx: dict[str, int32]  ──► Fast string to int index mapping    │
   │ _idx_to_id: np.ndarray        ──► Fast int to string ID lookup         │
   └───────────────────────────────────┬────────────────────────────────────┘
                                       │
                      HIGH-PERFORMANCE DATA BACKEND
  ┌────────────────────────────────────┼────────────────────────────────────┐
  │ 1. Layer 2: Audio Similarity CSR   │ 2. Layer 1: Categorical Metadata   │
  │    - SciPy csr_matrix (float32)    │    - Fast inverted index maps      │
  │    - O(1) row slice per 1-hop      │    - Continuous audio feature array│
  └────────────────────────────────────┴────────────────────────────────────┘
```

---

## 2. Layer 1: Categorical Metadata Layer

### 2.1 Node Specification
* **`Track` Nodes**:
  * Identifier: `track_id` (e.g. `1Gvb2qDyodCVORCiSvFXkD`)
  * Node Attributes: `type="track"`, `name`, `popularity`, `duration_ms`, `explicit`
* **`Artist` Entities**:
  * Identifier: `artist_<ArtistName>` (e.g. `artist_YUNGBLUD`)
  * Multi-artist strings (e.g. `"YUNGBLUD;Charlotte Lawrence"`) are parsed and split on `;` so tracks link to each artist individually.
* **`Genre` Entities**:
  * Identifier: `genre_<GenreName>` (e.g. `genre_pop`)
* **`Album` Entities**:
  * Identifier: `album_<ArtistName>_<AlbumName>` (scoped by primary artist to prevent title collisions across artists).

### 2.2 Metadata Edge Relationships
Metadata connections are represented internally as inverted index maps and sparse bipartite boolean matrices to enable microsecond 2-hop traversals:
* `Track ──[BY_ARTIST]──► Artist` and `Artist ──[HAS_TRACK]──► Track`
* `Track ──[IN_GENRE]──► Genre` and `Genre ──[HAS_TRACK]──► Track`
* `Track ──[IN_ALBUM]──► Album` and `Album ──[HAS_TRACK]──► Track`

---

## 3. Layer 2: Audio Similarity Layer

### 3.1 Feature Vector & Preprocessing
Continuous audio features are extracted into a matrix $X \in \mathbb{R}^{N \times F}$:
* **Features**: `danceability`, `energy`, `valence`, `tempo`, `acousticness`, `instrumentalness`, `speechiness`, `loudness`, `liveness`, `duration_ms`, `popularity`.
* **Normalization**: All features undergo `StandardScaler` normalization (zero mean, unit variance) so metric scales do not distort similarity distance.

### 3.2 Feature Weight Assignment ($W_{\text{feat}}$)
Features are weighted by domain importance using a feature weight vector $W_{\text{feat}} \in \mathbb{R}^{F}$:

```python
DEFAULT_FEATURE_WEIGHTS = {
    # High Importance (Vibe, Rhythm & Mood)
    "danceability": 1.5,
    "energy": 1.5,
    "valence": 1.3,        # Positivity / Mood
    "tempo": 1.2,
    
    # Moderate Importance (Timbre & Texture)
    "acousticness": 1.0,
    "instrumentalness": 1.0,
    "speechiness": 0.8,
    
    # Low Importance (Production / Secondary Attributes)
    "loudness": 0.5,
    "liveness": 0.4,
    "duration_ms": 0.2,
    "popularity": 0.3
}
```

### 3.3 Weighted Cosine Similarity & Chunked Matrix Calculation
The weighted feature matrix $X_W$ is computed by scaling feature columns by $\sqrt{W_{\text{feat}}}$:

$$X_W = X_{\text{normalized}} \odot \sqrt{W_{\text{feat}}}$$

To compute true weighted cosine similarity (in $[-1.0, +1.0]$), each row vector of $X_W$ is row-$L_2$ normalized prior to matrix multiplication:

$$\hat{X}_W = \text{diag}(\|\mathbf{x}_{W, i}\|_2)^{-1} X_W$$

Pairwise similarity is computed in **chunks / batches** (batch size = 1,000 tracks):
* For each batch $\hat{X}_{\text{batch}} \in \mathbb{R}^{1000 \times F}$, similarity against all $N$ tracks is computed via vectorized BLAS matrix multiplication:
  $$S_{\text{batch}} = \hat{X}_{\text{batch}} \cdot \hat{X}_W^T$$
* Peak temporary construction memory stays under **~456 MB RAM** (using `float32`), completing similarity matrix calculation in ~2–3 seconds across 114,000 tracks.

### 3.4 Data Deduplication
In `loader.py`, duplicate tracks sharing identical `(artist, track_name)` pairs or identical feature vectors are merged during data ingestion to prevent recommendation loops across duplicate remastered/compilation album entries.

### 3.5 Dual-Pruning & SciPy CSR Memory Footprint

To eliminate low-similarity noise and enforce a low memory footprint, edges undergo a 2-stage pruning process:
1. **Threshold Pruning ($\ge 0.3$)**:
   A directed similarity edge `(Track i -> Track j)` is created **only if** $S_{i, j} \ge 0.3$.
2. **Top-K Directed Degree Capping ($k \le 300$)**:
   For each track, up to its top $k = 300$ strongest outgoing similarity neighbors are retained.

#### Memory Performance Breakdown ($N = 114,000$, $M = 34,200,000$ edges):
The similarity graph is stored as a SciPy Compressed Sparse Row matrix (`csr_matrix`) with `float32` values and `int32` indices:
* `data` array (`float32`): $34.2\text{M} \times 4\text{ B} = \mathbf{136.80 \text{ MB}}$
* `indices` array (`int32`): $34.2\text{M} \times 4\text{ B} = \mathbf{136.80 \text{ MB}}$
* `indptr` array (`int32`): $114,001 \times 4\text{ B} = \mathbf{0.46 \text{ MB}}$
* **Layer 2 CSR Footprint**: **274.06 MB**
* **Layer 1 Metadata Footprint**: **~5.20 MB**
* **Total `GraphEngine` RAM Usage**: **~279.26 MB RAM** (a **98.0% memory reduction** compared to baseline NetworkX dictionary objects).


---

## 4. `GraphEngine` Developer API Specification

The `GraphEngine` class (`src/graph/engine.py`) encapsulates the high-performance SciPy/NumPy backend while providing a clean, Pythonic interface:

### 4.1 Core API Methods
```python
# Query 1-hop similarity neighbors
neighbors = graph.get_neighbors(track_id)  # Returns list[tuple[neighbor_id, weight]]

# Query track metadata
metadata = graph.get_metadata(track_id)    # Returns dict of metadata & audio features

# Query 2-hop metadata candidates
candidates = graph.get_2hop_metadata_candidates(track_id)  # Returns list[candidate_id]

# Query edge existence & weight
has_edge = graph.has_edge(u, v)             # Returns bool
weight = graph.get_edge_weight(u, v)        # Returns float
```

### 4.2 NetworkX Duck-Typing Support
To allow existing NetworkX-compatible recommendation algorithms to run without code modification, `GraphEngine` supports standard NetworkX access patterns:
* `graph[track_id]`: Returns neighbor dict `{'nbr_id': {'weight': float}}`.
* `graph.nodes[track_id]`: Returns node attribute dictionary.
* `track_id in graph`: Checks track existence in $O(1)$ time.
* `len(graph)`: Returns total track count $N$.

---

## 5. Serialization & Persistence Format

* **Primary High-Performance Format**: Python `Pickle` (`.pkl`) format or SciPy sparse NPZ format (`scipy.sparse.save_npz`) for zero-copy binary serialization and instant reload speeds.
* **Secondary Export Format**: GraphML (`.graphml`) export adapter for external network visualization tools like Gephi.
