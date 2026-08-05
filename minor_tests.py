import argparse
import os
import time
from dataclasses import dataclass

import numpy as np

from src.graph.builder import get_or_build_graph
from src.graph.recommender import AdaptiveRadioRecommender

DEFAULT_DATASET_PATH = os.path.join("data", "small_spotify_tracks_dataset.csv")
DEFAULT_CACHE_PATH = os.path.join("data", "small_spotify_graph_cache.pkl")


@dataclass(frozen=True)
class TransitionMetric:
    source_id: str
    target_id: str
    similarity: float
    cost: float


@dataclass(frozen=True)
class EvaluationResult:
    sequence_ids: list[str]
    transitions: list[TransitionMetric]
    average_similarity: float
    minimum_similarity: float
    maximum_similarity: float
    average_cost: float
    diversity: float
    graph_coverage: float
    graph_density: float
    average_degree: float
    build_time_seconds: float
    recommendation_time_seconds: float
    recommendation_types: dict[str, int]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Avaliação do recomendador usando dataset small"
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default=DEFAULT_DATASET_PATH,
    )
    parser.add_argument(
        "--cache",
        type=str,
        default=DEFAULT_CACHE_PATH,
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--seed-index",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.30,
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=50,
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
    )

    return parser.parse_args()


def get_direct_similarity(
    graph,
    source_id: str,
    target_id: str,
) -> float:
    return float(graph.get_edge_weight(source_id, target_id))


def calculate_sequence_metrics(
    graph,
    sequence_ids: list[str],
) -> tuple[
    list[TransitionMetric],
    float,
    float,
    float,
    float,
]:
    transitions: list[TransitionMetric] = []

    for source_id, target_id in zip(sequence_ids, sequence_ids[1:]):
        similarity = get_direct_similarity(graph, source_id, target_id)
        cost = 1.0 - similarity

        transitions.append(
            TransitionMetric(
                source_id=source_id,
                target_id=target_id,
                similarity=similarity,
                cost=cost,
            )
        )

    if not transitions:
        return [], 0.0, 0.0, 0.0, 0.0

    similarities = np.array(
        [item.similarity for item in transitions],
        dtype=np.float64,
    )
    costs = np.array(
        [item.cost for item in transitions],
        dtype=np.float64,
    )

    return (
        transitions,
        float(np.mean(similarities)),
        float(np.min(similarities)),
        float(np.max(similarities)),
        float(np.mean(costs)),
    )


def calculate_diversity(
    graph,
    sequence_ids: list[str],
) -> float:
    if len(sequence_ids) < 2:
        return 0.0

    feature_vectors = []
    for track_id in sequence_ids:
        vector = graph.get_feature_vector(track_id)
        if vector is not None:
            feature_vectors.append(np.asarray(vector, dtype=np.float64))

    if len(feature_vectors) < 2:
        return 0.0

    distances = []
    for index, vector_a in enumerate(feature_vectors):
        for vector_b in feature_vectors[index + 1 :]:
            distance = float(np.linalg.norm(vector_a - vector_b))
            distances.append(distance)

    if not distances:
        return 0.0

    return float(np.mean(distances))


def calculate_graph_metrics(
    graph,
) -> tuple[float, float, float]:
    matrix = graph.similarity_matrix
    number_of_nodes = matrix.shape[0]
    number_of_edges = matrix.nnz

    if number_of_nodes <= 1:
        return 0.0, 0.0, 0.0

    possible_directed_edges = number_of_nodes * (number_of_nodes - 1)
    density = number_of_edges / possible_directed_edges
    average_degree = number_of_edges / number_of_nodes
    connected_nodes = np.count_nonzero(np.diff(matrix.indptr))
    coverage = connected_nodes / number_of_nodes

    return (
        float(coverage),
        float(density),
        float(average_degree),
    )


