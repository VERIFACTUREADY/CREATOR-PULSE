"""Configuración de la aplicación leída de variables de entorno."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AiProvider = Literal["none", "anthropic", "openai", "ollama"]
EmbeddingBackend = Literal["hashing", "sentence-transformers"]
SentimentBackend = Literal["lexicon", "transformers"]
PgvectorMode = Literal["auto", "true", "false"]

#: Versión del algoritmo determinista. Se persiste en cada ejecución de análisis
#: para que los resultados históricos sean interpretables tras cambios de lógica.
ALGORITHM_VERSION = "1.0.0"


class Settings(BaseSettings):
    """Ajustes de la aplicación.

    Todos los valores tienen un valor por defecto seguro para que la aplicación
    arranque en modo demostración sin ninguna credencial.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Aplicación ---------------------------------------------------
    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "CreatorPulse AI"
    frontend_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000"

    # --- Control de acceso --------------------------------------------
    # La aplicación no tiene usuarios propios. En una beta privada el acceso se
    # delega en un proxy autenticado (Cloudflare Access, Azure Easy Auth, un
    # reverse proxy…) que inyecta una cabecera. `none` sólo vale para
    # desarrollo: en producción la aplicación se niega a arrancar con él.
    auth_mode: Literal["none", "trusted_proxy"] = "none"
    trusted_auth_header: str = "X-Auth-Token"
    trusted_auth_value: str = ""
    #: Redes desde las que se acepta la cabecera de autenticación, separadas
    #: por comas (CIDR o IP). Sin esto, cualquiera podría falsificarla.
    trusted_proxy_networks: str = "127.0.0.1/32,::1/128"

    # --- Retención ----------------------------------------------------
    # Son dos políticas distintas a propósito: los resultados de un análisis
    # caducan antes que los comentarios brutos, que se comparten entre
    # ejecuciones y volver a descargarlos cuesta cuota.
    comment_retention_days: int = 180

    # --- Base de datos ------------------------------------------------
    database_url: str = (
        "postgresql+psycopg://creator_signal:change-me@localhost:5432/creator_signal"
    )
    pgvector_mode: PgvectorMode = "auto"

    # --- Redis / cola -------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    rq_queue_name: str = "analysis"
    rq_job_timeout_seconds: int = 1800

    # --- YouTube ------------------------------------------------------
    youtube_api_key: str = ""
    youtube_max_videos_per_analysis: int = 20
    youtube_max_comments_per_video: int = 250
    youtube_max_comments_per_channel: int = 3000
    youtube_include_replies: bool = False
    youtube_cache_ttl_hours: int = 24
    youtube_request_timeout_seconds: int = 30
    youtube_max_retries: int = 4
    youtube_hard_max_videos: int = 50
    youtube_hard_max_comments_per_video: int = 500
    youtube_hard_max_comments_per_channel: int = 10_000
    youtube_api_base_url: str = "https://www.googleapis.com/youtube/v3"

    # --- Modo propietario (andamiaje) ---------------------------------
    enable_owner_mode: bool = False
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/api/oauth/google/callback"
    oauth_token_encryption_key: str = ""

    # --- Proveedor LLM opcional ---------------------------------------
    ai_provider: AiProvider = "none"
    anthropic_api_key: str = ""
    anthropic_model: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = ""
    ai_request_timeout_seconds: int = 60
    ai_max_retries: int = 2

    # --- Modelos de análisis ------------------------------------------
    embedding_backend: EmbeddingBackend = "hashing"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384
    sentiment_backend: SentimentBackend = "lexicon"
    sentiment_model: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    enable_toxicity_analysis: bool = True
    clustering_min_cluster_size: int = 5
    clustering_min_comments: int = 30

    # --- Privacidad ---------------------------------------------------
    data_retention_days: int = 90
    anonymize_comment_authors: bool = True
    author_hash_salt: str = "change-me-author-salt"

    # --- Observabilidad -----------------------------------------------
    #: Directorio de datos de demostración. Vacío = búsqueda automática
    #: relativa al repositorio (útil en desarrollo). En Docker se fija a
    #: `/fixtures`, que es donde los copia la imagen.
    fixtures_dir: str = ""

    log_level: str = "INFO"
    log_json: bool = True
    enable_demo_mode: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, value: str) -> str:
        return value.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        """Orígenes CORS explícitos. Nunca se usa el comodín `*`."""
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins or ["http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def trusted_proxy_network_list(self) -> list[str]:
        return [n.strip() for n in self.trusted_proxy_networks.split(",") if n.strip()]

    @property
    def auth_configured(self) -> bool:
        """`True` si el modo `trusted_proxy` tiene todo lo que necesita."""
        if self.auth_mode != "trusted_proxy":
            return False
        return bool(
            self.trusted_auth_header.strip()
            and self.trusted_auth_value.strip()
            and self.trusted_proxy_network_list
        )

    @property
    def youtube_configured(self) -> bool:
        return bool(self.youtube_api_key.strip())

    @property
    def ai_enabled(self) -> bool:
        """`True` sólo si el proveedor está configurado *y* tiene credenciales."""
        if self.ai_provider == "none":
            return False
        if self.ai_provider == "anthropic":
            return bool(self.anthropic_api_key.strip())
        if self.ai_provider == "openai":
            return bool(self.openai_api_key.strip())
        if self.ai_provider == "ollama":
            return bool(self.ollama_base_url.strip() and self.ollama_model.strip())
        return False

    @property
    def ai_model_name(self) -> str:
        return {
            "anthropic": self.anthropic_model,
            "openai": self.openai_model,
            "ollama": self.ollama_model,
        }.get(self.ai_provider, "")

    def clamp_limits(
        self,
        max_videos: int | None,
        max_comments_per_video: int | None,
        max_comments_per_channel: int | None,
    ) -> tuple[int, int, int]:
        """Ajusta los límites solicitados por el usuario a los máximos seguros."""
        videos = max_videos or self.youtube_max_videos_per_analysis
        per_video = max_comments_per_video or self.youtube_max_comments_per_video
        per_channel = max_comments_per_channel or self.youtube_max_comments_per_channel
        return (
            max(1, min(videos, self.youtube_hard_max_videos)),
            max(1, min(per_video, self.youtube_hard_max_comments_per_video)),
            max(1, min(per_channel, self.youtube_hard_max_comments_per_channel)),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instancia única de configuración (cacheada)."""
    return Settings()


settings: Settings = get_settings()

__all__ = ["ALGORITHM_VERSION", "Settings", "get_settings", "settings"]
