"""
AudioGraph-AI Super-Genre Taxonomy & Compatibility Module

Categorizes raw Spotify sub-genres into cohesive Super-Genre Families
and provides compatibility distance matrices for graph edge filtering.
"""

from typing import Dict

SUPER_GENRE_MAP: Dict[str, str] = {
    # 1. ACOUSTIC / INDIE / SAD / CHILL
    "acoustic": "ACOUSTIC_INDIE",
    "sad": "ACOUSTIC_INDIE",
    "indie": "ACOUSTIC_INDIE",
    "indie-pop": "ACOUSTIC_INDIE",
    "chill": "ACOUSTIC_INDIE",
    "singer-songwriter": "ACOUSTIC_INDIE",
    "songwriter": "ACOUSTIC_INDIE",
    "folk": "ACOUSTIC_INDIE",
    "bluegrass": "ACOUSTIC_INDIE",
    "guitar": "ACOUSTIC_INDIE",
    "romance": "ACOUSTIC_INDIE",
    # 2. CLASSICAL / AMBIENT / PIANO / SLEEP
    "classical": "CLASSICAL_AMBIENT",
    "ambient": "CLASSICAL_AMBIENT",
    "piano": "CLASSICAL_AMBIENT",
    "sleep": "CLASSICAL_AMBIENT",
    "study": "CLASSICAL_AMBIENT",
    "new-age": "CLASSICAL_AMBIENT",
    "opera": "CLASSICAL_AMBIENT",
    # 3. POP / DANCE-POP
    "pop": "POP",
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
    # 4. ELECTRONIC / DANCE / HOUSE / TECHNO / TRANCE
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
    # 5. ROCK / METAL / PUNK
    "rock": "ROCK_METAL",
    "alt-rock": "ROCK_METAL",
    "alternative": "ROCK_METAL",
    "hard-rock": "ROCK_METAL",
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
    # 6. HIP-HOP / R&B / SOUL / FUNK
    "hip-hop": "HIPHOP_URBAN",
    "r-n-b": "HIPHOP_URBAN",
    "soul": "HIPHOP_URBAN",
    "funk": "HIPHOP_URBAN",
    "groove": "HIPHOP_URBAN",
    # 7. REGGAE / DUB / DANCEHALL / SKA
    "reggae": "REGGAE_DUB",
    "dub": "REGGAE_DUB",
    "dancehall": "REGGAE_DUB",
    "ska": "REGGAE_DUB",
    "afrobeat": "REGGAE_DUB",
    # 8. BRAZILIAN FORRÓ / AXÉ (PISADINHA, FORRÓ ELETRÔNICO)
    "forro": "BRAZILIAN_FORRO_AXE",
    # 9. BRAZILIAN SERTANEJO (SERTANEJO UNIVERSITÁRIO & COUNTRY)
    "sertanejo": "BRAZILIAN_SERTANEJO",
    # 10. BRAZILIAN MPB / SAMBA / POP-ROCK (BARÃO VERMELHO, FREJAT, PAGODE)
    "brazil": "BRAZILIAN_MPB_SAMBA_ROCK",
    "mpb": "BRAZILIAN_MPB_SAMBA_ROCK",
    "samba": "BRAZILIAN_MPB_SAMBA_ROCK",
    "pagode": "BRAZILIAN_MPB_SAMBA_ROCK",
    # 11. SPANISH LATIN / REGGAETON / SALSA
    "latin": "SPANISH_LATIN_URBAN",
    "latino": "SPANISH_LATIN_URBAN",
    "reggaeton": "SPANISH_LATIN_URBAN",
    "salsa": "SPANISH_LATIN_URBAN",
    "tango": "SPANISH_LATIN_URBAN",
    # 12. JAZZ / BLUES / COUNTRY
    "jazz": "JAZZ_BLUES",
    "blues": "JAZZ_BLUES",
    "country": "JAZZ_BLUES",
    "honky-tonk": "JAZZ_BLUES",
    "gospel": "JAZZ_BLUES",
    # 13. WORLD / MEDIA
    "anime": "WORLD_MEDIA",
    "pop-film": "WORLD_MEDIA",
    "show-tunes": "WORLD_MEDIA",
    "disney": "WORLD_MEDIA",
    "children": "WORLD_MEDIA",
    "kids": "WORLD_MEDIA",
    "comedy": "WORLD_MEDIA",
    "indian": "WORLD_MEDIA",
    "iranian": "WORLD_MEDIA",
    "malay": "WORLD_MEDIA",
    "turkish": "WORLD_MEDIA",
    "world-music": "WORLD_MEDIA",
}


def get_super_genre(genre: str) -> str:
    """
    Returns the Super-Genre Family for a given sub-genre.
    Defaults to 'OTHER' if genre is unknown.
    """
    return SUPER_GENRE_MAP.get(str(genre).lower(), "OTHER")


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
    g1 = str(genre1).lower()
    g2 = str(genre2).lower()

    if g1 == g2:
        return 1.0

    sg1 = get_super_genre(g1)
    sg2 = get_super_genre(g2)

    if sg1 == sg2:
        return 0.85

    # Compatible adjacent Super-Genre pairs with custom affinity weights
    adjacent_pairs: Dict[tuple[str, str], float] = {
        ("ACOUSTIC_INDIE", "POP"): 0.50,
        ("ACOUSTIC_INDIE", "CLASSICAL_AMBIENT"): 0.50,
        ("ACOUSTIC_INDIE", "JAZZ_BLUES"): 0.50,
        ("POP", "ELECTRONIC_DANCE"): 0.50,
        ("POP", "HIPHOP_URBAN"): 0.50,
        ("POP", "SPANISH_LATIN_URBAN"): 0.50,
        ("ROCK_METAL", "POP"): 0.50,
        ("ROCK_METAL", "BRAZILIAN_MPB_SAMBA_ROCK"): 0.60,  # Brazilian Pop/Rock (Barão Vermelho, Frejat)
        ("HIPHOP_URBAN", "REGGAE_DUB"): 0.50,
        ("HIPHOP_URBAN", "SPANISH_LATIN_URBAN"): 0.50,
        ("BRAZILIAN_SERTANEJO", "BRAZILIAN_FORRO_AXE"): 0.40,  # Moderate Sertanejo + Forró affinity
        ("BRAZILIAN_MPB_SAMBA_ROCK", "BRAZILIAN_SERTANEJO"): 0.30,
    }

    if (sg1, sg2) in adjacent_pairs:
        return adjacent_pairs[(sg1, sg2)]
    if (sg2, sg1) in adjacent_pairs:
        return adjacent_pairs[(sg2, sg1)]

    return 0.15
