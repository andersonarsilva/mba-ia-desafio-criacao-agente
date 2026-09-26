import uvicorn

from aurora.config import DEFAULT_PATHS
from aurora.db.seed import restaurar as restaurar_dados
from aurora.logs import configure_logging

HOST = "127.0.0.1"
PORT = 8000


def restaurar() -> None:
    restaurar_dados(DEFAULT_PATHS)
    print(f"Dados restaurados em {DEFAULT_PATHS.var}")


def api() -> None:
    configure_logging()
    uvicorn.run("aurora.api.main:create_app", factory=True, host=HOST, port=PORT, workers=1, log_config=None)
