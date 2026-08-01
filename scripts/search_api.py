from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


def search_preview_url(artist: str, music: str) -> str | None:
    params = urllib.parse.urlencode(
        {"term": f"{artist} {music}", "media": "music", "entity": "song", "limit": 1})
    url = f"{ITUNES_SEARCH_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    results = data.get("results", [])
    if not results:
        return None
    return results[0].get("previewUrl")


def download_audio(url: str, save_path: str) -> bool:
    try:
        urllib.request.urlretrieve(url, save_path)
        return True
    except (urllib.error.URLError, OSError):
        return False


def search_download(artist: str, music: str, save_path: str) -> str:
    preview_url = search_preview_url(artist, music)
    if not preview_url:
        return "not_found"
    if download_audio(preview_url, save_path):
        return "success"
    return "error"