def evaluate(
    graph,
    seed_track_id: str,
    count: int,
    random_seed: int,
    build_time_seconds: float,
) -> EvaluationResult:
    recommender = AdaptiveRadioRecommender(
        graph=graph,
        history_size=max(count + 1, 15),
        exploration_prob=0.15,
        artist_boost=1.35,
        genre_boost=1.20,
        random_seed=random_seed,
    )

    recommendation_start = time.perf_counter()
    recommendations = recommender.recommend_stream(
        seed_track_id=seed_track_id,
        count=count,
    )
    recommendation_time_seconds = time.perf_counter() - recommendation_start

    sequence_ids = [
        seed_track_id,
        *[recommendation.recommended_track_id for recommendation in recommendations],
    ]

    (
        transitions,
        average_similarity,
        minimum_similarity,
        maximum_similarity,
        average_cost,
    ) = calculate_sequence_metrics(
        graph=graph,
        sequence_ids=sequence_ids,
    )

    diversity = calculate_diversity(
        graph=graph,
        sequence_ids=sequence_ids,
    )

    (
        graph_coverage,
        graph_density,
        average_degree,
    ) = calculate_graph_metrics(
        graph=graph,
    )

    recommendation_types: dict[str, int] = {}
    for recommendation in recommendations:
        recommendation_type = recommendation.recommendation_type
        recommendation_types[recommendation_type] = (
            recommendation_types.get(recommendation_type, 0) + 1
        )

    return EvaluationResult(
        sequence_ids=sequence_ids,
        transitions=transitions,
        average_similarity=average_similarity,
        minimum_similarity=minimum_similarity,
        maximum_similarity=maximum_similarity,
        average_cost=average_cost,
        diversity=diversity,
        graph_coverage=graph_coverage,
        graph_density=graph_density,
        average_degree=average_degree,
        build_time_seconds=build_time_seconds,
        recommendation_time_seconds=recommendation_time_seconds,
        recommendation_types=recommendation_types,
    )


def print_track(
    graph,
    position: int,
    track_id: str,
):
    metadata = graph.get_metadata(track_id)
    track_name = metadata.get("track_name", track_id)
    artist = metadata.get(
        "primary_artist",
        metadata.get("artists", "Unknown"),
    )
    genre = metadata.get("track_genre", "Unknown")

    print(f"{position:02d}. {track_name}")
    print(f"    Artista: {artist}")
    print(f"    Gênero : {genre}")


def print_result(
    graph,
    result: EvaluationResult,
):
    print()
    print("=" * 70)
    print("SEQUÊNCIA GERADA")
    print("=" * 70)

    for position, track_id in enumerate(result.sequence_ids, start=1):
        print_track(
            graph=graph,
            position=position,
            track_id=track_id,
        )

    print()
    print("=" * 70)
    print("SIMILARIDADE ENTRE TRANSIÇÕES")
    print("=" * 70)

    for position, transition in enumerate(result.transitions, start=1):
        source = graph.get_metadata(transition.source_id)
        target = graph.get_metadata(transition.target_id)
        source_name = source.get("track_name", transition.source_id)
        target_name = target.get("track_name", transition.target_id)

        print(f"{position:02d}. {source_name}")
        print(f"    → {target_name}")
        print(f"    Similaridade: {transition.similarity:.4f}")
        print(f"    Custo      : {transition.cost:.4f}")

    print()
    print("=" * 70)
    print("MÉTRICAS DA SEQUÊNCIA")
    print("=" * 70)
    print(f"Similaridade média : {result.average_similarity:.4f}")
    print(f"Similaridade mínima: {result.minimum_similarity:.4f}")
    print(f"Similaridade máxima: {result.maximum_similarity:.4f}")
    print(f"Custo médio        : {result.average_cost:.4f}")
    print(f"Diversidade média  : {result.diversity:.4f}")

    print()
    print("=" * 70)
    print("MÉTRICAS DO GRAFO")
    print("=" * 70)
    print(f"Cobertura de nós   : {result.graph_coverage:.2%}")
    print(f"Densidade          : {result.graph_density:.6f}")
    print(f"Grau médio         : {result.average_degree:.2f}")

    print()
    print("=" * 70)
    print("TIPOS DE RECOMENDAÇÃO")
    print("=" * 70)

    for recommendation_type, count in result.recommendation_types.items():
        print(f"{recommendation_type}: {count}")

    print()
    print("=" * 70)
    print("DESEMPENHO")
    print("=" * 70)
    print(f"Tempo de construção: {result.build_time_seconds:.4f}s")
    print(f"Tempo de recomendação: {result.recommendation_time_seconds:.4f}s")


def main():
    args = parse_args()

    if not os.path.exists(args.dataset):
        raise FileNotFoundError(f"Dataset não encontrado: {args.dataset}")

    build_start = time.perf_counter()

    graph = get_or_build_graph(
        csv_path=args.dataset,
        cache_path=args.cache,
        force_rebuild=args.rebuild,
        threshold=args.threshold,
        top_k=args.top_k,
    )

    build_time_seconds = time.perf_counter() - build_start

    if len(graph) == 0:
        raise RuntimeError("O grafo foi construído sem músicas.")

    seed_index = min(max(args.seed_index, 0), len(graph) - 1)
    seed_track_id = str(graph.idx_to_id[seed_index])

    result = evaluate(
        graph=graph,
        seed_track_id=seed_track_id,
        count=args.count,
        random_seed=args.random_seed,
        build_time_seconds=build_time_seconds,
    )

    print_result(
        graph=graph,
        result=result,
    )


if __name__ == "__main__":
    main()
