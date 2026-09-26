from aurora.config import DEFAULT_PATHS
from aurora.db.seed import restaurar as restaurar_dados


def restaurar() -> None:
    restaurar_dados(DEFAULT_PATHS)
    print(f"Dados restaurados em {DEFAULT_PATHS.var}")
