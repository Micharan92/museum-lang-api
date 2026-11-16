"""Caricamento della pipeline di riconoscimento lingua e predizione.

Il file pickle viene letto una sola volta all'avvio e tenuto in memoria.
Rileggerlo a ogni richiesta rallenterebbe il servizio e lo renderebbe
poco usabile da più reparti in parallelo.
"""

import pickle
import warnings
from pathlib import Path

from sklearn.exceptions import InconsistentVersionWarning

from app.log_audit import logger

# Il modello è stato salvato con scikit-learn 1.6.0.
# In questo ambiente si usa una versione più recente, perché la 1.6 non ha
# una ruota installabile su Python 3.14. L'avviso viene registrato nel log
# e, subito dopo, un testo di prova controlla che predict() risponda IT.
PERCORSO_MODELLO = Path(__file__).resolve().parent.parent / "language_detection_pipeline.pkl"

# Sotto questa probabilità la lingua non viene considerata identificata.
# Con i soli numeri, per esempio, le tre classi restano intorno a 0.33:
# il modello sceglierebbe comunque una classe, ma senza una confidenza utile.
SOGLIA_CONFIDENZA_MINIMA = 0.5

# La pipeline caricata. Resta None finché carica_pipeline() non va a buon fine.
pipeline = None


class LinguaNonIdentificata(Exception):
    """Errore noto: il testo è arrivato, ma la lingua non è determinabile."""

    def __init__(self, confidenza: float) -> None:
        self.confidenza = confidenza
        super().__init__(
            "Impossibile identificare la lingua del testo: "
            f"la confidenza del modello è {round(confidenza, 4)}, "
            f"inferiore alla soglia minima di {SOGLIA_CONFIDENZA_MINIMA}."
        )


def carica_pipeline():
    """Carica il pickle, verifica predict() sul testo di prova e memorizza la pipeline."""
    global pipeline

    if pipeline is not None:
        return pipeline

    if not PERCORSO_MODELLO.is_file():
        raise FileNotFoundError(
            "File del modello non trovato: "
            f"{PERCORSO_MODELLO}. Va collocato nella cartella del progetto "
            "con il nome language_detection_pipeline.pkl."
        )

    # Gli avvisi di versione non devono interrompere l'avvio: li raccogliamo e li scriviamo nel log.
    with warnings.catch_warnings(record=True) as avvisi:
        warnings.simplefilter("always", InconsistentVersionWarning)
        # Stesso caricamento della traccia: pickle.load sul file aperto in lettura binaria.
        # Il with chiude il file anche se il caricamento fallisce.
        with open(PERCORSO_MODELLO, "rb") as file:
            loaded_pipeline = pickle.load(file)

    # Un'unica riga: il messaggio originale di scikit-learn si ripete per ogni stimatore e va a capo.
    if avvisi:
        logger.warning(
            "Il pickle è stato salvato con scikit-learn 1.6.0 e viene letto con una versione più recente. "
            "Subito sotto, la verifica sul testo di prova controlla che predict() restituisca IT."
        )

    # Verifica chiesta prima di esporre l'API: il testo di prova deve risultare italiano.
    text_to_predict = ["Questo è un testo di esempio in italiano."]
    predicted_language = loaded_pipeline.predict(text_to_predict)
    codice_prova = str(predicted_language[0])
    logger.info("Verifica iniziale del modello. Predicted language: %s", codice_prova)

    if codice_prova != "IT":
        raise RuntimeError(
            "Verifica iniziale fallita: per il testo di prova era atteso il codice IT, "
            f"il modello ha restituito {codice_prova}."
        )

    pipeline = loaded_pipeline
    logger.info(
        "Modello caricato da %s. Classi disponibili: %s",
        PERCORSO_MODELLO.name,
        ", ".join(str(classe) for classe in pipeline.classes_),
    )
    return pipeline


def predici_lingua(testo: str) -> dict:
    """Restituisce il codice lingua e la confidenza per un singolo testo.

    predict() restituisce la classe scelta, qui il codice lingua (valore discreto).
    predict_proba() restituisce, per ogni classe, la probabilità assegnata dal modello.
    La confidenza è la probabilità della classe scelta da predict(), non un valore a parte.
    """
    if pipeline is None:
        raise RuntimeError("Il modello non è stato caricato: impossibile fare la predizione.")

    # La pipeline è stata addestrata su una lista di stringhe, anche quando il testo è uno solo.
    testi = [testo]

    previsioni = pipeline.predict(testi)
    if len(previsioni) == 0 or previsioni[0] is None:
        raise LinguaNonIdentificata(0.0)

    # str() converte il tipo numpy restituito dal modello in una stringa JSON normale.
    codice = str(previsioni[0])
    classi = [str(classe) for classe in pipeline.classes_]
    if codice not in classi:
        raise LinguaNonIdentificata(0.0)

    probabilita = pipeline.predict_proba(testi)[0]
    confidenza = float(probabilita[classi.index(codice)])

    # Senza questa soglia il modello assegnerebbe sempre DE, EN o IT, anche a un testo senza lingua.
    if confidenza < SOGLIA_CONFIDENZA_MINIMA:
        raise LinguaNonIdentificata(confidenza)

    return {
        "language_code": codice,
        "confidence": round(confidenza, 4),
    }
