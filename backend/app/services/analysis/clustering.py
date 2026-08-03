"""Etapa 6b del pipeline: descubrimiento de temas.

Estrategias, de mayor a menor exigencia de datos:

1. `hdbscan`   — densidad variable, deja fuera el ruido. Requiere una muestra
                 suficiente (`CLUSTERING_MIN_COMMENTS`).
2. `agglomerative` — respaldo para muestras pequeñas: número de grupos acotado
                 y umbral de distancia coseno.
3. `keyword`   — respaldo final cuando ni siquiera hay para agrupar: se agrega
                 por aspecto de la taxonomía y se marca la limitación.

Los grupos demasiado pequeños se descartan y los solapados se fusionan para
evitar decenas de temas irrelevantes.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Similitud coseno por encima de la cual dos grupos se consideran el mismo tema.
MERGE_SIMILARITY_THRESHOLD = 0.82
#: Número máximo de temas que se presentan al creador.
MAX_CLUSTERS = 14
#: Proporción mínima de la muestra que debe tener un grupo para mostrarse.
MIN_CLUSTER_SHARE = 0.015


@dataclass
class ClusterAssignment:
    """Asignación de comentarios a grupos y metadatos del algoritmo."""

    labels: list[int]
    strategy: str
    n_clusters: int
    noise_count: int
    parameters: dict[str, Any] = field(default_factory=dict)
    centroids: dict[int, np.ndarray] = field(default_factory=dict)


def _compute_centroids(vectors: np.ndarray, labels: list[int]) -> dict[int, np.ndarray]:
    groups: dict[int, list[int]] = defaultdict(list)
    for index, label in enumerate(labels):
        if label >= 0:
            groups[label].append(index)
    centroids: dict[int, np.ndarray] = {}
    for label, indices in groups.items():
        centroid = vectors[indices].mean(axis=0)
        norm = float(np.linalg.norm(centroid))
        centroids[label] = centroid / norm if norm > 0 else centroid
    return centroids


def _merge_similar(
    labels: list[int], centroids: dict[int, np.ndarray], threshold: float
) -> list[int]:
    """Fusiona grupos cuyos centroides son casi idénticos.

    Usa union-find sobre la matriz de similitud coseno, de modo que una cadena
    de grupos parecidos acaba en un único tema.
    """
    if len(centroids) < 2:
        return labels

    keys = sorted(centroids)
    matrix = np.vstack([centroids[k] for k in keys])
    similarity = cosine_similarity(matrix)

    parent = {k: k for k in keys}

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for i, key_i in enumerate(keys):
        for j in range(i + 1, len(keys)):
            if similarity[i, j] >= threshold:
                root_i, root_j = find(key_i), find(keys[j])
                if root_i != root_j:
                    parent[max(root_i, root_j)] = min(root_i, root_j)

    return [find(label) if label >= 0 else label for label in labels]


def _prune_small(labels: list[int], min_size: int) -> list[int]:
    """Convierte en ruido (-1) los grupos con menos de `min_size` miembros."""
    counts = Counter(label for label in labels if label >= 0)
    small = {label for label, count in counts.items() if count < min_size}
    return [-1 if label in small else label for label in labels]


def _limit_clusters(labels: list[int], max_clusters: int) -> list[int]:
    """Conserva sólo los `max_clusters` grupos mayores; el resto pasa a ruido."""
    counts = Counter(label for label in labels if label >= 0)
    if len(counts) <= max_clusters:
        return labels
    keep = {label for label, _ in counts.most_common(max_clusters)}
    return [label if label in keep else -1 for label in labels]


def _renumber(labels: list[int]) -> list[int]:
    """Renumera las etiquetas a 0..n-1 conservando el orden por tamaño."""
    counts = Counter(label for label in labels if label >= 0)
    order = {label: i for i, (label, _) in enumerate(counts.most_common())}
    return [order.get(label, -1) for label in labels]


def cluster_embeddings(
    vectors: np.ndarray,
    *,
    min_cluster_size: int | None = None,
    min_comments: int | None = None,
) -> ClusterAssignment:
    """Agrupa los embeddings eligiendo la estrategia adecuada al tamaño."""
    n_samples = int(vectors.shape[0]) if vectors.size else 0
    min_size = min_cluster_size or settings.clustering_min_cluster_size
    threshold = min_comments or settings.clustering_min_comments

    if n_samples == 0:
        return ClusterAssignment(labels=[], strategy="none", n_clusters=0, noise_count=0)

    if n_samples < max(min_size * 2, 8):
        # Muestra demasiado pequeña para agrupar de forma fiable.
        return ClusterAssignment(
            labels=[-1] * n_samples,
            strategy="keyword",
            n_clusters=0,
            noise_count=n_samples,
            parameters={"reason": "muestra demasiado pequeña para agrupar"},
        )

    if n_samples >= threshold:
        assignment = _hdbscan(vectors, min_size)
        if assignment is not None:
            return assignment

    return _agglomerative(vectors, min_size)


def _hdbscan(vectors: np.ndarray, min_size: int) -> ClusterAssignment | None:
    """HDBSCAN de scikit-learn (>=1.3). Devuelve `None` si no está disponible."""
    try:
        from sklearn.cluster import HDBSCAN
    except ImportError:  # pragma: no cover - depende de la versión de sklearn
        logger.info("hdbscan_unavailable", fallback="agglomerative")
        return None

    try:
        model = HDBSCAN(
            min_cluster_size=max(3, min_size),
            min_samples=max(2, min_size // 2),
            metric="euclidean",
            cluster_selection_method="eom",
        )
        raw_labels = model.fit_predict(vectors)
    except Exception as exc:  # pragma: no cover - depende de los datos
        logger.warning("hdbscan_failed", error=str(exc), fallback="agglomerative")
        return None

    labels = [int(label) for label in raw_labels]
    if all(label < 0 for label in labels):
        # Todo se consideró ruido: el respaldo aglomerativo dará más señal.
        logger.info("hdbscan_all_noise", fallback="agglomerative")
        return None

    return _finalise(
        vectors,
        labels,
        strategy="hdbscan",
        parameters={"min_cluster_size": max(3, min_size), "algorithm": "sklearn.HDBSCAN"},
        min_size=min_size,
    )


def _agglomerative(vectors: np.ndarray, min_size: int) -> ClusterAssignment:
    """Respaldo aglomerativo con umbral de distancia coseno."""
    n_samples = int(vectors.shape[0])
    n_clusters = max(2, min(MAX_CLUSTERS, n_samples // max(3, min_size)))
    try:
        model = AgglomerativeClustering(n_clusters=n_clusters, metric="cosine", linkage="average")
        raw_labels = model.fit_predict(vectors)
    except Exception as exc:  # pragma: no cover - depende de los datos
        logger.warning("agglomerative_failed", error=str(exc), fallback="keyword")
        return ClusterAssignment(
            labels=[-1] * n_samples,
            strategy="keyword",
            n_clusters=0,
            noise_count=n_samples,
            parameters={"reason": "el agrupamiento no convergió"},
        )

    labels = [int(label) for label in raw_labels]
    return _finalise(
        vectors,
        labels,
        strategy="agglomerative",
        parameters={"n_clusters": n_clusters, "metric": "cosine", "linkage": "average"},
        min_size=min_size,
    )


def _finalise(
    vectors: np.ndarray,
    labels: list[int],
    *,
    strategy: str,
    parameters: dict[str, Any],
    min_size: int,
) -> ClusterAssignment:
    """Poda, fusiona y renumera los grupos resultantes."""
    n_samples = len(labels)
    absolute_min = max(3, min(min_size, int(n_samples * MIN_CLUSTER_SHARE) or min_size))

    labels = _prune_small(labels, absolute_min)
    centroids = _compute_centroids(vectors, labels)
    labels = _merge_similar(labels, centroids, MERGE_SIMILARITY_THRESHOLD)
    labels = _prune_small(labels, absolute_min)
    labels = _limit_clusters(labels, MAX_CLUSTERS)
    labels = _renumber(labels)
    centroids = _compute_centroids(vectors, labels)

    n_clusters = len({label for label in labels if label >= 0})
    noise_count = sum(1 for label in labels if label < 0)

    if n_clusters == 0:
        strategy = "keyword"
        parameters = {**parameters, "reason": "ningún grupo superó el tamaño mínimo"}

    return ClusterAssignment(
        labels=labels,
        strategy=strategy,
        n_clusters=n_clusters,
        noise_count=noise_count,
        parameters={**parameters, "min_cluster_size_effective": absolute_min},
        centroids=centroids,
    )


__all__ = [
    "MAX_CLUSTERS",
    "MERGE_SIMILARITY_THRESHOLD",
    "MIN_CLUSTER_SHARE",
    "ClusterAssignment",
    "cluster_embeddings",
]
