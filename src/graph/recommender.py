"""
Implements the Adaptive Radio next-track recommendation algorithm based on hybrid
graph traversal, metadata affinity multipliers, anti-repetition circular history, and
Session Trajectory Memory (Full-Path Awareness).
"""

from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from src.config import RecommenderConfig
from src.graph.engine import GraphEngine
from src.graph.taxonomy import get_genre_compatibility

# Base weights for Layer 1 metadata connections in 2-hop exploration (backwards compatibility alias)
METADATA_WEIGHTS: dict[str, float] = RecommenderConfig().metadata_weights


@dataclass
class RecommendationResult:
    """
    Data container for next-track recommendation output.
    """

    recommended_track_id: str
    track_metadata: dict[str, Any]
    recommendation_type: str  # "1-hop acoustic", "2-hop multi-hop", "fallback"
    score: float
    explanation: str


class AdaptiveRadioRecommender:
    """
    Adaptive Radio Engine with Session Trajectory Memory (Full-Path Awareness).
    """

    def __init__(
        self,
        graph: GraphEngine,
        history_size: int | None = None,
        exploration_prob: float | None = None,
        artist_boost: float | None = None,
        genre_boost: float | None = None,
        trajectory_alpha: float | None = None,
        session_weight: float | None = None,
        metadata_weights: dict[str, float] | None = None,
        random_seed: int | None = None,
        config: RecommenderConfig | None = None,
    ):
        """
        Parameters
        ----------
        graph : GraphEngine
            Initialised GraphEngine instance.
        history_size : int, optional
            Circular buffer size N for tracking recently played tracks.
        exploration_prob : float, optional
            Probability (0.0 to 1.0) of triggering multi-hop exploration.
        artist_boost : float, optional
            Multiplier for 1-hop candidates sharing the same artist (+35%).
        genre_boost : float, optional
            Multiplier for 1-hop candidates sharing the same genre (+20%).
        trajectory_alpha : float, optional
            Decay rate alpha for session trajectory vector (EMA).
        session_weight : float, optional
            Weight (0.0 to 1.0) assigned to global session vector alignment vs local transition.
        metadata_weights : Dict[str, float], optional
            Weights for artist, album, genre metadata connections in 2-hop exploration.
        random_seed : int, optional
            Random seed for reproducible recommendation streams.
        config : RecommenderConfig, optional
            Centralized RecommenderConfig instance.
        """
        cfg = config or RecommenderConfig()

        self.graph = graph
        self.history_size = (
            history_size if history_size is not None else cfg.history_size
        )
        self.exploration_prob = (
            exploration_prob if exploration_prob is not None else cfg.exploration_prob
        )
        self.artist_boost = (
            artist_boost if artist_boost is not None else cfg.artist_boost
        )
        self.genre_boost = genre_boost if genre_boost is not None else cfg.genre_boost
        self.trajectory_alpha = (
            trajectory_alpha if trajectory_alpha is not None else cfg.trajectory_alpha
        )
        self.session_weight = (
            session_weight if session_weight is not None else cfg.session_weight
        )
        self.metadata_weights = (
            metadata_weights if metadata_weights is not None else cfg.metadata_weights
        )

        self.history_buffer: deque[str] = deque(maxlen=self.history_size)
        self.session_vector: np.ndarray | None = None
        self.rng = np.random.RandomState(random_seed)

    def reset_session(self) -> None:
        """
        Resets session state: clears circular history buffer and session trajectory vector.
        """
        self.history_buffer.clear()
        self.session_vector = None

    def reset_history(self) -> None:
        """
        Alias for reset_session.
        """
        self.reset_session()

    def get_history(self) -> list[str]:
        """
        Returns the list of recently played track IDs in the history buffer.
        """
        return list(self.history_buffer)

    def update_session_trajectory(self, track_id: str) -> None:
        """
        Updates the running Exponential Moving Average (EMA) session vector with track_id acoustic features.
        """
        x_k = self.graph.get_feature_vector(track_id)
        if x_k is None:
            return

        if self.session_vector is None:
            self.session_vector = np.copy(x_k)
        else:
            raw_vec = (
                self.trajectory_alpha * x_k
                + (1.0 - self.trajectory_alpha) * self.session_vector
            )
            norm = np.linalg.norm(raw_vec)
            self.session_vector = raw_vec / (norm if norm > 0 else 1e-8)

    def recommend_next(
        self,
        current_track_id: str,
        exclude_ids: set[str] | list[str] | None = None,
        feedback: dict[str, list[str]] | None = None,
    ) -> RecommendationResult:
        """
        Generates the next track recommendation given the current playing track, taking into account
        optional user feedback (liked/disliked artists & genres) and excluded track IDs.
        """
        if current_track_id not in self.graph:
            raise KeyError(f"Track ID '{current_track_id}' not found in graph engine.")

        # Update session state with current track
        if current_track_id not in self.history_buffer:
            self.history_buffer.append(current_track_id)
            self.update_session_trajectory(current_track_id)

        excluded_ids = set(self.history_buffer)
        excluded_ids.add(current_track_id)
        if exclude_ids:
            excluded_ids.update(str(x) for x in exclude_ids)

        # Decide whether to attempt 1-hop sampling or multi-hop exploration
        roll = self.rng.uniform(0.0, 1.0)
        should_explore = roll < self.exploration_prob

        result: RecommendationResult | None = None

        if not should_explore:
            # Step 1: Direct 1-Hop Weighted Sampling (with metadata boost, feedback & session trajectory)
            result = self._try_1hop_sampling(current_track_id, excluded_ids, feedback)

        if result is None:
            # Step 2: Multi-Hop Fallback & Exploration
            result = self._try_2hop_traversal(current_track_id, excluded_ids, feedback)

        if result is None:
            # Step 3: Global Fallback (genre-anchored — see _global_fallback)
            result = self._global_fallback(excluded_ids, feedback, current_track_id)

        # Push recommended track into history and update session vector
        self.history_buffer.append(result.recommended_track_id)
        self.update_session_trajectory(result.recommended_track_id)
        return result

    def recommend_stream(
        self,
        seed_track_id: str,
        count: int = 10,
        exclude_ids: set[str] | list[str] | None = None,
        feedback: dict[str, list[str]] | None = None,
    ) -> list[RecommendationResult]:
        """
        Generates a continuous stream of next-track recommendations starting from a seed track.
        """
        stream: list[RecommendationResult] = []
        curr_id = seed_track_id
        running_excluded = set(str(x) for x in (exclude_ids or []))

        for _ in range(count):
            rec = self.recommend_next(curr_id, exclude_ids=running_excluded, feedback=feedback)
            stream.append(rec)
            running_excluded.add(rec.recommended_track_id)
            curr_id = rec.recommended_track_id

        return stream

    def _get_feedback_multiplier(
        self, track_id: str, feedback: dict[str, list[str]] | None
    ) -> float:
        if not feedback:
            return 1.0

        liked_artists = set(a.lower() for a in (feedback.get("liked_artists") or feedback.get("likedArtists") or []))
        liked_genres = set(g.lower() for g in (feedback.get("liked_genres") or feedback.get("likedGenres") or []))
        disliked_artists = set(a.lower() for a in (feedback.get("disliked_artists") or feedback.get("dislikedArtists") or []))
        disliked_genres = set(g.lower() for g in (feedback.get("disliked_genres") or feedback.get("dislikedGenres") or []))

        meta = self.graph.get_metadata(track_id)
        artist = (meta.get("primary_artist") or meta.get("artists") or "").lower()
        genre = (meta.get("track_genre") or "").lower()

        mult = 1.0
        if artist in liked_artists:
            mult *= 1.4
        if genre in liked_genres:
            mult *= 1.25
        if artist in disliked_artists:
            mult *= 0.05
        if genre in disliked_genres:
            mult *= 0.2

        return mult

    def _try_1hop_sampling(
        self,
        current_track_id: str,
        excluded_ids: set[str],
        feedback: dict[str, list[str]] | None = None,
    ) -> RecommendationResult | None:
        """
        Attempts direct 1-hop weighted sampling with metadata boost, feedback alignment, and session trajectory alignment.
        """
        neighbors = self.graph.get_neighbors(current_track_id)
        candidates = [(nid, w) for nid, w in neighbors if nid not in excluded_ids]

        if not candidates:
            return None

        curr_artists = set(self.graph.track_to_artist.get(current_track_id, []))
        curr_genre = self.graph.track_to_genre.get(current_track_id)

        boosted_weights = []
        for nid, base_weight in candidates:
            local_score = base_weight
            boost = 1.0
            nbr_artists = set(self.graph.track_to_artist.get(nid, []))
            if curr_artists & nbr_artists:
                boost *= self.artist_boost

            if curr_genre and self.graph.track_to_genre.get(nid) == curr_genre:
                boost *= self.genre_boost

            boost *= self._get_feedback_multiplier(nid, feedback)
            local_score *= boost

            # Incorporate Session Trajectory Memory
            if self.session_vector is not None and self.session_weight > 0.0:
                c_vec = self.graph.get_feature_vector(nid)
                if c_vec is not None:
                    dist = np.linalg.norm(self.session_vector - c_vec)
                    session_sim = float(np.exp(-2.0 * dist))
                    final_score = (
                        1.0 - self.session_weight
                    ) * local_score + self.session_weight * session_sim
                else:
                    final_score = local_score
            else:
                final_score = local_score

            boosted_weights.append(final_score)

        c_ids = [c[0] for c in candidates]
        weights_arr = np.array(boosted_weights, dtype=np.float64)
        total_w = weights_arr.sum()
        if total_w <= 0:
            prob_dist = np.ones(len(c_ids)) / len(c_ids)
        else:
            prob_dist = weights_arr / total_w

        chosen_idx = self.rng.choice(len(c_ids), p=prob_dist)
        chosen_id = c_ids[chosen_idx]
        chosen_weight = float(candidates[chosen_idx][1])

        meta = self.graph.get_metadata(chosen_id)
        track_name = meta.get("track_name", chosen_id)
        artist_name = meta.get("primary_artist", "Unknown Artist")

        affinities = []
        nbr_artists = set(self.graph.track_to_artist.get(chosen_id, []))
        if curr_artists & nbr_artists:
            affinities.append("same artist")
        if curr_genre and self.graph.track_to_genre.get(chosen_id) == curr_genre:
            affinities.append("same genre")

        affinity_str = f" [{', '.join(affinities)}]" if affinities else ""

        return RecommendationResult(
            recommended_track_id=chosen_id,
            track_metadata=meta,
            recommendation_type="1-hop acoustic",
            score=chosen_weight,
            explanation=(
                f"Direct acoustic similarity ({chosen_weight:.2f}){affinity_str} with '{track_name}' by {artist_name}"
            ),
        )

    def _try_2hop_traversal(
        self,
        current_track_id: str,
        excluded_ids: set[str],
        feedback: dict[str, list[str]] | None = None,
    ) -> RecommendationResult | None:
        """
        Executes 2-hop similarity and metadata path scoring ($A -> X -> C$).
        """
        candidate_scores: dict[str, float] = {}

        # Path A: 2-Hop Track-to-Track Similarity Path (A -> B -> C)
        for b_id, w_ab in self.graph.get_neighbors(current_track_id):
            for c_id, w_bc in self.graph.get_neighbors(b_id):
                if c_id not in excluded_ids:
                    candidate_scores[c_id] = candidate_scores.get(c_id, 0.0) + (
                        w_ab * w_bc
                    )

        # Path B: 2-Hop Track-Attribute Metadata Path
        metadata_candidates = self.graph.get_2hop_metadata_candidates(current_track_id)
        curr_artists = set(self.graph.track_to_artist.get(current_track_id, []))
        curr_genre = self.graph.track_to_genre.get(current_track_id)
        curr_album = self.graph.track_to_album.get(current_track_id)

        for c_id in metadata_candidates:
            if c_id in excluded_ids:
                continue

            meta_score = 0.0
            # Same artist check
            c_artists = set(self.graph.track_to_artist.get(c_id, []))
            if curr_artists & c_artists:
                meta_score += self.metadata_weights.get("artist", 0.8)

            # Same album check
            if curr_album and self.graph.track_to_album.get(c_id) == curr_album:
                meta_score += self.metadata_weights.get("album", 0.7)

            # Same genre check
            if curr_genre and self.graph.track_to_genre.get(c_id) == curr_genre:
                meta_score += self.metadata_weights.get("genre", 0.5)

            direct_weight = self.graph.get_edge_weight(current_track_id, c_id)
            acoustic_factor = direct_weight if direct_weight > 0.0 else 0.5

            candidate_scores[c_id] = candidate_scores.get(c_id, 0.0) + (
                meta_score * acoustic_factor
            )

        if not candidate_scores:
            return None

        # Apply user feedback multipliers
        for c_id in list(candidate_scores.keys()):
            candidate_scores[c_id] *= self._get_feedback_multiplier(c_id, feedback)

        # Blend with session trajectory vector
        if self.session_vector is not None and self.session_weight > 0.0:
            for c_id in list(candidate_scores.keys()):
                c_vec = self.graph.get_feature_vector(c_id)
                if c_vec is not None:
                    dist = np.linalg.norm(self.session_vector - c_vec)
                    session_sim = float(np.exp(-2.0 * dist))
                    candidate_scores[c_id] = (
                        1.0 - self.session_weight
                    ) * candidate_scores[c_id] + self.session_weight * session_sim

        c_ids = list(candidate_scores.keys())
        scores = np.array([candidate_scores[cid] for cid in c_ids], dtype=np.float64)
        total_score = scores.sum()

        if total_score <= 0.0:
            prob_dist = np.ones(len(c_ids)) / len(c_ids)
        else:
            prob_dist = scores / total_score

        chosen_idx = self.rng.choice(len(c_ids), p=prob_dist)
        chosen_id = c_ids[chosen_idx]
        chosen_score = float(scores[chosen_idx])

        meta = self.graph.get_metadata(chosen_id)
        track_name = meta.get("track_name", chosen_id)
        artist_name = meta.get("primary_artist", "Unknown Artist")

        return RecommendationResult(
            recommended_track_id=chosen_id,
            track_metadata=meta,
            recommendation_type="2-hop multi-hop",
            score=chosen_score,
            explanation=(
                f"Multi-hop graph score ({chosen_score:.2f}) to '{track_name}' by {artist_name}"
            ),
        )

    def _global_fallback(
        self,
        excluded_ids: set[str],
        feedback: dict[str, list[str]] | None = None,
        current_track_id: str | None = None,
    ) -> RecommendationResult:
        """
        Global fallback sampling when 1-hop and 2-hop candidate pools are exhausted
        (common for niche/underrepresented genres once their small neighbor pool
        has been played through). Still weighted by genre compatibility with the
        current track so a niche-genre seed doesn't randomly land on an
        acoustically/stylistically unrelated genre just because the catalog is
        dominated by other genres — e.g. without this, a ~100-track genre in an
        ~90k-track mostly-English catalog would almost always fall back to
        something completely unrelated.
        """
        all_ids = [str(tid) for tid in self.graph.idx_to_id]
        available_ids = [tid for tid in all_ids if tid not in excluded_ids]

        if not available_ids:
            # Clear history buffer if literally all tracks have been played
            self.reset_session()
            available_ids = all_ids

        curr_genre = (
            self.graph.track_to_genre.get(current_track_id) if current_track_id else None
        )
        if curr_genre:
            weights = np.array(
                [
                    get_genre_compatibility(curr_genre, self.graph.track_to_genre.get(tid, ""))
                    for tid in available_ids
                ],
                dtype=np.float64,
            )
        else:
            weights = np.ones(len(available_ids), dtype=np.float64)

        if feedback:
            fb_mult = np.array(
                [self._get_feedback_multiplier(tid, feedback) for tid in available_ids],
                dtype=np.float64,
            )
            weights = weights * fb_mult

        total = weights.sum()
        if total > 0:
            prob = weights / total
            chosen_id = str(self.rng.choice(available_ids, p=prob))
        else:
            chosen_id = str(self.rng.choice(available_ids))

        meta = self.graph.get_metadata(chosen_id)
        track_name = meta.get("track_name", chosen_id)
        artist_name = meta.get("primary_artist", "Unknown Artist")

        return RecommendationResult(
            recommended_track_id=chosen_id,
            track_metadata=meta,
            recommendation_type="fallback",
            score=0.1,
            explanation=f"Genre-anchored fallback to '{track_name}' by {artist_name}",
        )