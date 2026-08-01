# Adaptive Radio: Hybrid Graph Traversal & Next-Track Recommendation Algorithm

This document details the graph traversal and recommendation strategy used by AudioGraph-AI to generate continuous, high-quality "next track" recommendations from a music dataset graph.

---

## 1. Overview & Objectives

The goal of the algorithm is to provide a seamless, non-repetitive "next song" stream starting from any seed track in the graph network. 

The algorithm balances three core principles:
1. **Immediate Acoustic Relevance**: Keeping adjacent songs musically and stylistically consistent.
2. **Infinite Continuity & Dead-End Recovery**: Ensuring the recommendation queue never halts, even when encountering isolated or niche tracks.
3. **Controlled Exploration (Vibe Drift)**: Preventing repetitive loops and allowing smooth transitions between adjacent sub-genres.

---

## 2. Graph Topology

The system operates on a **Dual-Layer Heterogeneous Graph** built using NetworkX:

* **Track Nodes**: Represent individual tracks indexed by `track_id`, containing continuous audio features (danceability, energy, valence, tempo, etc.).
* **Attribute Nodes**: Represent categorical metadata entities (`Artist`, `Genre`, `Album`).
* **Metadata Edges**: Direct structural connections linking tracks to attributes (`Track -[BY_ARTIST]-> Artist`, `Track -[IN_GENRE]-> Genre`).
* **Weighted Similarity Edges**: Direct Track-to-Track edges (`Track A -[SIMILAR_TO {weight}]-> Track B`) created when the composite audio feature correlation exceeds a pruning threshold (e.g., correlation $\ge 0.3$).

---

## 3. Algorithm Architecture

```
                    [ Current Playing Track (A) ]
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Check History Buffer    │
                    │ (Exclude last N tracks) │
                    └────────────┬────────────┘
                                 │
             ┌───────────────────┴───────────────────┐
             │                                       │
  (Default: 85% Probability)             (15% Exploration or Fallback)
             ▼                                       ▼
  ┌─────────────────────────┐             ┌─────────────────────────┐
  │  Step 1: Direct 1-Hop   │             │ Step 2: Multi-Hop       │
  │  Weighted Sampling      │             │ Fallback & Exploration  │
  └──────────┬──────────────┘             └──────────┬──────────────┘
             │                                       │
             │   ┌───────────────────────────────┐   │
             └──►│ Valid unplayed 1-hop available?│◄──┘
                 └───────────────┬───────────────┘
                                 │
                   ┌─────────────┴─────────────┐
                   │ YES                       │ NO
                   ▼                           ▼
        ┌────────────────────┐       ┌────────────────────┐
        │ Sample from 1-Hop  │       │ Execute 2-Hop      │
        │ Candidate Pool     │       │ Traversal          │
        └────────────────────┘       └─────────┬──────────┘
                                               │
                                               ▼
                                     ┌────────────────────┐
                                     │ Sample from 2-Hop  │
                                     │ Candidate Pool     │
                                     └────────────────────┘
```

---

## 4. Step-by-Step Execution Details

### Step 0: History Buffer Maintenance
To prevent repetitive back-and-forth loops (e.g., $Track A \leftrightarrow Track B$), the recommender maintains a sliding circular history queue of size $N$ (e.g., $N = 15$). Any candidate track present in this buffer is excluded from immediate selection.

---

### Step 1: Direct 1-Hop Weighted Sampling (Primary Vibe)

1. Extract all immediate neighbors connected to `Current Track (A)` via `SIMILAR_TO` edges.
2. Filter out all tracks currently present in the History Buffer.
3. Apply optional Layer 1 metadata affinity multipliers (`artist_boost`, `genre_boost`) to candidate weights:

   $$W_{\text{boosted}}(A, j) = W(A, j) \times \text{ArtistBoost}_j \times \text{GenreBoost}_j$$

4. Compute selection probabilities for each remaining neighbor $j$ using normalized correlation weights:

   $$P(Track_j) = \frac{W_{\text{boosted}}(A, j)}{\sum_{k \in \text{Neighbors}(A)} W_{\text{boosted}}(A, k)}$$

5. Select 1 track via weighted random sampling.

---

### Step 2: Multi-Hop / Attribute Fallback & Exploration

Step 2 is executed in two cases:
* **Recovery Mode**: `Current Track (A)` has 0 valid (unplayed) 1-hop neighbors.
* **Exploration Mode**: On an intentional 15% probability roll to introduce subtle playlist progression.

When invoked, the walk gathers candidate tracks two hops away ($A \to X \to C$) using two parallel paths:

#### Path A: 2-Hop Track-to-Track Similarity Path
```
[ Track A ] ─── weight W(A,B) ───► [ Track B ] ─── weight W(B,C) ───► [ Track C ]
(Current)                         (Intermediate)                      (Candidate)
```
* **Concept**: `Track C` may not meet the direct threshold with `Track A`, but is strongly related to `Track B` (which connects to `Track A`).
* **Path Score**:
  $$\text{Score}_{\text{Similarity}}(A \to C) = W(A, B) \times W(B, C)$$

#### Path B: 2-Hop Track-Attribute Metadata Path
```
                                 ┌───► [ Artist Node ] ─────► [ Track C (Same Artist) ]
[ Track A ] ─── connected ───────┼───► [ Genre Node ]  ─────► [ Track D (Same Genre)  ]
 (Current)                       └───► [ Album Node ]  ─────► [ Track E (Same Album)  ]
```
* **Concept**: Bridges through shared metadata nodes when audio feature edges are absent or exhausted.
* **Path Score**:
  $$\text{Score}_{\text{Metadata}}(A \to C) = \text{AttributeWeight} \times \text{Similarity}(A, C)$$
  *(Base Attribute Weights: Artist = $0.8$, Album = $0.7$, Genre = $0.5$)*

---

### Step 3: Candidate Aggregation & Selection

1. Aggregate candidate scores across both Path A and Path B for all 2-hop tracks.
2. Filter out tracks in the History Buffer.
3. Normalize path scores into a probability distribution:

   $$P(\text{Candidate}_m) = \frac{\text{Score}(A \to m)}{\sum_{k} \text{Score}(A \to k)}$$

4. Draw 1 track using this weighted probability distribution.

---

## 5. Summary of Advantages

* **No Dead Ends**: Ensures continuous recommendation flow even for isolated or obscure songs.
* **Exploration vs Exploitation**: 85% local sampling maintains playlist vibe consistency, while 15% multi-hop exploration prevents static monotony.
* **Explainability**: Recommendation paths are easily traceable for debugging or user UI displays (e.g. *"Playing next because of 0.82 audio similarity with Track B"*).
