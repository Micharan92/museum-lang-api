# MuseumLangAPI

Servizio REST che espone MuseumLangID, il modello già addestrato per riconoscere la lingua di un testo museale. La richiesta contiene il testo in JSON; la risposta contiene il codice della lingua e la confidenza del modello.

Il modello distingue tre lingue: tedesco (`DE`), inglese (`EN`) e italiano (`IT`).

## Perché FastAPI

La consegna lasciava scegliere tra Flask e FastAPI. Qui si usa FastAPI perché con Pydantic controlla da solo che il corpo sia un JSON con il campo `text` di tipo stringa e, se il formato non è valido, risponde con un codice 4xx senza arrivare al modello. La documentazione interattiva è su `/docs`.

## Requisiti

- Python 3.14
- il file `language_detection_pipeline.pkl` nella cartella del progetto (è già presente)

Il pickle è stato prodotto con scikit-learn 1.6.0. Su Python 3.14 quella versione non ha un pacchetto installabile, quindi l'ambiente usa scikit-learn 1.9.1. All'avvio il servizio verifica che la frase di prova in italiano restituisca `IT`. Se la verifica fallisce, il processo non parte.

## Avvio

Dalla cartella del progetto, in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Il servizio ascolta su `http://127.0.0.1:8000`.

## Chiamare l'endpoint

`POST /identify-language`

```json
{
    "text": "Questo è un esempio di testo."
}
```

Risposta:

```json
{
    "language_code": "IT",
    "confidence": 1.0
}
```

Il valore `0.98` della consegna è solo un esempio. Il numero reale è la probabilità che `predict_proba()` assegna alla classe scelta da `predict()`.

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/identify-language -ContentType "application/json; charset=utf-8" -Body '{"text": "Questo è un esempio di testo."}'
```

## Codici di risposta

| Codice | Quando |
| --- | --- |
| 200 | Lingua identificata: `language_code` e `confidence`. |
| 400 | Testo vuoto o solo spazi. Il modello non viene chiamato. |
| 422 | JSON non valido, campo `text` mancante o non stringa, testo oltre 10000 caratteri, oppure confidenza sotto 0.5. |
| 500 | Errore interno. Il dettaglio tecnico resta nel log. |

`"12345 67890"` non ha una lingua riconoscibile e risponde 422. Una lingua diversa da DE, EN e IT viene assegnata a una di queste tre se la confidenza supera 0.5.

## Log e test

Richieste e risposte sono in `logs/api_audit.log`, con timestamp, testo ricevuto ed esito.

```powershell
pytest
```
