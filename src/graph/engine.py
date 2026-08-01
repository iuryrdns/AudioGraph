"""
High-performance API wrapper for the dual-layer heterogeneous music recommendation graph.
Combines SciPy CSR sparse matrix operations with fast inverted index metadata lookups.
"""

from typing import Any

import numpy as np
import scipy.sparse as sp


class NodesView:

    def __init__(self, track_metadata: dict[str, dict[str, Any]]):
        self._metadata = track_metadata

    def __getitem__(self, track_id: str) -> dict[str, Any]:
        if track_id not in self._metadata:
            raise KeyError(f"Node '{track_id}' not in graph.")
        return self._metadata[track_id]

    def __contains__(self, track_id: str) -> bool:
        return track_id in self._metadata

    def __iter__(self):
        return iter(self._metadata)

    def __len__(self) -> int:
        return len(self._metadata)


class GraphEngine:

    def __init__(
        self,
        similarity_matrix: sp.csr_matrix,
        id_to_idx: dict[str, int],
        idx_to_id: np.ndarray,
        track_metadata: dict[str, dict[str, Any]],
        artist_to_tracks: dict[str, list[str]],
        genre_to_tracks: dict[str, list[str]],
        album_to_tracks: dict[str, list[str]],
        track_to_artist: dict[str, list[str]],
        track_to_genre: dict[str, str],
        track_to_album: dict[str, str],
    ):
        self.similarity_matrix = similarity_matrix
        self.id_to_idx = id_to_idx
        self.idx_to_id = idx_to_id
        self.track_metadata = track_metadata
        self.artist_to_tracks = artist_to_tracks
        self.genre_to_tracks = genre_to_tracks
        self.album_to_tracks = album_to_tracks
        self.track_to_artist = track_to_artist
        self.track_to_genre = track_to_genre
        self.track_to_album = track_to_album

        # NetworkX duck-typing helper
        self.nodes = NodesView(self.track_metadata)

    def __len__(self) -> int:
        return len(self.id_to_idx)

    def __contains__(self, track_id: str) -> bool:
        return track_id in self.id_to_idx

    def __getitem__(self, track_id: str) -> dict[str, dict[str, float]]:
        neighbors = self.get_neighbors(track_id)
        return {nbr_id: {"weight": weight} for nbr_id, weight in neighbors}

    def get_neighbors(self, track_id: str) -> list[tuple[str, float]]:
        """
        Query 1-hop similarity neighbors for a track_id.
        Returns list of (neighbor_track_id, similarity_weight).
        """
        if track_id not in self.id_to_idx:
            return []

        row_idx = self.id_to_idx[track_id]
        row_start = self.similarity_matrix.indptr[row_idx]
        row_end = self.similarity_matrix.indptr[row_idx + 1]

        col_indices = self.similarity_matrix.indices[row_start:row_end]
        weights = self.similarity_matrix.data[row_start:row_end]

        neighbors = [
            (str(self.idx_to_id[col]), float(weight))
            for col, weight in zip(col_indices, weights)
        ]
        # Sort descending by weight
        neighbors.sort(key=lambda x: x[1], reverse=True)
        return neighbors

    def get_metadata(self, track_id: str) -> dict[str, Any]:
        """
        Retrieve metadata dictionary for a track.
        """
        if track_id not in self.track_metadata:
            raise KeyError(f"Track ID '{track_id}' not found in metadata.")
        return self.track_metadata[track_id]

    def has_edge(self, u: str, v: str) -> bool:
        return self.get_edge_weight(u, v) > 0.0

    def get_edge_weight(self, u: str, v: str) -> float:
        if u not in self.id_to_idx or v not in self.id_to_idx:
            return 0.0
        u_idx = self.id_to_idx[u]
        v_idx = self.id_to_idx[v]

        row_start = self.similarity_matrix.indptr[u_idx]
        row_end = self.similarity_matrix.indptr[u_idx + 1]
        col_indices = self.similarity_matrix.indices[row_start:row_end]

        matches = np.where(col_indices == v_idx)[0]
        if len(matches) > 0:
            return float(self.similarity_matrix.data[row_start + matches[0]])
        return 0.0

    def get_2hop_metadata_candidates(self, track_id: str) -> list[str]:
        """
        Query 2-hop metadata candidate track_ids (same artist, genre, or album).
        """
        if track_id not in self.id_to_idx:
            return []

        candidates = set()

        # Same artist tracks
        artists = self.track_to_artist.get(track_id, [])
        for artist in artists:
            for tid in self.artist_to_tracks.get(artist, []):
                if tid != track_id:
                    candidates.add(tid)

        # Same genre tracks
        genre = self.track_to_genre.get(track_id)
        if genre:
            for tid in self.genre_to_tracks.get(genre, []):
                if tid != track_id:
                    candidates.add(tid)

        # Same album tracks
        album = self.track_to_album.get(track_id)
        if album:
            for tid in self.album_to_tracks.get(album, []):
                if tid != track_id:
                    candidates.add(tid)

        return list(candidates)
