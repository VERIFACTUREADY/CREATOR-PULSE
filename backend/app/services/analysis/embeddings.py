"""Etapa 6a del pipeline: embeddings multilingües.

Backend por defecto `hashing`: vectoriza con n-gramas de caracteres mediante
`HashingVectorizer`. Es multilingüe por construcción (no depende de un
vocabulario por idioma), determinista, no requiere descargar nada y funciona
sin conexión, lo que mantiene el sistema utilizable y las pruebas rápidas.

Backend opcional `sentence-transformers`: usa el modelo de `EMBEDDING_MODEL`
cuando el extra `ml` está instalado. Si no puede cargarse, se degrada al backend
de hashing registrando el motivo.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer
from sklearn.preprocessing import normalize

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingBackend(Protocol):
    name: str
    dimension: int

    def encode(self, texts: list[str]) -> np.ndarray: ...


class HashingEmbeddingBackend:
    """Embeddings de n-gramas de caracteres con ponderación TF-IDF.

    Se usan n-gramas de caracteres (`char_wb`, 3-5) porque capturan raíces
    compartidas entre idiomas y toleran faltas de ortografía, muy habituales en
    los comentarios.
    """

    name = "hashing-char-tfidf"

    def __init__(self, dimension: int | None = None) -> None:
        self.dimension = dimension or settings.embedding_dim
        self._vectorizer = HashingVectorizer(
            n_features=self.dimension,
            analyzer="char_wb",
            ngram_range=(3, 5),
            lowercase=True,
            norm=None,
            alternate_sign=False,
        )
        self._tfidf = TfidfTransformer(sublinear_tf=True)

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        counts = self._vectorizer.transform(texts)
        if counts.shape[0] == 1:
            # TfidfTransformer necesita más de una muestra para ser informativo.
            dense = np.asarray(counts.todense(), dtype=np.float32)
            return normalize(dense).astype(np.float32)
        weighted = self._tfidf.fit_transform(counts)
        dense = np.asarray(weighted.todense(), dtype=np.float32)
        return normalize(dense).astype(np.float32)


class SentenceTransformerBackend:
    """Backend neuronal opcional basado en `sentence-transformers`."""

    name = "sentence-transformers"

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension())
        self.name = f"sentence-transformers:{model_name}"

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        vectors = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32
        )
        return np.asarray(vectors, dtype=np.float32)


def build_embedding_backend() -> EmbeddingBackend:
    """Crea el backend configurado, degradando a hashing si no está disponible."""
    if settings.embedding_backend == "sentence-transformers":
        try:
            return SentenceTransformerBackend(settings.embedding_model)
        except Exception as exc:
            logger.warning(
                "embedding_backend_fallback",
                requested="sentence-transformers",
                error=str(exc),
                using="hashing",
            )
    return HashingEmbeddingBackend()


def resize_vector(vector: np.ndarray, target_dim: int) -> list[float]:
    """Ajusta un vector a la dimensión de la columna de la base de datos."""
    values = np.asarray(vector, dtype=np.float32).ravel()
    if values.size == target_dim:
        return [float(v) for v in values]
    if values.size > target_dim:
        return [float(v) for v in values[:target_dim]]
    padded = np.zeros(target_dim, dtype=np.float32)
    padded[: values.size] = values
    return [float(v) for v in padded]


__all__ = [
    "EmbeddingBackend",
    "HashingEmbeddingBackend",
    "SentenceTransformerBackend",
    "build_embedding_backend",
    "resize_vector",
]
