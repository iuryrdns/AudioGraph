import argparse
import csv
import os
import random
import time
from dataclasses import dataclass

import numpy as np

from src.graph.builder import get_or_build_graph
from src.graph.recommender import AdaptiveRadioRecommender

DEFAULT_DATASET_PATH = os.path.join("data", "small_spotify_tracks_dataset.csv")
DEFAULT_CACHE_PATH = os.path.join("data", "small_spotify_graph_cache.pkl")
DEFAULT_OUTPUT_CSV = os.path.join("data", "evaluation_results.csv")


@dataclass(frozen=True)
class TransitionMetric:
    source_id: str
    target_id: str
    similarity: float
    cost: float


@dataclass(frozen=True)
class EvaluationResult:
    seed_index: int
    seed_track_id: str
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
        description="Avaliação do recomendador gerando múltiplas amostras para análise."
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
        help="Quantidade de recomendações por sequência",
    )
    parser.add_argument(
        "--seed-index",
        type=int,
        default=0,
        help="Índice inicial da música semente",
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
    parser.add_argument(
        "--output-csv",
        type=str,
        default=DEFAULT_OUTPUT_CSV,
        help="Caminho do arquivo CSV onde os resultados serão salvos.",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=50,
        help="Quantidade de amostras/rodadas a serem geradas e salvas no CSV.",
    )
    parser.add_argument(
        "--sample-mode",
        type=str,
        choices=["random", "range"],
        default="random",
        help="Modo de escolha das seeds: 'random' (sorteia músicas) ou 'range' (sequencial).",
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
    seed_index: int,
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
        seed_index=seed_index,
        seed_track_id=seed_track_id,
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


def export_to_csv(result: EvaluationResult, args, output_csv_path: str, current_seed: int):
    dirname = os.path.dirname(output_csv_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    file_exists = os.path.exists(output_csv_path)

    fieldnames = [
        "timestamp",
        "random_seed",
        "threshold",
        "top_k",
        "requested_count",
        "seed_index",
        "seed_track_id",
        "sequence_len",
        "average_similarity",
        "minimum_similarity",
        "maximum_similarity",
        "average_cost",
        "diversity",
        "graph_coverage",
        "graph_density",
        "average_degree",
        "build_time_seconds",
        "recommendation_time_seconds",
        "recommendation_types",
    ]

    row_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "random_seed": current_seed,
        "threshold": args.threshold,
        "top_k": args.top_k,
        "requested_count": args.count,
        "seed_index": result.seed_index,
        "seed_track_id": result.seed_track_id,
        "sequence_len": len(result.sequence_ids),
        "average_similarity": round(result.average_similarity, 6),
        "minimum_similarity": round(result.minimum_similarity, 6),
        "maximum_similarity": round(result.maximum_similarity, 6),
        "average_cost": round(result.average_cost, 6),
        "diversity": round(result.diversity, 6),
        "graph_coverage": round(result.graph_coverage, 6),
        "graph_density": round(result.graph_density, 6),
        "average_degree": round(result.average_degree, 6),
        "build_time_seconds": round(result.build_time_seconds, 6),
        "recommendation_time_seconds": round(result.recommendation_time_seconds, 6),
        "recommendation_types": str(result.recommendation_types),
    }

    with open(output_csv_path, mode="a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row_data)


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

    total_nodes = len(graph)
    if total_nodes == 0:
        raise RuntimeError("O grafo foi construído sem músicas.")

    print(f"Grafo pronto com {total_nodes} nós.")
    print(f"Gerando {args.num_samples} amostra(s) de recomendação...\n")

    random.seed(args.random_seed)

    for i in range(args.num_samples):
        if args.sample_mode == "random":
            seed_index = random.randint(0, total_nodes - 1)
        else:
            seed_index = (args.seed_index + i) % total_nodes

        seed_track_id = str(graph.idx_to_id[seed_index])
        
        current_run_seed = args.random_seed + i

        result = evaluate(
            graph=graph,
            seed_index=seed_index,
            seed_track_id=seed_track_id,
            count=args.count,
            random_seed=current_run_seed,
            build_time_seconds=build_time_seconds,
        )

        export_to_csv(
            result=result,
            args=args,
            output_csv_path=args.output_csv,
            current_seed=current_run_seed,
        )

        print(
            f"[{i + 1:03d}/{args.num_samples:03d}] Seed #{seed_index} -> "
            f"Sim. Média: {result.average_similarity:.4f} | "
            f"Diversidade: {result.diversity:.4f} | "
            f"Tempo: {result.recommendation_time_seconds*1000:.2f}ms"
        )

    print(f"\n[CSV] {args.num_samples} amostra(s) salvas com sucesso em: {args.output_csv}")


if __name__ == "__main__":
    main()