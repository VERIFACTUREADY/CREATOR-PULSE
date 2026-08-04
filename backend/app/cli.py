"""Comandos de administración de Creator Signal AI.

Uso:
    python -m app.cli purgar --dias 90
    python -m app.cli purgar --simular
    python -m app.cli estado
    python -m app.cli cargar-demo

Existe porque la política de retención de datos no puede depender de que
alguien recuerde ejecutar SQL a mano: es un requisito de privacidad y necesita
un comando reproducible que se pueda programar con cron o con un trabajo de
Azure Container Apps.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.config import settings
from app.core.crypto import encryption_available, generate_key
from app.core.logging import configure_logging, get_logger
from app.db.session import check_database, detect_pgvector, session_scope
from app.models.entities import AnalysisRun, Channel, Comment, Video
from app.repositories.analysis import AnalysisRunRepository
from app.services.demo import DemoLoader, list_demo_channels
from app.workers.queue import check_redis

logger = get_logger(__name__)


def _count(session: object, model: type) -> int:
    stmt = select(func.count()).select_from(model)
    return int(session.execute(stmt).scalar_one())  # type: ignore[attr-defined]


def cmd_purgar(args: argparse.Namespace) -> int:
    """Elimina los análisis más antiguos que la ventana de retención."""
    days = args.dias if args.dias is not None else settings.data_retention_days
    cutoff = datetime.now(UTC) - timedelta(days=days)

    with session_scope() as session:
        affected = int(
            session.execute(
                select(func.count()).select_from(AnalysisRun).where(AnalysisRun.created_at < cutoff)
            ).scalar_one()
        )

        if args.simular:
            print(
                f"Simulación: se eliminarían {affected} análisis anteriores a "
                f"{cutoff.date().isoformat()} (retención de {days} días)."
            )
            print("No se ha borrado nada. Quita --simular para aplicarlo.")
            return 0

        deleted = AnalysisRunRepository(session).purge_older_than(days)

    logger.info("retention_purge", deleted_runs=deleted, days=days)
    print(
        f"Eliminados {deleted} análisis anteriores a {cutoff.date().isoformat()} "
        f"(retención de {days} días)."
    )
    return 0


def cmd_estado(_args: argparse.Namespace) -> int:
    """Muestra el estado de los servicios y un recuento de los datos."""
    db_ok = check_database()
    redis_ok = check_redis()

    print(f"Base de datos : {'correcta' if db_ok else 'NO DISPONIBLE'}")
    print(f"Redis         : {'correcto' if redis_ok else 'NO DISPONIBLE'}")

    if not db_ok:
        return 1

    print(f"pgvector      : {'activo' if detect_pgvector() else 'no disponible (se usa JSONB)'}")
    print(f"Clave YouTube : {'configurada' if settings.youtube_configured else 'sin configurar'}")
    print(f"Proveedor IA  : {settings.ai_provider}{'' if settings.ai_enabled else ' (inactivo)'}")
    print(f"Modo demo     : {'activado' if settings.enable_demo_mode else 'desactivado'}")
    if settings.enable_owner_mode:
        cifrado = "listo" if encryption_available() else "SIN CLAVE DE CIFRADO"
        print(f"Modo propietar: activado (cifrado de tokens: {cifrado})")
    else:
        print("Modo propietar: desactivado")
    print(f"Retención     : {settings.data_retention_days} días")

    with session_scope() as session:
        print("\nDatos almacenados:")
        print(f"  Canales      : {_count(session, Channel)}")
        print(f"  Vídeos       : {_count(session, Video)}")
        print(f"  Comentarios  : {_count(session, Comment)}")
        print(f"  Análisis     : {_count(session, AnalysisRun)}")

        completados = int(
            session.execute(
                select(func.count())
                .select_from(AnalysisRun)
                .where(AnalysisRun.status == "completed")
            ).scalar_one()
        )
        print(f"  Completados  : {completados}")
    return 0


def cmd_cargar_demo(args: argparse.Namespace) -> int:
    """Carga los canales de demostración en la base de datos.

    No lanza el análisis: sólo deja los datos listos para poder analizarlos
    desde la interfaz o para preparar una demostración sin esperas.
    """
    if not settings.enable_demo_mode:
        print("El modo demostración está desactivado (ENABLE_DEMO_MODE=false).", file=sys.stderr)
        return 1

    disponibles = list_demo_channels()
    if not disponibles:
        print("No se han encontrado datos de demostración.", file=sys.stderr)
        print("Genera las fixtures con: python scripts/generate_fixtures.py", file=sys.stderr)
        return 1

    seleccion = [c for c in disponibles if not args.handle or c.handle == args.handle.lstrip("@")]
    if not seleccion:
        print(f"No existe el canal de demostración «{args.handle}».", file=sys.stderr)
        print(f"Disponibles: {', '.join(c.handle for c in disponibles)}", file=sys.stderr)
        return 1

    with session_scope() as session:
        loader = DemoLoader(session)
        for info in seleccion:
            channel = loader.load(info.handle)
            print(
                f"Cargado @{info.handle}: {channel.title} "
                f"({info.videos} vídeos, {info.comments} comentarios)"
            )

    print("\nAnalízalos desde http://localhost:3000/demostracion")
    return 0


def cmd_generar_clave(_args: argparse.Namespace) -> int:
    """Genera una clave de cifrado para los tokens del modo propietario."""
    print("Añade esta línea a tu fichero .env:\n")
    print(f"OAUTH_TOKEN_ENCRYPTION_KEY={generate_key()}")
    print(
        "\nGuárdala como un secreto. Si la cambias, los canales conectados\n"
        "tendrán que volver a autorizarse."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Comandos de administración de Creator Signal AI.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    purgar = sub.add_parser("purgar", help="Aplica la política de retención de datos")
    purgar.add_argument(
        "--dias",
        type=int,
        default=None,
        help=f"Días de retención (por defecto: DATA_RETENTION_DAYS={settings.data_retention_days})",
    )
    purgar.add_argument(
        "--simular",
        action="store_true",
        help="Muestra qué se borraría sin borrar nada",
    )
    purgar.set_defaults(func=cmd_purgar)

    estado = sub.add_parser("estado", help="Estado de los servicios y recuento de datos")
    estado.set_defaults(func=cmd_estado)

    demo = sub.add_parser("cargar-demo", help="Carga los canales de demostración")
    demo.add_argument("--handle", default=None, help="Carga sólo este canal (por defecto, todos)")
    demo.set_defaults(func=cmd_cargar_demo)

    clave = sub.add_parser(
        "generar-clave", help="Genera la clave de cifrado de tokens del modo propietario"
    )
    clave.set_defaults(func=cmd_generar_clave)

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging(settings.log_level, json_output=False)
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:  # pragma: no cover - interacción manual
        print("\nInterrumpido.", file=sys.stderr)
        return 130
    except Exception as exc:
        logger.error("cli_error", comando=args.comando, error=str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
