"""
Categorizes raw Spotify sub-genres into cohesive Super-Genre Families
and provides compatibility distance matrices for graph edge filtering.
"""

import unicodedata


def _normalize(text: str) -> str:
    """
    Lowercases and strips diacritics so tag variants like
    'forró' / 'forro' or 'música' / 'musica' resolve to the same key.
    Without this, accented tags silently fall through to 'OTHER'.
    """
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


SUPER_GENRE_MAP: dict[str, str] = {
    # ACOUSTIC / INDIE / SAD / CHILL
    "acoustic": "ACOUSTIC_INDIE",
    "sad": "ACOUSTIC_INDIE",
    "indie": "ACOUSTIC_INDIE",
    "indie-pop": "ACOUSTIC_INDIE",
    "chill": "ACOUSTIC_INDIE",
    "singer-songwriter": "ACOUSTIC_INDIE",
    "singer & songwriter": "ACOUSTIC_INDIE",
    "singer/songwriter": "ACOUSTIC_INDIE",
    "songwriter": "ACOUSTIC_INDIE",
    "folk": "ACOUSTIC_INDIE",
    "alternative folk": "ACOUSTIC_INDIE",
    "bluegrass": "ACOUSTIC_INDIE",
    "guitar": "ACOUSTIC_INDIE",
    "romance": "ACOUSTIC_INDIE",
    # CLASSICAL / AMBIENT / PIANO / SLEEP
    "classical": "CLASSICAL_AMBIENT",
    "classica": "CLASSICAL_AMBIENT",
    "ambient": "CLASSICAL_AMBIENT",
    "piano": "CLASSICAL_AMBIENT",
    "sleep": "CLASSICAL_AMBIENT",
    "study": "CLASSICAL_AMBIENT",
    "new-age": "CLASSICAL_AMBIENT",
    "opera": "CLASSICAL_AMBIENT",
    "instrumental": "CLASSICAL_AMBIENT",
    # POP / DANCE-POP
    "pop": "POP",
    "pop latino": "POP",
    "dance": "POP",
    "synth-pop": "POP",
    "k-pop": "POP",
    "j-pop": "POP",
    "j-idol": "POP",
    "cantopop": "POP",
    "mandopop": "POP",
    "power-pop": "POP",
    "british": "POP",
    "french": "POP",
    "german": "POP",
    "swedish": "POP",
    "spanish": "POP",
    # ELECTRONIC / DANCE / HOUSE / TECHNO / TRANCE
    "edm": "ELECTRONIC_DANCE",
    "house": "ELECTRONIC_DANCE",
    "deep-house": "ELECTRONIC_DANCE",
    "chicago-house": "ELECTRONIC_DANCE",
    "progressive-house": "ELECTRONIC_DANCE",
    "minimal-techno": "ELECTRONIC_DANCE",
    "techno": "ELECTRONIC_DANCE",
    "detroit-techno": "ELECTRONIC_DANCE",
    "trance": "ELECTRONIC_DANCE",
    "club": "ELECTRONIC_DANCE",
    "electro": "ELECTRONIC_DANCE",
    "electronic": "ELECTRONIC_DANCE",
    "breakbeat": "ELECTRONIC_DANCE",
    "drum-and-bass": "ELECTRONIC_DANCE",
    "dubstep": "ELECTRONIC_DANCE",
    "hardstyle": "ELECTRONIC_DANCE",
    "hardcore": "ELECTRONIC_DANCE",
    "idm": "ELECTRONIC_DANCE",
    "trip-hop": "ELECTRONIC_DANCE",
    "j-dance": "ELECTRONIC_DANCE",
    "party": "ELECTRONIC_DANCE",
    "happy": "ELECTRONIC_DANCE",
    "disco": "ELECTRONIC_DANCE",
    "garage": "ELECTRONIC_DANCE",
    # ROCK / METAL / PUNK
    "rock": "ROCK_METAL",
    "alt-rock": "ROCK_METAL",
    "alternative": "ROCK_METAL",
    "alternativo": "ROCK_METAL",
    "hard-rock": "ROCK_METAL",
    "hard rock": "ROCK_METAL",
    "heavy-metal": "ROCK_METAL",
    "black-metal": "ROCK_METAL",
    "death-metal": "ROCK_METAL",
    "metal": "ROCK_METAL",
    "metalcore": "ROCK_METAL",
    "grindcore": "ROCK_METAL",
    "punk": "ROCK_METAL",
    "punk-rock": "ROCK_METAL",
    "psych-rock": "ROCK_METAL",
    "j-rock": "ROCK_METAL",
    "grunge": "ROCK_METAL",
    "emo": "ROCK_METAL",
    "goth": "ROCK_METAL",
    "industrial": "ROCK_METAL",
    "rock-n-roll": "ROCK_METAL",
    "rockabilly": "ROCK_METAL",
    "rock latino": "ROCK_METAL",
    # HIP-HOP / R&B / SOUL / FUNK
    "hip-hop": "HIPHOP_URBAN",
    "hip-hop/rap": "HIPHOP_URBAN",
    "rap/hip hop": "HIPHOP_URBAN",
    "rap/funk brasileiro": "HIPHOP_URBAN",
    "r-n-b": "HIPHOP_URBAN",
    "r&b": "HIPHOP_URBAN",
    "r&b/soul": "HIPHOP_URBAN",
    "soul": "HIPHOP_URBAN",
    "soul & funk": "HIPHOP_URBAN",
    "soul contemporaneo": "HIPHOP_URBAN",
    "funk": "HIPHOP_URBAN",
    "groove": "HIPHOP_URBAN",
    # REGGAE / DUB / DANCEHALL / SKA / LATIN
    "reggae": "REGGAE_DUB",
    "dub": "REGGAE_DUB",
    "dancehall": "REGGAE_DUB",
    "ska": "REGGAE_DUB",
    "afrobeat": "REGGAE_DUB",
    "musica africana": "REGGAE_DUB",
    "cumbia": "SPANISH_LATIN_URBAN",
    "folklore latino-americain": "SPANISH_LATIN_URBAN",
    "norteno": "SPANISH_LATIN_URBAN",
    "bolero": "SPANISH_LATIN_URBAN",
    "ranchera": "SPANISH_LATIN_URBAN",
    "flamenco": "SPANISH_LATIN_URBAN",
    "banda/grupero": "SPANISH_LATIN_URBAN",
    "latin": "SPANISH_LATIN_URBAN",
    "latino": "SPANISH_LATIN_URBAN",
    "reggaeton": "SPANISH_LATIN_URBAN",
    "salsa": "SPANISH_LATIN_URBAN",
    "tango": "SPANISH_LATIN_URBAN",
    # BRAZILIAN FORRÓ / AXÉ / SERTANEJO / PISADINHA / MPB / SAMBA
    "forro": "BRAZILIAN_FORRO_AXE",
    "axe/forro": "BRAZILIAN_FORRO_AXE",
    "sertanejo": "BRAZILIAN_SERTANEJO",
    "pisadinha": "BRAZILIAN_PISADINHA",
    "piseiro": "BRAZILIAN_PISADINHA",
    "forro eletronico": "BRAZILIAN_PISADINHA",
    "brazil": "BRAZILIAN_MPB_SAMBA_ROCK",
    "mpb": "BRAZILIAN_MPB_SAMBA_ROCK",
    "samba": "BRAZILIAN_MPB_SAMBA_ROCK",
    "pagode": "BRAZILIAN_MPB_SAMBA_ROCK",
    "samba/pagode": "BRAZILIAN_MPB_SAMBA_ROCK",
    # JAZZ / BLUES / COUNTRY
    "jazz": "JAZZ_BLUES",
    "blues": "JAZZ_BLUES",
    "country": "JAZZ_BLUES",
    "honky-tonk": "JAZZ_BLUES",
    "gospel": "JAZZ_BLUES",
    # WORLD / MEDIA / INDIAN
    "anime": "WORLD_MEDIA",
    "pop-film": "WORLD_MEDIA",
    "show-tunes": "WORLD_MEDIA",
    "disney": "WORLD_MEDIA",
    "children": "WORLD_MEDIA",
    "kids": "WORLD_MEDIA",
    "children's music": "WORLD_MEDIA",
    "infantil": "WORLD_MEDIA",
    "filmes/games": "WORLD_MEDIA",
    "soundtrack": "WORLD_MEDIA",
    "comedy": "WORLD_MEDIA",
    "comedia": "WORLD_MEDIA",
    "spoken word": "WORLD_MEDIA",
    "holiday": "WORLD_MEDIA",
    "musica religiosa": "WORLD_MEDIA",
    "indian": "WORLD_MEDIA",
    "indian-folk": "WORLD_MEDIA",
    "indian folk": "WORLD_MEDIA",
    "musica indiana": "WORLD_MEDIA",
    "musica asiatica": "WORLD_MEDIA",
    "bollywood": "WORLD_MEDIA",
    "indian pop": "WORLD_MEDIA",
    "tamil": "WORLD_MEDIA",
    "telugu": "WORLD_MEDIA",
    "kannada": "WORLD_MEDIA",
    "devotional & spiritual": "WORLD_MEDIA",
    "iranian": "WORLD_MEDIA",
    "malay": "WORLD_MEDIA",
    "turkish": "WORLD_MEDIA",
    "world-music": "WORLD_MEDIA",
    "world music": "WORLD_MEDIA",
}

