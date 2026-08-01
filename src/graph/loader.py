"""
AudioGraph-AI Data Loader Module

Responsible for loading dataset CSVs, cleaning missing data, parsing multi-artist strings,
deduplicating track entries, and normalizing pure audio acoustic features to [0, 1] bounded space.
"""

from typing import Dict, List
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from src.graph.taxonomy import get_super_genre

# Pure acoustic features used for matrix similarity calculation
# (popularity and duration_ms are excluded from vector similarity to prevent non-acoustic bias)
FEATURE_COLUMNS: List[str] = [
    "danceability",
    "energy",
    "valence",
    "tempo_norm",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "loudness_norm",
    "liveness",
]

RAW_FEATURE_COLS: List[str] = [
    "danceability",
    "energy",
    "valence",
    "tempo",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "loudness",
    "liveness",
    "duration_ms",
    "popularity",
]


class TrackDataset:
    """
    Container class holding preprocessed track dataset artifacts.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        X_scaled: np.ndarray,
        scaler: MinMaxScaler,
        id_to_idx: Dict[str, int],
        idx_to_id: np.ndarray,
    ):
        self.df = df
        self.X_scaled = X_scaled
        self.scaler = scaler
        self.id_to_idx = id_to_idx
        self.idx_to_id = idx_to_id

    def __len__(self) -> int:
        return len(self.df)

    def get_track_metadata(self, track_id: str) -> dict:
        """
        Retrieves raw metadata for a specific track ID.
        """
        if track_id not in self.id_to_idx:
            raise KeyError(f"Track ID '{track_id}' not found in dataset.")
        idx = self.id_to_idx[track_id]
        row = self.df.iloc[idx]
        return row.to_dict()


def parse_artist_string(artist_str: str) -> List[str]:
    """
    Parses a multi-artist string separated by ';' into individual trimmed artist names.
    Example: "YUNGBLUD;Charlotte Lawrence" -> ["YUNGBLUD", "Charlotte Lawrence"]
    """
    if not isinstance(artist_str, str) or not artist_str.strip():
        return ["Unknown Artist"]
    artists = [a.strip() for a in artist_str.split(";") if a.strip()]
    return artists if artists else ["Unknown Artist"]


def load_and_preprocess_dataset(csv_path: str) -> TrackDataset:
    """
    Loads dataset CSV, cleans missing values, parses artists, deduplicates tracks,
    and computes [0, 1] bounded feature matrix using MinMaxScaler.

    Parameters
    ----------
    csv_path : str
        Path to the Spotify tracks dataset CSV file.

    Returns
    -------
    TrackDataset
        Container with preprocessed DataFrame, scaled feature matrix,
        MinMaxScaler instance, and bi-directional track ID index maps.
    """
    # 1. Load CSV
    df = pd.read_csv(csv_path)

    # 2. Drop index column if present (e.g. 'Unnamed: 0')
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    # 3. Handle missing/invalid data
    required_cols = ["track_id", "track_name", "artists", "track_genre"] + RAW_FEATURE_COLS
    df = df.dropna(subset=[col for col in required_cols if col in df.columns]).copy()

    # 4. Normalized acoustic features
    df["loudness_norm"] = np.clip((df["loudness"] + 60.0) / 60.0, 0.0, 1.0)
    df["tempo_norm"] = np.clip(df["tempo"] / 200.0, 0.0, 1.0)

    # 5. Super-Genre Family Mapping
    df["super_genre"] = df["track_genre"].astype(str).apply(get_super_genre)

    # 6. Parse multi-artist strings & set primary artist
    df["artist_list"] = df["artists"].astype(str).apply(parse_artist_string)
    df["primary_artist"] = df["artist_list"].apply(lambda arr: arr[0])

    # 7. Entity ID Formatting
    df["album_name"] = df["album_name"].fillna("Unknown Album")
    df["album_entity"] = "album_" + df["primary_artist"] + "_" + df["album_name"].astype(str)
    df["genre_entity"] = "genre_" + df["track_genre"].astype(str)
    df["artist_entities"] = df["artist_list"].apply(lambda arr: ["artist_" + a for a in arr])

    # 8. Data Deduplication
    df = df.drop_duplicates(subset=["track_id"], keep="first")
    df = df.drop_duplicates(subset=["primary_artist", "track_name"], keep="first")
    df = df.drop_duplicates(subset=FEATURE_COLUMNS, keep="first")

    df = df.reset_index(drop=True)

    # 9. Index Mapping
    track_ids = df["track_id"].values.astype(str)
    id_to_idx: Dict[str, int] = {tid: idx for idx, tid in enumerate(track_ids)}
    idx_to_id: np.ndarray = np.array(track_ids, dtype=object)

    # 10. Pure Audio Feature Extraction & MinMaxScaler Normalization
    X_raw = df[FEATURE_COLUMNS].values.astype(np.float32)
    scaler = MinMaxScaler(feature_range=(0.0, 1.0))
    X_scaled = scaler.fit_transform(X_raw).astype(np.float32)

    return TrackDataset(
        df=df,
        X_scaled=X_scaled,
        scaler=scaler,
        id_to_idx=id_to_idx,
        idx_to_id=idx_to_id,
    )
