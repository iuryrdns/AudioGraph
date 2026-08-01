from __future__ import annotations

import argparse
import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import librosa
import numpy as np
import requests
from pydub import AudioSegment

from .search_api import search_preview_url

DATASET_FIELDS = [
    "track_id",
    "artists",
    "album_name",
    "track_name",
    "popularity",
    "duration_ms",
    "explicit",
    "track_genre",
]

AUDIO_FEATURE_FIELDS = [
    "preview_duration_s",
    "tempo",
    "key",
    "mode",
    "loudness_db",
    "rms",
    "energy",
    "zcr",
    "spectral_centroid_hz",
    "spectral_bandwidth_hz",
    "spectral_rolloff_hz",
    "rhythmic_strength",
]

OUTPUT_FIELDS = DATASET_FIELDS + AUDIO_FEATURE_FIELDS


def load_audio(preview_url: str, sample_rate: int = 22_050) -> tuple[np.ndarray, int]:
    response = requests.get(preview_url, timeout=30)
    response.raise_for_status()
    audio_m4a = AudioSegment.from_file(
        io.BytesIO(response.content), format="m4a")
    wav_buffer = io.BytesIO()
    audio_m4a.export(wav_buffer, format="wav")
    wav_buffer.seek(0)

    waveform, sample_rate = librosa.load(wav_buffer, sr=sample_rate, mono=True)

    if waveform.size == 0:
        raise ValueError("A prévia não contém áudio.")

    return waveform, sample_rate


def estimate_key(chroma_mean: np.ndarray) -> tuple[int | None, int | None]:
    major_profile = np.array(
        [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array(
        [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    if chroma_mean.shape != (12,) or np.std(chroma_mean) < 1e-12:
        return None, None

    def correlate(chroma: np.ndarray, profile: np.ndarray) -> list[float]:
        return [float(np.corrcoef(np.roll(profile, index), chroma)[0, 1]) for index in range(12)]

    major_correlations = correlate(chroma_mean, major_profile)
    minor_correlations = correlate(chroma_mean, minor_profile)

    major_key = int(np.argmax(major_correlations))
    minor_key = int(np.argmax(minor_correlations))

    if major_correlations[major_key] > minor_correlations[minor_key]:
        return major_key, 1

    return minor_key, 0


def extract_audio_features(waveform: np.ndarray, sample_rate: int) -> dict[str, float | int | None]:
    onset_envelope = librosa.onset.onset_strength(y=waveform, sr=sample_rate)
    rhythmic_strength = float(np.mean(onset_envelope))

    tempo, _ = librosa.beat.beat_track(
        y=waveform, sr=sample_rate, onset_envelope=onset_envelope)
    tempo = float(np.atleast_1d(tempo)[0])

    rms_frames = librosa.feature.rms(y=waveform)[0]
    rms = float(np.mean(rms_frames))

    loudness_db = float(20 * np.log10(rms + 1e-9))
    energy = float(np.mean(waveform.astype(np.float64) ** 2))

    chroma = librosa.feature.chroma_cqt(y=waveform, sr=sample_rate)
    chroma_mean = np.mean(chroma, axis=1)
    key, mode = estimate_key(chroma_mean)

    zcr = float(np.mean(librosa.feature.zero_crossing_rate(y=waveform)))

    spectral_centroid = float(
        np.mean(librosa.feature.spectral_centroid(y=waveform, sr=sample_rate)))

    spectral_bandwidth = float(
        np.mean(librosa.feature.spectral_bandwidth(y=waveform, sr=sample_rate)))

    spectral_rolloff = float(
        np.mean(librosa.feature.spectral_rolloff(y=waveform, sr=sample_rate)))

    return {
        "preview_duration_s": len(waveform) / sample_rate,
        "tempo": tempo,
        "key": key,
        "mode": mode,
        "loudness_db": loudness_db,
        "rms": rms,
        "energy": energy,
        "zcr": zcr,
        "spectral_centroid_hz": spectral_centroid,
        "spectral_bandwidth_hz": spectral_bandwidth,
        "spectral_rolloff_hz": spectral_rolloff,
        "rhythmic_strength": rhythmic_strength,
    }


def process_music(dataset_row: dict) -> dict | None:
    track_name = (dataset_row.get("track_name") or "").strip()
    artists = (dataset_row.get("artists") or "").strip()

    if not track_name or not artists:
        print("Linha sem nome ou artista.")
        return None

    primary_artist = artists.split(";")[0].strip()
    preview_url = search_preview_url(primary_artist, track_name)

    if not preview_url:
        print(f"Prévia não encontrada: {artists} - {track_name}")
        return None

    try:
        waveform, sample_rate = load_audio(preview_url)
        features = extract_audio_features(waveform, sample_rate)
    except Exception as error:
        print(f"Erro ao processar {artists} - {track_name}: {error}")
        return None

    output_row = {field: dataset_row.get(field, "")
                  for field in DATASET_FIELDS}
    output_row.update(features)

    print(f"Processada: {artists} - {track_name}")
    return output_row


def process_dataset(dataset_path: Path, output_path: Path, limit: int, workers: int) -> None:
    success_count = 0
    failure_count = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with dataset_path.open(newline="", encoding="utf-8") as dataset_file:
        reader = csv.DictReader(dataset_file)
        rows = list(reader)

    if limit > 0:
        rows = rows[:limit]

    total = len(rows)

    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(
                process_music, row): row for row in rows}

            for index, future in enumerate(as_completed(futures), 1):
                output_row = future.result()

                if output_row:
                    writer.writerow(output_row)
                    success_count += 1
                else:
                    failure_count += 1

                if index % 10 == 0 or index == total:
                    output_file.flush()
                    print(f"[{index}/{total}] processadas")

    print()
    print(f"Sucessos: {success_count}")
    print(f"Falhas: {failure_count}")
    print(f"CSV gerado em: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path,
                        help="Caminho para o CSV do dataset.")
    parser.add_argument("--output", type=Path,
                        default=Path("data/features_audio.csv"))
    parser.add_argument("--limit", type=int, default=300,
                        help="Quantidade de músicas. Use 0 para todas.")
    parser.add_argument("--workers", type=int, default=8,
                        help="Threads simultaneas (busca + download em paralelo).")

    args = parser.parse_args()

    process_dataset(args.dataset, args.output, args.limit, args.workers)


if __name__ == "__main__":
    main()
