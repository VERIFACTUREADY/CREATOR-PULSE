"""La nota de calidad tiene que doler cuando los datos no acompañan.

La auditoría midió 95-97 % de calidad declarada con un 28-42 % de comentarios
sin agrupar. Estas pruebas fijan que eso ya no puede pasar, y que la nota
distingue entre «tengo muchos datos» y «he entendido lo que dicen».
"""

from __future__ import annotations

import pytest
from app.services.analysis.quality import (
    MIN_COMMENTS_FOR_TOPICS,
    DataQuality,
    finalise_quality,
)


def _muestra_grande(**overrides: object) -> DataQuality:
    """Muestra amplia y limpia: sin topes, debería puntuar alto."""
    base: dict[str, object] = {
        "videos_sampled": 12,
        "comments_sampled": 500,
        "comments_analysed": 480,
        "dominant_video_share": 0.15,
        "noise_share": 0.05,
        "cluster_coherence": 0.7,
        "mean_classifier_confidence": 0.8,
        "topics_found": 15,
        "embedding_backend": "sentence-transformers",
        "sentiment_backend": "transformers",
    }
    base.update(overrides)
    return finalise_quality(DataQuality(**base))  # type: ignore[arg-type]


# --- El hallazgo de la auditoría --------------------------------------------


def test_un_40_por_ciento_de_ruido_baja_la_nota_de_forma_visible() -> None:
    limpia = _muestra_grande(noise_share=0.05)
    ruidosa = _muestra_grande(noise_share=0.40, cluster_coherence=0.3)

    assert ruidosa.score < limpia.score
    # No es un matiz decorativo: la diferencia tiene que notarse.
    assert limpia.score - ruidosa.score >= 0.15


def test_con_mas_del_30_por_ciento_de_ruido_no_puede_ser_alta() -> None:
    calidad = _muestra_grande(noise_share=0.42, cluster_coherence=0.2)

    assert calidad.level != "alta"


def test_el_ruido_alto_con_grupos_muy_cohesionados_si_puede_ser_alta() -> None:
    """El tope se levanta con una métrica de cohesión fuerte, no por capricho."""
    calidad = _muestra_grande(noise_share=0.35, cluster_coherence=0.8)

    assert calidad.level == "alta"


# --- Topes por backend ------------------------------------------------------


def test_una_muestra_enorme_con_embeddings_hash_no_saca_nota_alta() -> None:
    """El caso exacto que producía el 96 %."""
    calidad = _muestra_grande(
        comments_analysed=2000,
        comments_sampled=2000,
        embedding_backend="hashing",
        sentiment_backend="lexicon",
    )

    assert calidad.level != "alta"
    assert any("hashing" in texto for texto in calidad.score_explanations_es)


def test_el_sentimiento_por_diccionario_penaliza_y_avisa() -> None:
    neuronal = _muestra_grande(sentiment_backend="transformers")
    lexico = _muestra_grande(sentiment_backend="lexicon")

    assert lexico.score < neuronal.score
    assert any("diccionario" in aviso for aviso in lexico.warnings_es)


def test_los_datos_buenos_con_modelos_reales_si_llegan_a_alta() -> None:
    """El tope no puede ser una condena: con buenos datos y buenos modelos, alta."""
    calidad = _muestra_grande()

    assert calidad.level == "alta"
    assert calidad.score >= 0.7


# --- Muestra pequeña --------------------------------------------------------


def test_una_muestra_pequena_se_limita() -> None:
    calidad = finalise_quality(
        DataQuality(videos_sampled=2, comments_sampled=10, comments_analysed=10)
    )

    assert calidad.level == "baja"
    assert any(str(MIN_COMMENTS_FOR_TOPICS) in texto for texto in calidad.score_explanations_es)


# --- Integridad de la muestra -----------------------------------------------


def test_una_muestra_no_ligada_a_la_ejecucion_es_un_error_no_un_aviso() -> None:
    calidad = _muestra_grande(sample_bound_to_run=False)

    assert calidad.score == 0.0
    assert calidad.level == "baja"
    assert any("ERROR" in aviso for aviso in calidad.warnings_es)
    assert any("ERROR" in texto for texto in calidad.score_explanations_es)


# --- Separación de conceptos ------------------------------------------------


def test_calidad_de_datos_y_confianza_semantica_son_distintas() -> None:
    """Muchos datos bien recogidos, pero el motor no los entiende."""
    calidad = _muestra_grande(
        comments_analysed=1500,
        comments_sampled=1500,
        noise_share=0.45,
        cluster_coherence=0.15,
        mean_classifier_confidence=0.35,
    )

    assert calidad.semantic_confidence < calidad.score
    assert calidad.semantic_confidence_level in {"baja", "media"}


def test_la_confianza_semantica_tiene_su_propio_nivel() -> None:
    calidad = _muestra_grande()

    assert calidad.semantic_confidence_level in {"baja", "media", "alta"}
    assert 0.0 <= calidad.semantic_confidence <= 1.0


# --- Transparencia ----------------------------------------------------------


def test_la_respuesta_expone_los_factores_de_la_nota() -> None:
    calidad = _muestra_grande()
    datos = calidad.to_dict()

    assert datos["score_factors"], "la API debe explicar de dónde sale la nota"
    nombres = {factor["nombre"] for factor in datos["score_factors"]}
    assert {
        "tamaño_de_muestra",
        "comentarios_agrupados",
        "cohesión_de_los_temas",
        "confianza_del_clasificador",
    } <= nombres

    for factor in datos["score_factors"]:
        assert factor["explicacion_es"], "cada factor se explica en español"
        assert 0.0 <= factor["valor"] <= 1.0


def test_los_pesos_de_los_factores_suman_uno() -> None:
    calidad = _muestra_grande()
    total = sum(factor["peso"] for factor in calidad.score_factors)

    assert total == pytest.approx(1.0)


def test_la_cohesion_no_medible_no_se_inventa() -> None:
    calidad = _muestra_grande(cluster_coherence=None)
    factor = next(f for f in calidad.score_factors if f["nombre"] == "cohesión_de_los_temas")

    assert "No se ha podido medir" in factor["explicacion_es"]
    assert calidad.to_dict()["cluster_coherence"] is None


def test_la_nota_nunca_se_sale_del_rango() -> None:
    extremos = [
        _muestra_grande(noise_share=1.0, cluster_coherence=0.0, mean_classifier_confidence=0.0),
        _muestra_grande(comments_analysed=100000, comments_sampled=100000),
        finalise_quality(DataQuality()),
    ]

    for calidad in extremos:
        assert 0.0 <= calidad.score <= 1.0
        assert 0.0 <= calidad.semantic_confidence <= 1.0