# Pre-normalized lookup built once at import time. This is what makes
# accented / non-accented tag variants ("forró" vs "forro") resolve to
# the same super-genre without needing duplicate entries above.
_NORMALIZED_MAP: dict[str, str] = {_normalize(k): v for k, v in SUPER_GENRE_MAP.items()}


def get_super_genre(genre: str) -> str:
    """
    Returns the Super-Genre Family for a given sub-genre.
    Defaults to 'OTHER' if genre is unknown.
    """
    return _NORMALIZED_MAP.get(_normalize(genre), "OTHER")


def get_genre_compatibility(genre1: str, genre2: str) -> float:
    """
    Calculates the compatibility factor (0.1 to 1.0) between two sub-genres.

    Parameters
    ----------
    genre1 : str
        First genre string.
    genre2 : str
        Second genre string.

    Returns
    -------
    float
        1.0 for identical genres, 0.85 for same Super-Genre family, 0.15 for distant.
    """
    g1 = _normalize(genre1)
    g2 = _normalize(genre2)

    if g1 == g2:
        return 1.0

    sg1 = get_super_genre(g1)
    sg2 = get_super_genre(g2)

    if sg1 == sg2 and sg1 != "OTHER":
        return 0.85

    # Compatible adjacent Super-Genre pairs with custom affinity weights
    adjacent_pairs: dict[tuple[str, str], float] = {
        ("ACOUSTIC_INDIE", "POP"): 0.50,
        ("ACOUSTIC_INDIE", "CLASSICAL_AMBIENT"): 0.50,
        ("ACOUSTIC_INDIE", "JAZZ_BLUES"): 0.50,
        ("POP", "ELECTRONIC_DANCE"): 0.50,
        ("POP", "HIPHOP_URBAN"): 0.50,
        ("POP", "SPANISH_LATIN_URBAN"): 0.50,
        ("ROCK_METAL", "POP"): 0.50,
        ("ROCK_METAL", "BRAZILIAN_MPB_SAMBA_ROCK"): 0.60,
        ("HIPHOP_URBAN", "REGGAE_DUB"): 0.50,
        ("HIPHOP_URBAN", "SPANISH_LATIN_URBAN"): 0.50,
        # Pisadinha/piseiro shares roots with forró and with sertanejo,
        # but its heavily electronic production sits closer to sertanejo
        # universitário than to acoustic pé-de-serra forró.
        ("BRAZILIAN_PISADINHA", "BRAZILIAN_SERTANEJO"): 0.55,
        ("BRAZILIAN_PISADINHA", "BRAZILIAN_FORRO_AXE"): 0.45,
        ("BRAZILIAN_SERTANEJO", "BRAZILIAN_FORRO_AXE"): 0.40,
        ("BRAZILIAN_MPB_SAMBA_ROCK", "BRAZILIAN_SERTANEJO"): 0.30,
    }

    if (sg1, sg2) in adjacent_pairs:
        return adjacent_pairs[(sg1, sg2)]
    if (sg2, sg1) in adjacent_pairs:
        return adjacent_pairs[(sg2, sg1)]

    return 0.15


