"""Test dell'endpoint /identify-language.

Coprono il caso corretto e i casi che la consegna chiede di gestire a mano:
testo vuoto, corpo non valido e lingua non determinabile.
"""

from fastapi.testclient import TestClient

from app.log_audit import PERCORSO_LOG
from app.main import app
from app.routers import lingua

client = TestClient(app)


def test_radice_segnala_servizio_attivo():
    risposta = client.get("/")
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert corpo["service"] == "MuseumLangAPI"
    assert corpo["status"] == "ok"
    assert corpo["model_loaded"] is True


def test_testo_italiano():
    risposta = client.post(
        "/identify-language",
        json={"text": "Questo è un esempio di testo."},
    )
    assert risposta.status_code == 200
    corpo = risposta.json()
    assert set(corpo) == {"language_code", "confidence"}
    assert corpo["language_code"] == "IT"
    assert 0.5 <= corpo["confidence"] <= 1


def test_testo_inglese():
    risposta = client.post(
        "/identify-language",
        json={"text": "The museum preserves paintings from the nineteenth century."},
    )
    assert risposta.status_code == 200
    assert risposta.json()["language_code"] == "EN"


def test_testo_tedesco():
    risposta = client.post(
        "/identify-language",
        json={"text": "Das Museum bewahrt Gemaelde aus dem neunzehnten Jahrhundert."},
    )
    assert risposta.status_code == 200
    assert risposta.json()["language_code"] == "DE"


def test_testo_vuoto(monkeypatch):
    chiamate = {"n": 0}

    def spia(testo):
        chiamate["n"] += 1
        return {"language_code": "IT", "confidence": 1.0}

    # Il modello non deve essere interpellato se non c'è un testo.
    monkeypatch.setattr(lingua, "predici_lingua", spia)
    risposta = client.post("/identify-language", json={"text": "   "})
    assert risposta.status_code == 400
    assert "vuoto" in risposta.json()["detail"].lower()
    assert chiamate["n"] == 0


def test_stringa_vuota():
    risposta = client.post("/identify-language", json={"text": ""})
    assert risposta.status_code == 400
    assert "vuoto" in risposta.json()["detail"].lower()


def test_campo_mancante():
    risposta = client.post("/identify-language", json={})
    assert risposta.status_code == 422
    assert "text" in risposta.json()["detail"]


def test_tipo_sbagliato():
    risposta = client.post("/identify-language", json={"text": 123})
    assert risposta.status_code == 422
    dettaglio = risposta.json()["detail"].lower()
    assert "stringa" in dettaglio


def test_json_non_valido():
    risposta = client.post(
        "/identify-language",
        content=b"questo non e' json",
        headers={"Content-Type": "application/json"},
    )
    assert risposta.status_code == 422
    assert "json" in risposta.json()["detail"].lower()


def test_lingua_non_identificabile():
    # Cifre senza parole: le probabilità restano divise fra le tre classi.
    risposta = client.post("/identify-language", json={"text": "12345 67890"})
    assert risposta.status_code == 422
    assert "impossibile identificare" in risposta.json()["detail"].lower()


def test_errore_interno_non_mostra_il_dettaglio_tecnico(monkeypatch):
    def esplodi(testo):
        raise RuntimeError("dettaglio interno da non mostrare")

    monkeypatch.setattr(lingua, "predici_lingua", esplodi)
    risposta = client.post(
        "/identify-language",
        json={"text": "Testo sufficiente per arrivare al modello."},
    )
    assert risposta.status_code == 500
    dettaglio = risposta.json()["detail"].lower()
    assert "interno" in dettaglio
    assert "dettaglio interno" not in dettaglio


def test_log_contiene_richiesta_e_risposta():
    frase = "Catalogo delle opere esposte nella sala del primo piano."
    risposta = client.post("/identify-language", json={"text": frase})
    assert risposta.status_code == 200

    contenuto_log = PERCORSO_LOG.read_text(encoding="utf-8")
    assert frase in contenuto_log
    assert '"language_code": "IT"' in contenuto_log
    assert "esito=OK" in contenuto_log
