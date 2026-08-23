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

def test_predict_structure():
    response = client.post("/predict", json={
        "dp": "I500",
        "pathologie": "IC",
        "nb_sejours_precedents": 2,
        "mois_entree": 6
    })
    assert response.status_code == 200
    assert "probabilite_readmission_30j" in response.json()
    assert "niveau_risque" in response.json()

def test_predict_pathologie_invalide():
    response = client.post("/predict", json={
        "dp": "I500",
        "pathologie": "INVALIDE",
        "nb_sejours_precedents": 0,
        "mois_entree": 1
    })
    assert response.status_code == 400
