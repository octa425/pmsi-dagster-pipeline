from fastapi.testclient import TestClient
from api_prediction import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["statut"] == "OK"

def test_accueil():
    response = client.get("/")
    assert response.status_code == 200
    assert "API" in response.json()["message"]

def test_predict_retourne_une_reponse():
    response = client.post("/predict", json={
        "dp": "I500",
        "pathologie": "IC",
        "nb_sejours_precedents": 2,
        "mois_entree": 6
    })
    # Soit le modele est charge (200 avec prediction)
    # Soit il est absent (200 avec message erreur)
    # Dans les deux cas l'API repond 200
    assert response.status_code == 200
    data = response.json()
    assert "erreur" in data or "probabilite_readmission_30j" in data

def test_predict_champs_obligatoires():
    # Sans les champs requis → 422 Unprocessable Entity
    # Independant des .pkl
    response = client.post("/predict", json={})
    assert response.status_code == 422
