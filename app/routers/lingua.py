"""Endpoint di riconoscimento della lingua.

Il router è separato dalla creazione dell'app, come visto per APIRouter:
la definizione della rotta resta leggibile anche se in seguito si aggiungono altri endpoint.
"""

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status

from app.log_audit import logger, testo_per_log
from app.modello import LinguaNonIdentificata, predici_lingua
from app.schemi import RichiestaTesto, RispostaLingua

router = APIRouter(tags=["Riconoscimento lingua"])


@router.post(
    "/identify-language",
    response_model=RispostaLingua,
    status_code=status.HTTP_200_OK,
    summary="Riconosce la lingua di un testo",
    responses={
        400: {"description": "Il testo è vuoto oppure contiene solo spazi."},
        422: {
            "description": (
                "Il JSON non è valido, il campo text manca o ha un tipo sbagliato, "
                "il testo supera la lunghezza massima, oppure la lingua non è identificabile."
            )
        },
        500: {"description": "Errore interno durante la predizione."},
    },
)
def identifica_lingua(richiesta: RichiestaTesto, request: Request) -> RispostaLingua:
    """Riceve un JSON con il campo text e restituisce lingua e confidenza.

    La funzione è sincrona perché predict() di scikit-learn è un'operazione bloccante.
    FastAPI esegue le funzioni definite con def in un thread separato.
    """
    # Id del processamento: collega nel log la richiesta e la risposta della stessa chiamata.
    request_id = str(uuid4())
    client = request.client.host if request.client else "sconosciuto"
    testo = richiesta.text.strip()

    logger.info(
        "request_id=%s | client=%s | richiesta ricevuta | testo=%s",
        request_id,
        client,
        testo_per_log(testo),
    )

    # Controllo esplicito prima del modello: un testo vuoto non è una lingua da predire.
    if not testo:
        dettaglio = "Il testo da analizzare non può essere vuoto."
        logger.warning(
            "request_id=%s | esito=TESTO_VUOTO | risposta=%s",
            request_id,
            dettaglio,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=dettaglio,
        )

    try:
        risultato = predici_lingua(testo)
    except LinguaNonIdentificata as errore:
        # Caso previsto: il modello non raggiunge la soglia di confidenza.
        logger.warning(
            "request_id=%s | esito=LINGUA_NON_IDENTIFICATA | risposta=%s",
            request_id,
            errore,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(errore),
        ) from errore
    except Exception:
        # L'errore completo resta nel log. Al client arriva solo un messaggio generico.
        logger.exception("request_id=%s | esito=ERRORE_INTERNO", request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno del servizio. La richiesta non è stata completata.",
        ) from None

    logger.info(
        "request_id=%s | esito=OK | risposta=%s",
        request_id,
        json.dumps(risultato, ensure_ascii=False),
    )
    return risultato