# --- Audio-feature tiebreaker -------------------------------------------
#
# Some Spotify genre tags are too coarse to separate real sub-styles.
# "forro" is the clearest example: it covers everything from acoustic
# pé-de-serra (Luiz Gonzaga, Dominguinhos, loudness ~ -8 to -10 dB) to
# heavily produced modern piseiro (Barões da Pisadinha, Henry Freitas,
# loudness ~ -2 to -4 dB). Two tracks can share the exact same
# track_genre string and still sound nothing alike. get_genre_compatibility()
# can't see this — it only has text. get_track_compatibility() below adds
# audio features as a tiebreaker on top of it, so an identical tag no
# longer guarantees a 1.0 score if the tracks are sonically far apart.

# Normalization ranges taken from typical Spotify audio-feature bounds.
_FEATURE_RANGES = {
    "danceability": (0.0, 1.0),
    "energy": (0.0, 1.0),
    "acousticness": (0.0, 1.0),
    "valence": (0.0, 1.0),
    "loudness": (-40.0, 0.0),   # dB, most tracks fall in this band
    "tempo": (60.0, 200.0),     # bpm
}

# How much a track's genre tag alone is trusted vs. its acoustic signature.
# Lower this if genre tags in your dataset are known to be coarse/noisy.
_GENRE_TRUST = 0.55


