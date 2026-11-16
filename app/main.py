"""Punto di avvio di MuseumLangAPI.

FastAPI è stato scelto al posto di Flask per tre motivi:
valida da solo i tipi dichiarati con Pydantic, genera la documentazione su /docs
e rende espliciti i codici di risposta. Flask lascia questi controlli a chi scrive l'endpoint.
"""

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.log_audit import configura_logging, logger, testo_per_log
from app.modello import carica_pipeline
from app.routers.lingua import router as router_lingua

# Il logger va preparato prima del modello, così anche la verifica iniziale finisce nel file di audit.
configura_logging()
carica_pipeline()

app = FastAPI(
    title="MuseumLangAPI",
    description=(
        "Servizio REST per il riconoscimento della lingua di testi museali. "
        "Il modello distingue tedesco (DE), inglese (EN) e italiano (IT)."
    ),
    version="1.0.0",
)

app.include_router(router_lingua)


def _messaggio_validazione(errore: dict) -> str:
    """Traduce un errore di Pydantic in una frase leggibile."""
    tipo = errore.get("type", "")
    messaggio = str(errore.get("msg", ""))
    parti_campo = [str(parte) for parte in errore.get("loc", []) if parte != "body"]
    campo = ".".join(parti_campo) if parti_campo else "corpo della richiesta"

    if tipo == "missing":
        return f"Manca il campo obbligatorio '{campo}'."
    if tipo == "string_type":
        return f"Il campo '{campo}' deve essere una stringa."
    if tipo in {"string_too_long", "too_long"}:
        return f"Il campo '{campo}' supera la lunghezza massima consentita di 10000 caratteri."
    if tipo in {"json_invalid", "json_decode"}:
        return "Il corpo della richiesta non è un JSON valido."
    if "vuoto" in messaggio.lower():
        return "Il testo da analizzare non può essere vuoto."
    return f"Campo '{campo}': {messaggio}"


@app.exception_handler(RequestValidationError)
async def gestisci_richiesta_non_valida(request: Request, exc: RequestValidationError):
    """Intercetta JSON assente, campo mancante o tipo sbagliato e risponde 422.

    Questi casi non arrivano all'endpoint: il modello non viene chiamato.
    """
    frasi = [_messaggio_validazione(errore) for errore in exc.errors()]
    dettaglio = "Richiesta non valida. " + " ".join(frasi)

    logger.warning(
        "esito=RICHIESTA_NON_VALIDA | path=%s | body=%s | risposta=%s",
        request.url.path,
        testo_per_log(exc.body),
        dettaglio,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": dettaglio},
    )


@app.exception_handler(Exception)
async def gestisci_errore_interno(request: Request, exc: Exception):
    """Rete di sicurezza per un errore non previsto fuori dall'endpoint."""
    logger.exception("esito=ERRORE_INTERNO | path=%s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Errore interno del servizio. La richiesta non è stata completata."},
    )


@app.get("/", tags=["Stato"])
def stato_servizio() -> dict:
    """Controllo rapido: se risponde, il processo è avviato e il modello è già in memoria."""
    return {
        "service": "MuseumLangAPI",
        "status": "ok",
        "model_loaded": True,
    }


if __name__ == "__main__":
    # Avvio diretto, come visto per il debug dell'API dentro l'IDE.
    uvicorn.run(app, host="0.0.0.0", port=8000)
