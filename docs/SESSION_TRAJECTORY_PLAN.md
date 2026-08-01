# Implementation Plan: Session Trajectory Memory (Full-Path Awareness)

**Document Path**: [`docs/SESSION_TRAJECTORY_PLAN.md`](file:///home/adley/repos/university/AudioGraph-AI/docs/SESSION_TRAJECTORY_PLAN.md)  
**Target Module**: [`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py)  
**Status**: Proposed / Approved  

---

## 1. Executive Summary & Objective

Currently, AudioGraph-AI generates recommendations using 1-step **Markovian transitions** ($T_k \to T_{k+1}$): candidate tracks are evaluated relative to the immediate predecessor $T_k$, using the recent path only to exclude previously played tracks ($N=15$ history buffer).

While this provides fast local transitions, extended listening sessions risk **Vibe Drift**—where a single bridging track shifts the playlist into an unrelated genre/vibe, forgetting the user's initial listening context.

**Objective**: Implement **Session Trajectory Memory**, maintaining a cumulative, exponentially weighted acoustic embedding vector of the listening session ($\vec{v}_{\text{session}}$). Candidate tracks will be scored against both the local predecessor $T_k$ and the global session vector $\vec{v}_{\text{session}}$.

---

## 2. Mathematical Model & Architecture

```
                    ┌───────────────────────────────┐
                    │  Current Played Track (T_k)   │
                    │  Vector: x_k                  │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │ Update Session Embedding Vector (Exponential Decay):      │
       │  v_session^(k) = L2_Normalize( α*x_k + (1-α)*v_session )  │
       └────────────────────────────┬─────────────────────────────┘
                                    │
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │ Hybrid Candidate Scoring for Next Track C:               │
       │  Score(C) = λ * S_local(T_k, C) + (1-λ) * S_session(v, C) │
       └────────────────────────────┬─────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ Weighted Softmax Sampling     │
                    │ Selection: T_(k+1)            │
                    └───────────────┬───────────────┘
```

### 2.1 Session Vector Update Rule (Exponential Moving Average)
When a track $T_k$ with normalized feature vector $\mathbf{x}_k \in \mathbb{R}^F$ is played:

$$\vec{v}_{\text{session}}^{(k)} = \text{L2\_Normalize}\left( \alpha \cdot \mathbf{x}_k + (1 - \alpha) \cdot \vec{v}_{\text{session}}^{(k-1)} \right)$$

* **$\alpha \in (0, 1]$ (default $\alpha = 0.6$)**: Trajectory decay rate.
  * $\alpha = 1.0$: Pure Markovian (no historical session memory).
  * $\alpha = 0.6$: Balanced session awareness (60% weight on current track, 40% memory of session history).
  * $\alpha = 0.2$: Strong anchor on session origin.

### 2.2 Hybrid Candidate Scoring
For every candidate track $C \in \text{Candidates}(T_k)$:

$$\text{Score}_{\text{hybrid}}(C) = \lambda \cdot S_{\text{local}}(T_k, C) + (1 - \lambda) \cdot S_{\text{session}}(\vec{v}_{\text{session}}, C)$$

* **$S_{\text{local}}(T_k, C)$**: 1-hop acoustic similarity with metadata boost ($W_{\text{boosted}}$).
* **$S_{\text{session}}(\vec{v}_{\text{session}}, C)$**: Gaussian RBF similarity between candidate vector $\mathbf{x}_C$ and the global session vector $\vec{v}_{\text{session}}$:
  $$S_{\text{session}} = \exp\left( -\gamma \cdot \|\vec{v}_{\text{session}} - \mathbf{x}_C\|_{2, W} \right)$$
* **$\lambda \in [0, 1]$ (default $\lambda = 0.7$)**:
  * $70\%$ weight on immediate local transition continuity.
  * $30\%$ weight on global session vibe alignment.

---

## 3. Implementation Roadmap

### Phase 1: Feature Vector Accessor ([`src/graph/engine.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/engine.py))
- Store normalized feature matrix $X_{\text{scaled}}$ inside `GraphEngine`.
- Implement `graph.get_feature_vector(track_id: str) -> np.ndarray` for $O(1)$ vector retrievals.

### Phase 2: Session Trajectory Integration ([`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py))
- Add parameters to `AdaptiveRadioRecommender`:
  * `trajectory_alpha: float = 0.6`
  * `session_weight: float = 0.3`
- Add session state management:
  * `session_vector: Optional[np.ndarray]`
  * `update_session_trajectory(track_id: str)`
  * `reset_session()` (clears `history_buffer` and `session_vector`)
- Update `_try_1hop_sampling()` and `_try_2hop_traversal()` to blend candidate scores with $S_{\text{session}}$.

### Phase 3: Unit Testing ([`tests/test_recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/tests/test_recommender.py))
- Test `session_vector` initialization and EMA vector updating.
- Verify session trajectory prevents vibe drift across a 20-track recommendation stream.
- Verify `reset_session()` resets trajectory state.

### Phase 4: CLI Demonstration & Config ([`main.py`](file:///home/adley/repos/university/AudioGraph-AI/main.py) & [`.env.example`](file:///home/adley/repos/university/AudioGraph-AI/.env.example))
- Add environment variables:
  * `TRAJECTORY_ALPHA=0.6`
  * `SESSION_WEIGHT=0.3`
- Add CLI flag `--trajectory` to `main.py`.

---

## 4. Verification & Success Criteria

1. **Vibe Drift Reduction**: In a 20-track stream, acoustic distance between track 20 and the session origin vector $\mathbf{x}_{\text{seed}}$ is bounded within $\le 0.35$ (vs $\ge 0.70$ without session memory).
2. **Performance**: Zero measurable latency increase ($< 0.001\text{s}$ per recommendation step).
3. **Test Suite**: 100% pass rate across all unit tests (`pytest`).