def _scale(value: float, feature: str) -> float:
    lo, hi = _FEATURE_RANGES[feature]
    return max(0.0, min(1.0, (float(value) - lo) / (hi - lo)))


def audio_feature_similarity(features1: dict, features2: dict) -> float:
    """
    0.0 (opposite production style) to 1.0 (near-identical) similarity
    based on Spotify audio features. Missing features are skipped.
    """
    used = [f for f in _FEATURE_RANGES if f in features1 and f in features2]
    if not used:
        return 1.0  # no data to disagree with -> don't penalize

    diffs = [abs(_scale(features1[f], f) - _scale(features2[f], f)) for f in used]
    mean_diff = sum(diffs) / len(diffs)
    return 1.0 - mean_diff


def get_track_compatibility(
    genre1: str,
    genre2: str,
    features1: dict | None = None,
    features2: dict | None = None,
) -> float:
    """
    Full edge-weight used for graph filtering: genre_compatibility blended
    with audio-feature similarity, so a matching genre tag on two sonically
    very different tracks (e.g. Dominguinhos vs. Barões da Pisadinha, both
    tagged "forro") doesn't automatically score 1.0.
    """
    genre_score = get_genre_compatibility(genre1, genre2)

    if not features1 or not features2:
        return genre_score

    audio_score = audio_feature_similarity(features1, features2)

    # Genre sets the baseline; audio similarity pulls it up or down.
    # A perfect genre match with very different audio features settles
    # around GENRE_TRUST instead of staying pinned at 1.0.
    blended = genre_score * (1 - _GENRE_TRUST) + (genre_score * audio_score) * _GENRE_TRUST
    return round(max(0.1, min(1.0, blended)), 3)