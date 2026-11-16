"""Schemi dei dati in ingresso e in uscita.

Pydantic controlla i tipi prima che il testo arrivi al modello:
se il JSON non ha la forma attesa, FastAPI rifiuta la richiesta da solo.
"""

from pydantic import BaseModel, Field

# Una scheda di catalogo o una didascalia stanno comodamente sotto questo limite.
# Il tetto evita di mandare al modello un testo enorme per errore.
LUNGHEZZA_MASSIMA_TESTO = 10_000


class RichiestaTesto(BaseModel):
    """Corpo della POST /identify-language."""

    text: str = Field(
        ...,
        max_length=LUNGHEZZA_MASSIMA_TESTO,
        description="Testo di cui riconoscere la lingua.",
        examples=["Questo è un esempio di testo."],
    )


class RispostaLingua(BaseModel):
    """Risposta quando il modello assegna una lingua con confidenza sufficiente."""

    language_code: str = Field(
        ...,
        description="Codice della lingua identificata (DE, EN o IT).",
        examples=["IT"],
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Probabilità che il modello assegna alla lingua identificata.",
        examples=[0.98],
    )
