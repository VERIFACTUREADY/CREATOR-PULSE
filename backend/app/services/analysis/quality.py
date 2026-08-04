"""Calidad de los datos: qué sabe y qué no sabe el análisis.

Esta sección es la que permite al creador distinguir un patrón real de una
anécdota. Se calcula siempre, incluso cuando el análisis termina con datos
insuficientes.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

#: Umbrales que determinan la puntuación global de calidad.
GOOD_COMMENT_SAMPLE = 300
GOOD_VIDEO_SAMPLE = 10
MIN_COMMENTS_FOR_TOPICS = 30
MIN_VIDEOS_FOR_ASSOCIATION = 4


@dataclass
class DataQuality:
    """Resumen de la calidad y las limitaciones de la muestra."""

    videos_sampled: int = 0
    comments_sampled: int = 0
    comments_analysed: int = 0
    comments_discarded_spam: int = 0
    comments_discarded_duplicate: int = 0
    comments_discarded_empty: int = 0
    videos_with_comments_disabled: int = 0
    videos_with_zero_comments: int = 0
    include_replies: bool = False
    replies_incomplete: bool = False
    #: Cohesión media de los grupos (0-1). `None` si no se pudo calcular.
    cluster_coherence: float | None = None
    #: Confianza media del clasificador de sentimiento sobre la muestra.
    mean_classifier_confidence: float = 0.0
    #: `False` si la muestra no está anclada a la ejecución. Es un error, no un
    #: aviso: sin eso el análisis no es reproducible ni respeta sus límites.
    sample_bound_to_run: bool = True
    #: Confianza semántica del modelo, separada de la calidad de los datos.
    semantic_confidence: float = 0.0
    semantic_confidence_level: str = "baja"
    #: Desglose de por qué la nota es la que es.
    score_factors: list[dict[str, Any]] = field(default_factory=list)
    score_explanations_es: list[str] = field(default_factory=list)
    videos_missing_views: int = 0
    videos_missing_likes: int = 0
    sampling_strategy: str = "mixed"
    sampling_buckets: dict[str, int] = field(default_factory=dict)
    date_coverage: dict[str, Any] = field(default_factory=dict)
    language_distribution: dict[str, int] = field(default_factory=dict)
    dominant_video_share: float = 0.0
    viral_view_concentration: float = 0.0
    clustering_strategy: str = "none"
    topics_found: int = 0
    noise_share: float = 0.0
    ai_used: bool = False
    ai_provider: str = "none"
    algorithm_version: str = ""
    embedding_backend: str = ""
    sentiment_backend: str = ""
    is_demo: bool = False
    score: float = 0.0
    level: str = "baja"
    warnings_es: list[str] = field(default_factory=list)
    biases_es: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "videos_sampled": self.videos_sampled,
            "comments_sampled": self.comments_sampled,
            "comments_analysed": self.comments_analysed,
            "comments_discarded_spam": self.comments_discarded_spam,
            "comments_discarded_duplicate": self.comments_discarded_duplicate,
            "comments_discarded_empty": self.comments_discarded_empty,
            "videos_with_comments_disabled": self.videos_with_comments_disabled,
            "videos_with_zero_comments": self.videos_with_zero_comments,
            "include_replies": self.include_replies,
            "replies_incomplete": self.replies_incomplete,
            "cluster_coherence": self.cluster_coherence,
            "mean_classifier_confidence": self.mean_classifier_confidence,
            "sample_bound_to_run": self.sample_bound_to_run,
            "semantic_confidence": self.semantic_confidence,
            "semantic_confidence_level": self.semantic_confidence_level,
            "score_factors": self.score_factors,
            "score_explanations_es": self.score_explanations_es,
            "videos_missing_views": self.videos_missing_views,
            "videos_missing_likes": self.videos_missing_likes,
            "sampling_strategy": self.sampling_strategy,
            "sampling_buckets": self.sampling_buckets,
            "date_coverage": self.date_coverage,
            "language_distribution": self.language_distribution,
            "dominant_video_share": self.dominant_video_share,
            "viral_view_concentration": self.viral_view_concentration,
            "clustering_strategy": self.clustering_strategy,
            "topics_found": self.topics_found,
            "noise_share": self.noise_share,
            "ai_used": self.ai_used,
            "ai_provider": self.ai_provider,
            "algorithm_version": self.algorithm_version,
            "embedding_backend": self.embedding_backend,
            "sentiment_backend": self.sentiment_backend,
            "is_demo": self.is_demo,
            "score": self.score,
            "level": self.level,
            "warnings_es": self.warnings_es,
            "biases_es": self.biases_es,
        }


def language_distribution(languages: list[str]) -> dict[str, int]:
    counter = Counter(lang or "und" for lang in languages)
    return dict(counter.most_common())


#: Backends deterministas que funcionan sin descargar modelos. Son
#: explicables y rápidos, pero no entienden el significado como un modelo
#: neuronal, así que la nota no puede fingir que sí.
FALLBACK_EMBEDDING_BACKENDS = frozenset({"hashing"})
FALLBACK_SENTIMENT_BACKENDS = frozenset({"lexicon"})

#: Con estos backends la calidad no puede declararse «alta».
FALLBACK_SCORE_CAP = 0.69
#: Con más de este ruido no se puede pasar de «media» sin cohesión demostrada.
NOISE_CAP_THRESHOLD = 0.30
NOISE_CAP_SCORE = 0.69
#: Cohesión a partir de la cual se considera que los grupos son compactos.
STRONG_COHERENCE = 0.55
#: Por debajo de `MIN_COMMENTS_FOR_TOPICS` la nota no puede pasar de «baja».
SMALL_SAMPLE_SCORE = 0.39


def _level(score: float) -> str:
    return "alta" if score >= 0.7 else "media" if score >= 0.4 else "baja"


def _score_quality(quality: DataQuality) -> None:
    """Calcula la nota de calidad de datos y la confianza semántica.

    Son **dos cosas distintas** y antes se mezclaban: se puede tener una muestra
    grande y limpia (buena calidad de datos) analizada con un motor heurístico
    que agrupa mal (baja confianza semántica). La nota anterior sólo miraba lo
    primero, y por eso daba 95 % con un 40 % de comentarios sin agrupar.
    """
    factors: list[dict[str, Any]] = []
    explanations: list[str] = []

    def add(nombre: str, valor: float, peso: float, texto: str) -> float:
        factors.append(
            {
                "nombre": nombre,
                "valor": round(valor, 4),
                "peso": peso,
                "aportacion": round(valor * peso, 4),
                "explicacion_es": texto,
            }
        )
        return valor * peso

    # --- Calidad y cobertura de los datos ------------------------------
    comment_factor = min(1.0, quality.comments_analysed / GOOD_COMMENT_SAMPLE)
    video_factor = min(1.0, quality.videos_sampled / GOOD_VIDEO_SAMPLE)
    coverage_factor = 1.0 - min(0.6, quality.dominant_video_share)

    total_sampled = max(1, quality.comments_sampled)
    discarded = (
        quality.comments_discarded_spam
        + quality.comments_discarded_duplicate
        + quality.comments_discarded_empty
    )
    cleanliness = 1.0 - min(0.5, discarded / total_sampled)

    datos = 0.0
    datos += add(
        "tamaño_de_muestra",
        comment_factor,
        0.30,
        f"{quality.comments_analysed} comentarios analizados "
        f"(una muestra holgada son {GOOD_COMMENT_SAMPLE}).",
    )
    datos += add(
        "vídeos_analizados",
        video_factor,
        0.20,
        f"{quality.videos_sampled} vídeos (una muestra holgada son {GOOD_VIDEO_SAMPLE}).",
    )
    datos += add(
        "reparto_entre_vídeos",
        coverage_factor,
        0.10,
        f"El vídeo con más comentarios aporta el {quality.dominant_video_share:.0%} de la muestra.",
    )
    datos += add(
        "limpieza",
        cleanliness,
        0.10,
        f"{discarded} de {total_sampled} comentarios descartados por spam, duplicado o vacío.",
    )

    # --- Confianza semántica del modelo --------------------------------
    noise_factor = 1.0 - min(1.0, quality.noise_share)
    datos += add(
        "comentarios_agrupados",
        noise_factor,
        0.15,
        f"El {quality.noise_share:.0%} de los comentarios no encaja en ningún tema.",
    )

    if quality.cluster_coherence is None:
        coherence_factor = 0.5
        coherence_text = "No se ha podido medir la cohesión de los grupos."
    else:
        coherence_factor = max(0.0, min(1.0, quality.cluster_coherence))
        coherence_text = (
            f"Cohesión media de los grupos: {quality.cluster_coherence:.2f} "
            "(cuánto se parecen entre sí los comentarios de un mismo tema)."
        )
    datos += add("cohesión_de_los_temas", coherence_factor, 0.10, coherence_text)

    confidence_factor = max(0.0, min(1.0, quality.mean_classifier_confidence))
    datos += add(
        "confianza_del_clasificador",
        confidence_factor,
        0.05,
        f"Confianza media del clasificador de sentimiento: {confidence_factor:.2f}.",
    )

    score = max(0.0, min(1.0, datos))

    # --- Topes explícitos ----------------------------------------------
    embedding_fallback = quality.embedding_backend in FALLBACK_EMBEDDING_BACKENDS
    sentiment_fallback = quality.sentiment_backend in FALLBACK_SENTIMENT_BACKENDS

    if quality.comments_analysed < MIN_COMMENTS_FOR_TOPICS and score > SMALL_SAMPLE_SCORE:
        score = SMALL_SAMPLE_SCORE
        explanations.append(
            f"La nota está limitada a «baja» porque sólo se han analizado "
            f"{quality.comments_analysed} comentarios: por debajo de "
            f"{MIN_COMMENTS_FOR_TOPICS} cualquier patrón puede ser casualidad."
        )

    if embedding_fallback and score > FALLBACK_SCORE_CAP:
        score = FALLBACK_SCORE_CAP
        explanations.append(
            "La nota se limita porque los embeddings son de tipo «hashing»: agrupan por "
            "parecido de caracteres, no por significado. Con un modelo multilingüe real "
            "(EMBEDDING_BACKEND=sentence-transformers) esta limitación desaparece."
        )
    if sentiment_fallback:
        score *= 0.95
        explanations.append(
            "Penalización moderada por usar sentimiento por diccionario: es explicable y "
            "rápido, pero capta peor la ironía y el sarcasmo que un modelo neuronal."
        )

    coherencia_fuerte = (
        quality.cluster_coherence is not None and quality.cluster_coherence >= STRONG_COHERENCE
    )
    if (
        quality.noise_share > NOISE_CAP_THRESHOLD
        and not coherencia_fuerte
        and score > NOISE_CAP_SCORE
    ):
        score = NOISE_CAP_SCORE
        explanations.append(
            f"La nota no puede ser «alta» porque el {quality.noise_share:.0%} de los comentarios "
            "se queda fuera de todo tema y los grupos formados no son lo bastante compactos."
        )

    quality.score = round(max(0.0, min(1.0, score)), 3)
    quality.level = _level(quality.score)

    # La confianza semántica va aparte: mide si el motor ha entendido los
    # comentarios, no si había muchos.
    semantica = 0.45 * noise_factor + 0.35 * coherence_factor + 0.20 * confidence_factor
    if embedding_fallback:
        semantica *= 0.75
    if sentiment_fallback:
        semantica *= 0.9
    quality.semantic_confidence = round(max(0.0, min(1.0, semantica)), 3)
    quality.semantic_confidence_level = _level(quality.semantic_confidence)

    if not quality.sample_bound_to_run:
        # No es un matiz: sin muestra anclada el análisis no es reproducible ni
        # respeta sus propios límites, así que la nota no significa nada.
        quality.score = 0.0
        quality.level = "baja"
        quality.semantic_confidence = 0.0
        quality.semantic_confidence_level = "baja"
        explanations.append(
            "ERROR: la muestra de comentarios no está asociada a esta ejecución, así que no "
            "se puede garantizar qué se ha analizado. La nota se fija en cero a propósito."
        )

    quality.score_factors = factors
    quality.score_explanations_es = explanations


def finalise_quality(quality: DataQuality) -> DataQuality:
    """Calcula la puntuación global y redacta avisos y sesgos en español."""
    warnings: list[str] = []
    biases: list[str] = []

    _score_quality(quality)

    # --- Avisos --------------------------------------------------------
    if quality.comments_analysed < MIN_COMMENTS_FOR_TOPICS:
        warnings.append(
            f"Sólo se han podido analizar {quality.comments_analysed} comentarios. "
            "Los temas detectados son orientativos y no deben tomarse como un patrón del canal."
        )
    if quality.videos_sampled < MIN_VIDEOS_FOR_ASSOCIATION:
        warnings.append(
            f"Se han analizado {quality.videos_sampled} vídeos. Con tan pocos vídeos no se "
            "pueden asociar temas con el rendimiento de forma fiable."
        )
    if quality.videos_with_comments_disabled:
        warnings.append(
            f"{quality.videos_with_comments_disabled} vídeo(s) tienen los comentarios "
            "desactivados y no aportan feedback."
        )
    if quality.videos_with_zero_comments:
        warnings.append(
            f"{quality.videos_with_zero_comments} vídeo(s) no tienen comentarios públicos."
        )
    if quality.videos_missing_views:
        warnings.append(
            f"{quality.videos_missing_views} vídeo(s) no exponen sus visualizaciones públicas."
        )
    if quality.include_replies and quality.replies_incomplete:
        warnings.append(
            "Algunas conversaciones no se han descargado enteras: se alcanzó el límite de "
            "comentarios o la API falló al pedir las respuestas. Los hilos largos pueden "
            "aparecer incompletos."
        )
    if quality.clustering_strategy == "keyword":
        warnings.append(
            "No había muestra suficiente para agrupar comentarios por significado. "
            "Los temas se han agregado por palabras clave y aspectos."
        )
    if quality.noise_share > NOISE_CAP_THRESHOLD and quality.topics_found > 0:
        warnings.append(
            f"El {quality.noise_share:.0%} de los comentarios no encaja en ningún tema claro. "
            "Los temas detectados describen sólo una parte de lo que dice tu audiencia."
        )
    if quality.embedding_backend in FALLBACK_EMBEDDING_BACKENDS:
        warnings.append(
            "Los temas se agrupan con embeddings «hashing», que comparan parecido de "
            "caracteres y no significado. Sirven para detectar patrones repetidos, pero "
            "confunden expresiones distintas que quieren decir lo mismo."
        )
    if quality.sentiment_backend in FALLBACK_SENTIMENT_BACKENDS:
        warnings.append(
            "El sentimiento se calcula con diccionarios. Es explicable y no depende de "
            "ningún servicio externo, pero se le escapan la ironía y el sarcasmo."
        )
    if not quality.sample_bound_to_run:
        warnings.append(
            "ERROR: no se ha podido determinar qué comentarios analizó esta ejecución. "
            "No uses estos resultados: vuelve a lanzar el análisis."
        )

    # --- Sesgos --------------------------------------------------------
    if quality.dominant_video_share >= 0.5:
        biases.append(
            f"El {quality.dominant_video_share:.0%} de los comentarios analizados procede de un "
            "solo vídeo, así que la muestra refleja sobre todo la reacción a ese vídeo."
        )
    if quality.viral_view_concentration >= 0.5:
        biases.append(
            f"Un único vídeo concentra el {quality.viral_view_concentration:.0%} de las "
            "visualizaciones. Las medianas del canal están dominadas por ese vídeo."
        )
    if quality.sampling_strategy == "relevant":
        biases.append(
            "La muestra prioriza los comentarios más votados, que suelen ser más positivos "
            "y más antiguos que el conjunto real."
        )
    if quality.sampling_strategy == "recent":
        biases.append(
            "La muestra prioriza los comentarios recientes, así que refleja mejor la reacción "
            "a los últimos vídeos que la opinión histórica de la audiencia."
        )
    if quality.sampling_strategy == "mixed":
        biases.append(
            "La muestra combina comentarios recientes y populares. Aun así, no es una muestra "
            "aleatoria de todos los comentarios del canal."
        )
    languages = quality.language_distribution
    if languages:
        total_langs = sum(languages.values())
        top_lang, top_count = next(iter(languages.items()))
        if total_langs and top_count / total_langs < 0.6:
            biases.append(
                "Los comentarios están repartidos entre varios idiomas, lo que puede reducir "
                "la precisión de la clasificación de sentimiento."
            )
        if top_lang == "und" and top_count / max(1, total_langs) > 0.3:
            biases.append(
                "Una parte importante de los comentarios es demasiado corta para detectar "
                "su idioma con fiabilidad."
            )
    span = quality.date_coverage.get("span_days")
    if isinstance(span, (int, float)) and span < 7:
        biases.append(
            "Todos los comentarios analizados son de un periodo muy corto: no se puede "
            "distinguir una tendencia de una reacción puntual."
        )
    if quality.is_demo:
        biases.append(
            "Estos son datos de demostración generados para probar el producto. "
            "No corresponden a ningún canal real."
        )

    quality.warnings_es = warnings
    quality.biases_es = biases
    return quality


__all__ = [
    "GOOD_COMMENT_SAMPLE",
    "GOOD_VIDEO_SAMPLE",
    "MIN_COMMENTS_FOR_TOPICS",
    "MIN_VIDEOS_FOR_ASSOCIATION",
    "DataQuality",
    "finalise_quality",
    "language_distribution",
]
