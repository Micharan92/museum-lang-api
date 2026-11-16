"""Logging su file delle chiamate, per gli audit interni della Fondazione.

Si usa il modulo logging della libreria standard, con un handler su file.
I messaggi non passano da print: restano nel file anche quando la console è chiusa.
"""

import logging
from pathlib import Path

# Cartella del progetto: app/ è un livello sotto la radice.
RADICE_PROGETTO = Path(__file__).resolve().parent.parent
PERCORSO_LOG = RADICE_PROGETTO / "logs" / "api_audit.log"

logger = logging.getLogger("museumlang")


def configura_logging() -> logging.Logger:
    """Prepara il logger una sola volta e lo scrive in logs/api_audit.log."""
    if logger.handlers:
        return logger

    PERCORSO_LOG.parent.mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.INFO)
    # Il logger non inoltra i messaggi al root logger, così ogni riga compare una volta sola.
    logger.propagate = False

    handler = logging.FileHandler(PERCORSO_LOG, encoding="utf-8")
    # Timestamp, livello e file di provenienza rendono il log leggibile a posteriori.
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(filename)s | %(message)s")
    )
    logger.addHandler(handler)
    return logger


def testo_per_log(testo: object, limite: int = 200) -> str:
    """Compatta il testo su una riga e lo tronca, se è molto lungo."""
    if testo is None:
        return ""
    compatto = " ".join(str(testo).split())
    if len(compatto) <= limite:
        return compatto
    return compatto[:limite] + "..."
