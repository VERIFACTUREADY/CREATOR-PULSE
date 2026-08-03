#!/usr/bin/env python3
"""Genera los ficheros de datos de demostración en `fixtures/`.

Los datos son **ficticios**: no corresponden a ningún canal real de YouTube.
El generador es determinista (semilla fija), de modo que volver a ejecutarlo
produce exactamente los mismos ficheros.

Uso:
    python scripts/generate_fixtures.py
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SEED = 20240517
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "fixtures"
#: Fecha de referencia. Las fechas se generan como desplazamientos negativos
#: respecto a ella y el cargador las reancla al momento de la carga.
REFERENCE = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _thumb(seed: str, size: str = "hq") -> str:
    digest = hashlib.md5(seed.encode(), usedforsecurity=False).hexdigest()[:11]
    return f"https://demo.creator-signal.local/thumbs/{size}/{digest}.jpg"


# ---------------------------------------------------------------------------
# Bancos de comentarios por tema
# ---------------------------------------------------------------------------

CommentBank = dict[str, list[str]]

BEAUTY_BANK: CommentBank = {
    "praise_eyes": [
        "Tus ojos se ven increíbles en este vídeo, ¿qué haces?",
        "Madre mía la mirada, se te ven los ojos enormes 😍",
        "Vengo por los ojos, me encanta cómo te quedan",
        "Nunca había visto unos ojos así en cámara, brutal",
        "Los ojos son lo mejor del vídeo sin duda ❤️",
        "Your eyes look amazing here, what mascara is that?",
        "Cada vídeo tus ojos destacan más, es espectacular",
        "Me encanta el delineado, los ojos quedan preciosos",
    ],
    "request_tutorial": [
        "Haz un tutorial paso a paso de este maquillaje porfa",
        "Necesitamos tutorial de ojos para principiantes 🙏",
        "¿Puedes hacer un vídeo explicando cómo consigues ese efecto?",
        "Tutorial de delineado desde cero por favor",
        "Please make a beginner tutorial for this look",
        "Enséñanos paso a paso cómo lo haces, va muy rápido",
        "Un vídeo solo de cómo iluminar los ojos, te lo pido",
        "¿Tutorial de la rutina completa? Sería genial",
    ],
    "criticism_audio": [
        "La música está muy alta, no se escucha bien tu voz",
        "No se te oye cuando hablas bajito, sube el micro",
        "El audio se escucha con eco en esta parte",
        "Baja la música de fondo porfa, tapa lo que dices",
        "Can't hear you over the background music",
        "El sonido va mal, se corta a ratos",
        "La voz se escucha muy bajo comparado con la música",
    ],
    "praise_authenticity": [
        "Me gusta que seas tan natural y sincera",
        "Gracias por ser honesta con los productos que no funcionan",
        "Eres de las pocas que dice la verdad, se agradece",
        "Tu autenticidad es lo que me hizo suscribirme",
        "So refreshing to see someone honest about products",
    ],
    "request_product": [
        "¿Qué marca es la base que usas? Déjanos el enlace",
        "Enlace del producto porfa 🙏",
        "¿Dónde compro esa paleta? No la encuentro",
        "What camera do you use? The quality is great",
        "¿Cuál es la referencia exacta del labial?",
        "Link please de la crema que enseñas al principio",
    ],
    "question_routine": [
        "¿Cuánto tiempo tardas en hacerte esto por la mañana?",
        "¿Esto sirve para piel grasa?",
        "¿Cada cuánto repites la rutina?",
        "Does this work for sensitive skin?",
        "¿Se puede hacer sin los productos caros?",
    ],
    "trend_night_routine": [
        "Me encanta la rutina de noche, más contenido así",
        "La rutina nocturna me ha cambiado la piel, gracias",
        "Más vídeos de rutina de noche porfa",
        "La parte de la rutina de noche es la mejor",
        "Necesito una rutina de noche completa en vídeo",
        "Night routine content is the best, keep going",
    ],
    "neutral": [
        "Primera 🙋",
        "Vengo del short",
        "2024 y sigo aquí",
        "Ok",
        "Visto",
        "👀",
    ],
    "toxic": [
        "Qué fea te ves con ese maquillaje, deja YouTube",
        "Eres ridícula, nadie te quiere ver",
    ],
    "spam": [
        "SUSCRÍBETE A MI CANAL y te devuelvo el sub sub4sub",
        "Gana dinero rápido aquí t.me/oferta2024",
    ],
}

GAMING_BANK: CommentBank = {
    "praise_humor": [
        "Me he reído todo el vídeo, eres un crack 😂",
        "El humor de este canal no lo tiene nadie",
        "Llevo 10 minutos con carcajadas, gracias",
        "Tus comentarios mientras juegas son lo mejor",
        "Your commentary is hilarious, best gaming channel",
        "Me duele la barriga de reír 😂😂",
        "La forma en que reaccionas es oro puro",
        "Vengo solo por el humor, el juego me da igual",
        "Qué gracioso eres tío, no fallas",
    ],
    "criticism_length": [
        "El vídeo se hace muy largo, se podría cortar más",
        "Demasiado largo, con 15 minutos sobraba",
        "Sobran los 10 primeros minutos de intro",
        "Too long, the pacing drags in the middle",
        "Podrías editar más, hay muchos tiempos muertos",
        "El ritmo baja mucho a mitad del vídeo",
    ],
    "criticism_audio": [
        "El micro suena metálico en esta partida",
        "Se escucha el juego más alto que tu voz",
        "No se te oye cuando gritas, satura el audio",
        "Audio balance is off, game is way louder",
    ],
    "request_series": [
        "Haz una serie completa de este juego porfa",
        "Segunda parte ya, no me dejes así",
        "Parte 2 por favor 🙏",
        "Necesitamos una serie entera, no un vídeo suelto",
        "Please make this a full series",
        "Continúa la partida, quiero ver el final",
        "Más capítulos de esto, es lo mejor del canal",
    ],
    "request_tutorial": [
        "¿Cómo haces ese truco? Tutorial porfa",
        "Explica paso a paso cómo configuras el mando",
        "Tutorial de cómo llegas a ese nivel tan rápido",
        "How do you do that combo? Teach us",
    ],
    "question_setup": [
        "¿Qué PC tienes? ¿A cuántos FPS grabas?",
        "¿Con qué programa editas?",
        "¿Qué mando usas?",
        "What settings do you play on?",
        "¿Juegas con teclado o mando?",
    ],
    "praise_skill": [
        "Qué nivel tienes, impresionante",
        "Eres el mejor jugando a esto, sin discusión",
        "Nunca había visto a alguien jugar así",
    ],
    "neutral": [
        "Primero",
        "Aquí antes de que llegue a 1M",
        "gg",
        "🔥🔥",
        "Vengo del directo",
        "Ok siguiente",
    ],
    "toxic": [
        "Eres malísimo jugando, patético",
        "Cállate ya idiota, das vergüenza",
        "Deja YouTube, no vales para esto",
    ],
    "spam": [
        "Mira mi canal, subo lo mismo pero mejor",
        "REGALO SKINS GRATIS bit.ly/skins",
    ],
}

TECH_BANK: CommentBank = {
    "praise_clarity": [
        "Lo has explicado clarísimo, por fin lo entiendo",
        "La mejor explicación que he visto de esto",
        "Gracias, llevaba semanas sin entenderlo y contigo en 10 minutos",
        "Explicas con una claridad increíble",
        "Clearest explanation on YouTube, thank you",
        "Se entiende todo perfectamente, gracias de verdad",
        "Por fin alguien que lo explica bien y sin rodeos",
        "Qué bien estructurado está el vídeo",
    ],
    "praise_expertise": [
        "Se nota que sabes mucho del tema",
        "El nivel de detalle es impresionante, muy documentado",
        "Aprendí más aquí que en un curso de pago",
        "Contenido educativo del bueno, gracias",
        "I learned more here than in my university class",
        "Qué bien documentado está todo",
    ],
    "criticism_pace": [
        "Vas demasiado rápido, tuve que poner 0.75x",
        "El ritmo es muy acelerado para principiantes",
        "Podrías ir más despacio en la parte del código",
        "Too fast for beginners, slow down please",
        "Se te va la explicación muy rápido a partir del minuto 8",
        "Muy rápido, no da tiempo a leer el código",
    ],
    "request_beginner": [
        "Haz un vídeo desde cero para principiantes porfa",
        "Necesitamos un tutorial para novatos de esto",
        "¿Puedes hacer una versión para gente que empieza?",
        "Please make a beginner version of this",
        "Un curso desde cero sería increíble",
        "Tutorial paso a paso para los que empezamos 🙏",
        "Vídeo para principiantes por favor, me pierdo",
    ],
    "question_repeated": [
        "¿Esto funciona también en Windows?",
        "¿Sirve para la versión nueva?",
        "¿Hay alguna alternativa gratuita?",
        "Does this work on Mac too?",
        "¿Se puede hacer sin instalar nada?",
        "¿Esto sigue siendo válido en 2024?",
    ],
    "request_product": [
        "¿Qué micrófono usas? Se escucha muy bien",
        "¿Dónde puedo ver el código completo?",
        "Enlace al repositorio porfa",
        "What editor theme is that?",
    ],
    "criticism_editing": [
        "Los cortes son muy bruscos, marean un poco",
        "La letra del código se ve muy pequeña",
        "El zoom del código llega tarde",
    ],
    "neutral": [
        "Guardado para verlo luego",
        "Comento para el algoritmo",
        "👍",
        "Buenas",
        "Aquí antes de los 100k",
    ],
    "toxic": [
        "Menuda tontería de vídeo, no sabes nada",
    ],
    "spam": [
        "Curso completo gratis en mi perfil, entra ya",
    ],
}


# ---------------------------------------------------------------------------
# Definición de canales
# ---------------------------------------------------------------------------

CHANNELS: list[dict[str, Any]] = [
    {
        "youtube_channel_id": "UCdemoBEAUTY0000000000a",
        "handle": "luciaglowdemo",
        "title": "Lucía Glow (demo)",
        "description": (
            "Canal ficticio de belleza y estilo de vida creado para probar Creator Signal AI. "
            "Rutinas, maquillaje y cuidado de la piel sin filtros."
        ),
        "subscriber_count": 84_300,
        "subscriber_count_hidden": False,
        "video_count": 148,
        "view_count": 6_240_000,
        "country": "ES",
        "bank": BEAUTY_BANK,
        "base_views": 42_000,
        "video_titles": [
            ("Mi rutina de noche completa (paso a paso)", "trend_night_routine"),
            ("5 errores de maquillaje que yo también cometía", "praise_eyes"),
            ("Delineado fácil para ojos pequeños", "praise_eyes"),
            ("Probando la crema viral de 12€", "praise_authenticity"),
            ("Rutina de noche cuando llego agotada", "trend_night_routine"),
            ("Mi base de maquillaje favorita del año", "request_product"),
            ("Maquillaje de día en 7 minutos", "request_tutorial"),
            ("Lo que nadie te cuenta del contorno", "praise_authenticity"),
            ("Rutina de noche minimalista (3 productos)", "trend_night_routine"),
            ("Reacciono a mis vídeos de hace 3 años", "neutral"),
            ("Cómo hago que mis ojos destaquen en cámara", "praise_eyes"),
            ("Skincare de invierno: lo que sí funciona", "question_routine"),
        ],
        "viral_index": 10,
        "comments_disabled_index": 9,
    },
    {
        "youtube_channel_id": "UCdemoGAMING0000000000b",
        "handle": "pixelraptordemo",
        "title": "PixelRaptor (demo)",
        "description": (
            "Canal ficticio de gaming creado para probar Creator Signal AI. "
            "Partidas comentadas, retos imposibles y mucho humor."
        ),
        "subscriber_count": None,
        "subscriber_count_hidden": True,
        "video_count": 312,
        "view_count": 18_900_000,
        "country": "MX",
        "bank": GAMING_BANK,
        "base_views": 96_000,
        "video_titles": [
            ("Intento pasarme el juego sin recibir daño", "praise_humor"),
            ("El reto más absurdo que he hecho nunca", "praise_humor"),
            ("Jugando el peor juego de la historia", "criticism_length"),
            ("Serie nueva: empezamos la campaña", "request_series"),
            ("Capítulo 2: esto se complica", "request_series"),
            ("Reaccionando a mis peores partidas", "praise_humor"),
            ("Speedrun a las 3 de la mañana", "criticism_audio"),
            ("Mi setup completo de grabación", "question_setup"),
            ("Capítulo 3: el jefe final", "request_series"),
            ("24 horas jugando sin parar", "criticism_length"),
            ("El truco que nadie conoce", "request_tutorial"),
            ("Partida con subs, caos absoluto", "praise_humor"),
            ("Analizo por qué este juego fracasó", "praise_skill"),
        ],
        "viral_index": 1,
        "comments_disabled_index": 7,
    },
    {
        "youtube_channel_id": "UCdemoTECH00000000000c",
        "handle": "codigoclarodemo",
        "title": "Código Claro (demo)",
        "description": (
            "Canal ficticio de tecnología y programación creado para probar Creator Signal AI. "
            "Explicaciones claras de conceptos difíciles."
        ),
        "subscriber_count": 27_800,
        "subscriber_count_hidden": False,
        "video_count": 96,
        "view_count": 1_420_000,
        "country": "AR",
        "bank": TECH_BANK,
        "base_views": 15_500,
        "video_titles": [
            ("Qué es una base de datos vectorial (explicado fácil)", "praise_clarity"),
            ("Entiende los embeddings en 12 minutos", "praise_clarity"),
            ("Docker desde cero: lo mínimo que necesitas", "request_beginner"),
            ("Por qué tu API es lenta (y cómo arreglarlo)", "praise_expertise"),
            ("Git: los 8 comandos que uso a diario", "request_beginner"),
            ("Cómo funciona realmente HTTPS", "praise_expertise"),
            ("Mi setup de desarrollo en 2024", "request_product"),
            ("Errores típicos al aprender a programar", "criticism_pace"),
            ("SQL vs NoSQL: cuándo usar cada uno", "question_repeated"),
            ("Explicando el algoritmo de ordenación más rápido", "criticism_pace"),
            ("Tu primer proyecto: paso a paso", "request_beginner"),
            ("Cómo leer documentación técnica sin morir", "praise_clarity"),
        ],
        "viral_index": 1,
        "comments_disabled_index": 6,
    },
]


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------


def _mix_for_video(
    bank: CommentBank, focus: str, position: int, total: int, rng: random.Random
) -> list[tuple[str, str]]:
    """Devuelve pares `(bucket, texto)` para un vídeo.

    `position` es 0 para el vídeo más antiguo. La proporción de algunos temas
    varía con la posición para crear tendencias reales que el pipeline pueda
    detectar (no se inyecta ninguna tendencia en los resultados: se inyecta en
    los datos y el análisis la descubre).
    """
    recency = position / max(1, total - 1)
    weights: dict[str, float] = {}

    for bucket in bank:
        if bucket == "neutral":
            weights[bucket] = 0.18
        elif bucket == "toxic":
            # El acoso crece ligeramente en los vídeos recientes.
            weights[bucket] = 0.01 + 0.05 * recency
        elif bucket == "spam":
            weights[bucket] = 0.02
        else:
            weights[bucket] = 0.07

    weights[focus] = weights.get(focus, 0.07) + 0.34

    # Tendencias explícitas por canal.
    if "trend_night_routine" in bank:
        weights["trend_night_routine"] = 0.02 + 0.28 * recency
        weights["criticism_audio"] = 0.16 * (1.0 - recency) + 0.03
    if "request_series" in bank:
        weights["request_series"] = 0.04 + 0.22 * recency
        weights["criticism_length"] = 0.06 + 0.16 * recency
    if "request_beginner" in bank:
        weights["request_beginner"] = 0.05 + 0.25 * recency
        weights["criticism_pace"] = 0.05 + 0.18 * recency

    buckets = list(weights)
    probabilities = [weights[b] for b in buckets]

    count = rng.randint(28, 52)
    out: list[tuple[str, str]] = []
    for _ in range(count):
        bucket = rng.choices(buckets, weights=probabilities, k=1)[0]
        text = rng.choice(bank[bucket])
        out.append((bucket, text))
    return out


#: Aperturas y cierres que se combinan con las plantillas para que los
#: comentarios no se repitan literalmente, igual que ocurre en un canal real.
_PREFIXES: tuple[str, ...] = (
    "", "", "", "",
    "Hola, ", "Buenas, ", "Llevo tiempo viéndote y ", "Acabo de descubrir el canal y ",
    "Vengo del short y ", "Sinceramente, ", "La verdad es que ", "Solo quería decir que ",
    "Después de ver el vídeo entero, ", "Mira, ", "Oye, ", "Perdona si ya lo has dicho pero ",
    "Hi, ", "Just wanted to say ", "Been watching for a while and ",
)

_SUFFIXES: tuple[str, ...] = (
    "", "", "", "", "",
    " Un saludo desde México.", " Saludos desde Argentina.", " Saludos desde España.",
    " Gracias por el contenido.", " Sigue así.", " Espero que lo leas.",
    " Es mi opinión, sin más.", " Lo digo con buena intención.",
    " Llevo suscrito desde el principio.", " Perdón por el tocho.",
    " Greetings from the UK.", " Keep it up.",
)


#: Buckets cuyo tono es negativo: no deben decorarse con emojis ni despedidas
#: positivas, o el texto dejaría de parecerse a una crítica real.
_NEGATIVE_BUCKETS = frozenset(
    {
        "criticism_audio",
        "criticism_length",
        "criticism_pace",
        "criticism_editing",
        "toxic",
    }
)

_NEGATIVE_EMOJIS: tuple[str, ...] = ("😕", "🙄", "😴", "👎", "😐")

_NEUTRAL_SUFFIXES: tuple[str, ...] = (
    "", "", "", "",
    " Lo digo con buena intención.", " Es solo una sugerencia.",
    " Por lo demás el vídeo está bien.", " Espero que se pueda arreglar.",
    " No te lo tomes a mal.",
)


def _decorate(text: str, rng: random.Random, bucket: str = "") -> str:
    """Compone y varía el comentario para que no haya repeticiones literales.

    Los comentarios reales rara vez son idénticos entre sí, así que se combinan
    aperturas, cierres, emojis, mayúsculas y erratas. Esto evita que el paso de
    deduplicación descarte la muestra por copia-pega. Los comentarios negativos
    reciben decoraciones acordes a su tono para que el sentimiento del texto
    generado sea coherente con su categoría.
    """
    negative = bucket in _NEGATIVE_BUCKETS
    prefix = rng.choice(_PREFIXES)
    suffix = rng.choice(_NEUTRAL_SUFFIXES if negative else _SUFFIXES)

    core = text
    if prefix and core and core[0].isupper() and not core.startswith("¿"):
        core = core[0].lower() + core[1:]

    result = f"{prefix}{core}{suffix}"

    roll = rng.random()
    if roll < 0.08:
        result = result.upper()
    elif roll < 0.20:
        result = result.lower()
    if rng.random() < 0.25:
        result += " " + rng.choice(
            _NEGATIVE_EMOJIS
            if negative
            else ("❤️", "😍", "🔥", "😂", "🙏", "👏", "💪", "👍", "✨")
        )
    if rng.random() < 0.10:
        # Erratas típicas de escritura rápida en móvil.
        result = result.replace("que", "ke", 1)
    if rng.random() < 0.06:
        result += "!!!"
    if rng.random() < 0.05:
        result = result.replace(" ", "  ", 1)
    return result


def build_channel(spec: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    total_videos = len(spec["video_titles"])
    videos: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []

    for index, (title, focus) in enumerate(spec["video_titles"]):
        # El vídeo 0 es el más antiguo.
        days_ago = (total_videos - index) * rng.randint(6, 11)
        published = REFERENCE - timedelta(days=days_ago, hours=rng.randint(0, 20))
        video_id = f"demo{spec['handle'][:4]}{index:02d}v"[:11].ljust(11, "x")

        is_viral = index == spec["viral_index"]
        comments_disabled = index == spec["comments_disabled_index"]

        base = spec["base_views"]
        views = int(base * rng.uniform(0.55, 1.5))
        if is_viral:
            views = int(base * rng.uniform(11.0, 15.0))

        like_rate = rng.uniform(0.035, 0.062)
        likes = int(views * like_rate)

        video_comments: list[dict[str, Any]] = []
        if not comments_disabled:
            pairs = _mix_for_video(spec["bank"], focus, index, total_videos, rng)
            if is_viral:
                # Un vídeo viral concentra muchos más comentarios.
                pairs = pairs * 4
            for order, (bucket, text) in enumerate(pairs):
                offset_hours = rng.uniform(0.5, min(24 * 30, days_ago * 24 * 0.85))
                published_at = published + timedelta(hours=offset_hours)
                video_comments.append(
                    {
                        "youtube_comment_id": f"Ugz{video_id}{order:04d}",
                        "text": _decorate(text, rng, bucket),
                        "published_at": published_at.isoformat(),
                        "like_count": max(0, int(rng.expovariate(1 / 6.0))),
                        "reply_count": rng.choice([0, 0, 0, 1, 2]),
                        "is_top_level": True,
                        "author_seed": f"{spec['handle']}-author-{rng.randint(1, 900)}",
                        "bucket": bucket,
                        "sampling_bucket": "recent" if order % 2 == 0 else "relevant",
                    }
                )

        videos.append(
            {
                "youtube_video_id": video_id,
                "title": title,
                "description": (
                    f"Vídeo de demostración del canal ficticio {spec['title']}. "
                    "Este contenido no existe en YouTube."
                ),
                "published_at": published.isoformat(),
                "thumbnail_url": _thumb(video_id),
                "duration_seconds": rng.randint(180, 1500),
                "view_count": views,
                "like_count": likes,
                "comment_count": None if comments_disabled else len(video_comments),
                "tags": ["demo", spec["handle"]],
                "category_id": "22",
                "is_live_content": False,
                "live_broadcast_content": "none",
                "comments_disabled": comments_disabled,
            }
        )
        comments.extend({**c, "video_id": video_id} for c in video_comments)

    return {
        "channel": {
            "youtube_channel_id": spec["youtube_channel_id"],
            "handle": spec["handle"],
            "title": spec["title"],
            "description": spec["description"],
            "thumbnail_url": _thumb(spec["youtube_channel_id"], "channel"),
            "subscriber_count": spec["subscriber_count"],
            "subscriber_count_hidden": spec["subscriber_count_hidden"],
            "video_count": spec["video_count"],
            "view_count": spec["view_count"],
            "country": spec["country"],
            "published_at": (REFERENCE - timedelta(days=1400)).isoformat(),
            "uploads_playlist_id": "UU" + spec["youtube_channel_id"][2:],
        },
        "videos": videos,
        "comments": comments,
        "reference_date": REFERENCE.isoformat(),
    }


def main() -> None:
    rng = random.Random(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index: list[dict[str, Any]] = []
    for spec in CHANNELS:
        payload = build_channel(spec, rng)
        filename = f"demo_{spec['handle']}.json"
        path = OUTPUT_DIR / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        index.append(
            {
                "file": filename,
                "youtube_channel_id": spec["youtube_channel_id"],
                "handle": spec["handle"],
                "title": spec["title"],
                "videos": len(payload["videos"]),
                "comments": len(payload["comments"]),
            }
        )
        print(
            f"{filename}: {len(payload['videos'])} vídeos, {len(payload['comments'])} comentarios"
        )

    (OUTPUT_DIR / "index.json").write_text(
        json.dumps(
            {
                "note_es": (
                    "Datos de demostración generados artificialmente. No corresponden a "
                    "ningún canal ni persona real de YouTube."
                ),
                "generator": "scripts/generate_fixtures.py",
                "seed": SEED,
                "channels": index,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nEscrito en {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
