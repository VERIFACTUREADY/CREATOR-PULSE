"""Léxicos multilingües (español e inglés) del motor determinista.

Estos recursos hacen que el análisis funcione sin descargar ningún modelo y sin
depender de ningún LLM. Cuando se activa un backend neuronal, estos léxicos
siguen usándose para la extracción de intenciones y aspectos.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Sentimiento
# ---------------------------------------------------------------------------

#: Términos positivos con su peso (0-1). Cubre español e inglés.
POSITIVE_TERMS: dict[str, float] = {
    # Español
    "genial": 0.8,
    "increíble": 0.9,
    "increible": 0.9,
    "excelente": 0.9,
    "buenísimo": 0.9,
    "buenisimo": 0.9,
    "espectacular": 0.9,
    "maravilloso": 0.9,
    "fantástico": 0.9,
    "fantastico": 0.9,
    "brutal": 0.8,
    "crack": 0.8,
    "top": 0.6,
    "guay": 0.6,
    "bueno": 0.5,
    "buena": 0.5,
    "buenos": 0.5,
    "buenas": 0.5,
    "mejor": 0.6,
    "encanta": 0.9,
    "encantó": 0.9,
    "encanto": 0.8,
    "amo": 0.8,
    "adoro": 0.85,
    "gracias": 0.6,
    "útil": 0.7,
    "util": 0.7,
    "utilísimo": 0.85,
    "claro": 0.5,
    "clarísimo": 0.8,
    "clarisimo": 0.8,
    "divertido": 0.7,
    "gracioso": 0.7,
    "risa": 0.6,
    "reír": 0.6,
    "reir": 0.6,
    "carcajada": 0.75,
    "humor": 0.5,
    "aprendí": 0.7,
    "aprendi": 0.7,
    "aprendo": 0.65,
    "recomiendo": 0.75,
    "felicidades": 0.8,
    "enhorabuena": 0.8,
    "impresionante": 0.85,
    "perfecto": 0.85,
    "sigue": 0.4,
    "auténtico": 0.7,
    "autentico": 0.7,
    "honesto": 0.65,
    "sincero": 0.65,
    "bonito": 0.7,
    "bonita": 0.7,
    "guapo": 0.6,
    "guapa": 0.6,
    "preciosa": 0.8,
    "precioso": 0.8,
    "ídolo": 0.8,
    "idolo": 0.8,
    "favorito": 0.75,
    "favorita": 0.75,
    "calidad": 0.5,
    "profesional": 0.6,
    "inspirador": 0.8,
    "motivador": 0.75,
    "gran": 0.55,
    "grande": 0.5,
    "wow": 0.7,
    "😍": 0.8,
    "❤️": 0.8,
    "🔥": 0.7,
    "😂": 0.6,
    "👏": 0.7,
    "👍": 0.6,
    "🥰": 0.8,
    "💪": 0.6,
    "✨": 0.5,
    # Inglés
    "great": 0.8,
    "amazing": 0.9,
    "awesome": 0.85,
    "excellent": 0.9,
    "love": 0.85,
    "loved": 0.85,
    "perfect": 0.85,
    "best": 0.75,
    "good": 0.5,
    "nice": 0.55,
    "helpful": 0.75,
    "clear": 0.5,
    "funny": 0.7,
    "hilarious": 0.85,
    "thanks": 0.6,
    "thank": 0.6,
    "brilliant": 0.85,
    "underrated": 0.6,
    "quality": 0.5,
    "inspiring": 0.8,
    "authentic": 0.7,
    "honest": 0.65,
    "beautiful": 0.75,
    "gorgeous": 0.8,
    "favourite": 0.75,
    "favorite": 0.75,
    "wholesome": 0.7,
}

#: Términos negativos con su peso (0-1).
NEGATIVE_TERMS: dict[str, float] = {
    # Español
    "malo": 0.7,
    "mala": 0.7,
    "malísimo": 0.9,
    "malisimo": 0.9,
    "horrible": 0.9,
    "terrible": 0.85,
    "pésimo": 0.9,
    "pesimo": 0.9,
    "aburrido": 0.7,
    "aburre": 0.7,
    "lento": 0.5,
    "largo": 0.35,
    "repetitivo": 0.6,
    "repetido": 0.5,
    "cansino": 0.7,
    "pesado": 0.6,
    "confuso": 0.65,
    "confusa": 0.65,
    "lío": 0.5,
    "lio": 0.5,
    "no entiendo": 0.6,
    "no se entiende": 0.75,
    "no se escucha": 0.8,
    "no se oye": 0.8,
    "no se ve": 0.7,
    "ruido": 0.6,
    "ruidoso": 0.7,
    "molesta": 0.65,
    "molesto": 0.65,
    "fatal": 0.85,
    "decepción": 0.85,
    "decepcion": 0.85,
    "decepcionado": 0.85,
    "decepcionante": 0.85,
    "peor": 0.7,
    "flojo": 0.6,
    "floja": 0.6,
    "clickbait": 0.7,
    "engaño": 0.8,
    "engano": 0.8,
    "mentira": 0.75,
    "falso": 0.7,
    "aburrida": 0.7,
    "insoportable": 0.9,
    "odio": 0.85,
    "basura": 0.9,
    "penoso": 0.85,
    "sobra": 0.4,
    "innecesario": 0.5,
    "oscuro": 0.45,
    "borroso": 0.6,
    "cortado": 0.5,
    "problema": 0.5,
    "error": 0.5,
    "fallo": 0.55,
    "😡": 0.85,
    "👎": 0.7,
    "🤮": 0.9,
    "😴": 0.6,
    "🙄": 0.5,
    # Inglés
    "bad": 0.7,
    "awful": 0.9,
    "boring": 0.7,
    "worst": 0.85,
    "hate": 0.85,
    "confusing": 0.65,
    "unclear": 0.6,
    "noisy": 0.7,
    "loud": 0.45,
    "disappointing": 0.85,
    "disappointed": 0.85,
    "annoying": 0.7,
    "repetitive": 0.6,
    "slow": 0.5,
    "cringe": 0.7,
    "garbage": 0.9,
    "misleading": 0.75,
    "fake": 0.7,
    "blurry": 0.6,
    "dark": 0.4,
    "cant hear": 0.8,
    "can't hear": 0.8,
    "too long": 0.55,
    "too loud": 0.7,
}

#: Palabras que invierten la polaridad del término siguiente.
NEGATION_TERMS: frozenset[str] = frozenset(
    {
        "no",
        "nunca",
        "jamás",
        "jamas",
        "ni",
        "tampoco",
        "sin",
        "nada",
        "not",
        "never",
        "without",
        "dont",
        "don't",
        "doesnt",
        "doesn't",
        "isnt",
        "isn't",
        "wasnt",
        "wasn't",
        "cant",
        "can't",
        "cannot",
    }
)

#: Intensificadores que amplifican el término siguiente.
INTENSIFIER_TERMS: dict[str, float] = {
    "muy": 1.4,
    "super": 1.5,
    "súper": 1.5,
    "demasiado": 1.35,
    "bastante": 1.2,
    "tan": 1.3,
    "totalmente": 1.4,
    "absolutamente": 1.5,
    "realmente": 1.3,
    "increíblemente": 1.5,
    "extremadamente": 1.5,
    "mucho": 1.3,
    "muchísimo": 1.5,
    "very": 1.4,
    "really": 1.3,
    "so": 1.25,
    "extremely": 1.5,
    "absolutely": 1.5,
    "incredibly": 1.5,
    "totally": 1.4,
    "quite": 1.15,
    "too": 1.3,
}

#: Atenuadores que reducen la intensidad.
DIMINISHER_TERMS: dict[str, float] = {
    "poco": 0.6,
    "algo": 0.7,
    "ligeramente": 0.6,
    "apenas": 0.5,
    "casi": 0.8,
    "slightly": 0.6,
    "somewhat": 0.7,
    "a bit": 0.65,
    "barely": 0.5,
    "kinda": 0.7,
}

#: Marcadores de contraste que suelen indicar sentimiento mixto.
CONTRAST_MARKERS: frozenset[str] = frozenset(
    {"pero", "aunque", "sin embargo", "no obstante", "but", "however", "although", "though"}
)

#: Marcadores de posible sarcasmo. Sólo reducen la confianza, nunca invierten.
SARCASM_MARKERS: tuple[str, ...] = (
    "claro claro",
    "sí claro",
    "si claro",
    "ya ya",
    "qué sorpresa",
    "que sorpresa",
    "yeah right",
    "sure sure",
    "/s",
    "🙃",
    "obviamente no",
)

# ---------------------------------------------------------------------------
# Toxicidad y acoso (señal de seguridad para el creador, no vigilancia)
# ---------------------------------------------------------------------------

TOXIC_TERMS: dict[str, float] = {
    "idiota": 0.85,
    "imbécil": 0.9,
    "imbecil": 0.9,
    "estúpido": 0.85,
    "estupido": 0.85,
    "tonto": 0.6,
    "tonta": 0.6,
    "payaso": 0.7,
    "payasa": 0.7,
    "inútil": 0.75,
    "inutil": 0.75,
    "cállate": 0.8,
    "callate": 0.8,
    "muérete": 0.95,
    "muerete": 0.95,
    "asqueroso": 0.85,
    "asquerosa": 0.85,
    "patético": 0.8,
    "patetico": 0.8,
    "gorda": 0.7,
    "gordo": 0.6,
    "fea": 0.75,
    "feo": 0.7,
    "ridículo": 0.65,
    "ridiculo": 0.65,
    "vergüenza": 0.6,
    "verguenza": 0.6,
    "lárgate": 0.85,
    "largate": 0.85,
    "nadie te quiere": 0.95,
    "deja youtube": 0.8,
    "idiot": 0.85,
    "stupid": 0.8,
    "moron": 0.85,
    "loser": 0.8,
    "ugly": 0.75,
    "shut up": 0.8,
    "kill yourself": 1.0,
    "kys": 1.0,
    "pathetic": 0.8,
    "worthless": 0.85,
    "nobody likes you": 0.95,
    "quit youtube": 0.8,
}

# ---------------------------------------------------------------------------
# Intenciones
# ---------------------------------------------------------------------------

#: Patrones por intención. Cada uno es una expresión regular ya compilada.
INTENT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    # Sólo cuenta como pregunta si hay signo de interrogación o un
    # interrogativo inequívoco. `que` y `como` sin tilde son conjunciones
    # frecuentísimas en español y marcarían casi cualquier comentario.
    "question": [
        re.compile(r"[?¿]"),
        re.compile(r"\b(qué|cuál|cuándo|dónde|quién|cómo|por qué)\b"),
        re.compile(r"\b(alguien sabe|sabes si|me pregunto|tengo una duda|una pregunta)\b"),
        re.compile(r"\b(anyone know|does anyone|can you tell|any idea)\b"),
    ],
    "tutorial_request": [
        re.compile(
            r"\b(tutorial|paso a paso|explica|explícanos|explicanos|enséñan?os|ensenanos|enseña|guía|guia)\b"
        ),
        re.compile(r"\b(cómo|como)\s+(lo\s+)?(haces|hiciste|consigues|logras|editas|grabas)\b"),
        re.compile(
            r"\b(tutorial|step by step|how do you|how did you|teach us|walkthrough|guide)\b"
        ),
        re.compile(r"\b(para principiantes|desde cero|para novatos|for beginners|from scratch)\b"),
    ],
    "content_request": [
        re.compile(
            r"\b(haz|has|hazte|hagan|podrías|podrias|puedes|podéis|podeis)\s+.{0,25}\b(vídeo|video|short|directo|serie)\b"
        ),
        re.compile(
            r"\b(quiero|queremos|me gustaría|me gustaria|nos gustaría|necesito)\s+.{0,25}\b(vídeo|video|ver|contenido|más|mas)\b"
        ),
        re.compile(
            r"\b(segunda parte|parte 2|parte dos|continuación|continuacion|secuela|más de esto|mas de esto)\b"
        ),
        re.compile(
            r"\b(please make|please do|can you make|can you do|do a video|part 2|second part|more of this)\b"
        ),
        re.compile(r"\b(sube|suban|subid)\s+.{0,20}\b(vídeo|video|contenido)\b"),
    ],
    "product_request": [
        re.compile(
            r"\b(qué|que|cuál|cual)\s+.{0,20}\b(usas|usaste|utilizas|marca|modelo|producto|micro|micrófono|microfono|cámara|camara)\b"
        ),
        re.compile(
            r"\b(enlace|link|dónde lo compro|donde lo compro|dónde comprar|donde comprar|referencia)\b"
        ),
        re.compile(
            r"\b(what|which)\s+.{0,20}\b(do you use|did you use|brand|camera|mic|microphone|product)\b"
        ),
        re.compile(r"\b(link please|where to buy|drop the link)\b"),
    ],
    "constructive_criticism": [
        re.compile(
            r"\b(deberías|deberias|deberíais|podrías mejorar|podrias mejorar|te recomiendo|sugiero|sugerencia|mejoraría|mejoraria)\b"
        ),
        re.compile(
            r"\b(sería mejor|seria mejor|estaría mejor|estaria mejor|le falta|le sobra|hace falta)\b"
        ),
        re.compile(
            r"\b(you should|it would be better|i suggest|my suggestion|needs work|could improve)\b"
        ),
        re.compile(
            r"\b(no se (escucha|oye|entiende|ve)|se escucha (mal|bajo)|la música (tapa|está muy alta))\b"
        ),
    ],
    "praise": [
        re.compile(
            r"\b(gracias|genial|increíble|increible|excelente|me encanta|me encantó|me encanto|buenísimo|buenisimo|crack|felicidades|enhorabuena)\b"
        ),
        re.compile(
            r"\b(thank you|thanks|amazing|great video|love this|loved it|awesome|best video)\b"
        ),
        re.compile(r"\b(el mejor|la mejor|mi favorito|mi favorita)\b"),
    ],
    "insult": [
        re.compile(
            r"\b(idiota|imbécil|imbecil|estúpido|estupido|payaso|asqueroso|patético|patetico|cállate|callate|muérete|muerete|lárgate|largate)\b"
        ),
        re.compile(r"\b(idiot|stupid|moron|loser|shut up|kill yourself|kys|pathetic|worthless)\b"),
    ],
    "agreement": [
        re.compile(
            r"\b(totalmente de acuerdo|estoy de acuerdo|exacto|tienes razón|tienes razon|así es|asi es|coincido)\b"
        ),
        re.compile(r"\b(i agree|totally agree|exactly|so true|this|facts)\b"),
    ],
    "disagreement": [
        re.compile(
            r"\b(no estoy de acuerdo|discrepo|te equivocas|no es (así|asi|cierto|verdad)|falso)\b"
        ),
        re.compile(r"\b(i disagree|thats wrong|that's wrong|not true|actually no)\b"),
    ],
    "personal_story": [
        re.compile(
            r"\b(a mí me pasó|a mi me paso|cuando yo|en mi caso|yo también|yo tambien|mi experiencia|llevo \d+ años)\b"
        ),
        re.compile(r"\b(happened to me|in my case|i also|my experience|when i was)\b"),
    ],
    "spam": [
        re.compile(
            r"\b(suscríbete a mi canal|suscribete a mi canal|visita mi perfil|mira mi canal|sub4sub|sigueme|sígueme)\b"
        ),
        re.compile(
            r"\b(check out my channel|sub to me|follow me|free .{0,15}(bitcoin|crypto|money)|whatsapp \+?\d)\b"
        ),
        re.compile(r"(t\.me/|bit\.ly/|wa\.me/)"),
    ],
}

# ---------------------------------------------------------------------------
# Aspectos
# ---------------------------------------------------------------------------

#: Taxonomía inicial. Los temas dinámicos se descubren aparte con clustering,
#: y ningún comentario se fuerza a encajar en una de estas etiquetas.
ASPECT_KEYWORDS: dict[str, list[str]] = {
    "apariencia": [
        "apariencia",
        "look",
        "estilo",
        "guapo",
        "guapa",
        "atractivo",
        "outfit",
        "vestuario",
        "ropa",
        "estética",
        "estetica",
        "aesthetic",
    ],
    "ojos": ["ojos", "mirada", "eyes", "eyeliner"],
    "pelo": ["pelo", "cabello", "peinado", "melena", "hair", "haircut", "flequillo"],
    "maquillaje": ["maquillaje", "makeup", "labial", "sombra", "base", "corrector", "delineado"],
    "voz": ["voz", "tono de voz", "acento", "vocaliza", "voice", "accent", "hablas"],
    "personalidad": [
        "personalidad",
        "carisma",
        "energía",
        "energia",
        "vibra",
        "personality",
        "charisma",
        "vibe",
    ],
    "humor": [
        "humor",
        "gracioso",
        "risa",
        "chiste",
        "divertido",
        "funny",
        "hilarious",
        "joke",
        "comedia",
    ],
    "autenticidad": [
        "auténtico",
        "autentico",
        "honesto",
        "sincero",
        "natural",
        "real",
        "genuine",
        "authentic",
        "honest",
    ],
    "conocimiento": [
        "experto",
        "sabes mucho",
        "conocimiento",
        "profundidad",
        "riguroso",
        "documentado",
        "expertise",
        "knowledgeable",
        "aprendí",
        "aprendi",
        "aprendo",
        "educativo",
    ],
    "narrativa": [
        "narrativa",
        "historia",
        "storytelling",
        "cuentas",
        "relato",
        "guion",
        "guión",
        "story",
    ],
    "edicion": [
        "edición",
        "edicion",
        "montaje",
        "editado",
        "cortes",
        "editing",
        "cuts",
        "transiciones",
        "efectos",
    ],
    "iluminacion": [
        "iluminación",
        "iluminacion",
        "luz",
        "luces",
        "oscuro",
        "lighting",
        "light",
        "brillo",
    ],
    "audio": [
        "audio",
        "sonido",
        "micrófono",
        "microfono",
        "micro",
        "no se escucha",
        "no se oye",
        "ruido",
        "sound",
        "mic",
        "volumen",
        "volume",
    ],
    "musica": [
        "música",
        "musica",
        "canción",
        "cancion",
        "banda sonora",
        "music",
        "soundtrack",
        "beat",
    ],
    "ritmo": [
        "ritmo",
        "pace",
        "rápido",
        "rapido",
        "lento",
        "slow",
        "fast",
        "pacing",
        "se hace pesado",
    ],
    "duracion": [
        "duración",
        "duracion",
        "largo",
        "corto",
        "demasiado largo",
        "too long",
        "length",
        "minutos",
    ],
    "miniatura": ["miniatura", "thumbnail", "portada", "caratula", "carátula"],
    "titulo": ["título", "titulo", "title", "clickbait"],
    "frecuencia": [
        "frecuencia",
        "sube más",
        "sube mas",
        "cuándo subes",
        "cuando subes",
        "más seguido",
        "mas seguido",
        "upload",
        "post more",
        "cada cuánto",
        "cada cuanto",
    ],
    "repeticion": [
        "repetitivo",
        "siempre lo mismo",
        "repites",
        "repetitive",
        "same thing",
        "otra vez lo mismo",
    ],
    "claridad": [
        "claro",
        "claridad",
        "se entiende",
        "no entiendo",
        "confuso",
        "explicas bien",
        "clear",
        "clarity",
        "confusing",
    ],
    "producto": [
        "producto",
        "marca",
        "patrocinio",
        "publicidad",
        "afiliado",
        "sponsor",
        "brand",
        "ad",
    ],
    "comunidad": [
        "comunidad",
        "responde",
        "contestas",
        "interacción",
        "interaccion",
        "directo",
        "comunidad",
        "community",
        "reply",
        "livestream",
    ],
}

#: Etiqueta legible en español de cada aspecto.
ASPECT_LABELS_ES: dict[str, str] = {
    "apariencia": "Apariencia y estilo visual",
    "ojos": "Ojos y mirada",
    "pelo": "Pelo y peinado",
    "maquillaje": "Maquillaje",
    "voz": "Voz",
    "personalidad": "Personalidad",
    "humor": "Humor",
    "autenticidad": "Autenticidad",
    "conocimiento": "Conocimiento y valor educativo",
    "narrativa": "Narrativa y storytelling",
    "edicion": "Edición",
    "iluminacion": "Iluminación",
    "audio": "Audio",
    "musica": "Música",
    "ritmo": "Ritmo",
    "duracion": "Duración",
    "miniatura": "Miniatura",
    "titulo": "Título",
    "frecuencia": "Frecuencia de publicación",
    "repeticion": "Repetición de contenidos",
    "claridad": "Claridad de la explicación",
    "producto": "Producto o servicio mencionado",
    "comunidad": "Interacción con la comunidad",
}

# ---------------------------------------------------------------------------
# Detección de idioma (heurística ligera basada en marcadores)
# ---------------------------------------------------------------------------

LANGUAGE_MARKERS: dict[str, frozenset[str]] = {
    "es": frozenset(
        {
            "el",
            "la",
            "los",
            "las",
            "de",
            "que",
            "y",
            "en",
            "un",
            "una",
            "es",
            "por",
            "con",
            "para",
            "muy",
            "más",
            "mas",
            "pero",
            "como",
            "este",
            "esta",
            "eso",
            "tu",
            "tus",
            "me",
            "te",
            "se",
            "no",
            "sí",
            "si",
            "gracias",
            "vídeo",
            "video",
            "canal",
            "hola",
            "porque",
            "cuando",
            "también",
            "tambien",
        }
    ),
    "en": frozenset(
        {
            "the",
            "and",
            "you",
            "your",
            "this",
            "that",
            "is",
            "are",
            "was",
            "for",
            "with",
            "have",
            "but",
            "not",
            "video",
            "channel",
            "thanks",
            "please",
            "what",
            "when",
            "how",
            "why",
            "would",
            "could",
            "really",
            "just",
            "like",
        }
    ),
    "pt": frozenset(
        {
            "você",
            "voce",
            "não",
            "nao",
            "muito",
            "obrigado",
            "vídeo",
            "canal",
            "para",
            "com",
            "isso",
            "essa",
            "esse",
            "então",
            "entao",
            "mais",
        }
    ),
    "fr": frozenset(
        {
            "le",
            "la",
            "les",
            "des",
            "vous",
            "est",
            "pour",
            "avec",
            "mais",
            "merci",
            "vidéo",
            "chaîne",
            "très",
            "pas",
            "ça",
            "cette",
        }
    ),
}

#: Caracteres exclusivos o muy característicos de cada idioma.
LANGUAGE_CHAR_HINTS: dict[str, str] = {
    "es": "ñ¿¡áéíóúü",
    "pt": "ãõçà",
    "fr": "çèêëùœ",
    "de": "äöüß",
}


__all__ = [
    "ASPECT_KEYWORDS",
    "ASPECT_LABELS_ES",
    "CONTRAST_MARKERS",
    "DIMINISHER_TERMS",
    "INTENSIFIER_TERMS",
    "INTENT_PATTERNS",
    "LANGUAGE_CHAR_HINTS",
    "LANGUAGE_MARKERS",
    "NEGATION_TERMS",
    "NEGATIVE_TERMS",
    "POSITIVE_TERMS",
    "SARCASM_MARKERS",
    "TOXIC_TERMS",
]
