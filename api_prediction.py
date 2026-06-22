from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np

modele = joblib.load("model_rf.pkl")
encodeur_dp = joblib.load("encodeur_dp.pkl")
encodeur_pathologie = joblib.load("encodeur_pathologie.pkl")

app = FastAPI(
    title="API Prediction Readmission PMSI",
    description="Predit le risque de readmission a 30 jours pour les patients PMSI",
    version="1.0.0"
)

class DonneesPatient(BaseModel):
    dp: str
    pathologie: str
    nb_sejours_precedents: int
    mois_entree: int

@app.get("/")
def accueil():
    return {"message": "API Prediction Readmission PMSI", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"statut": "OK", "modele": "Random Forest"}

@app.post("/predict")
def predire_readmission(patient: DonneesPatient):

    if patient.dp not in encodeur_dp.classes_:
        raise HTTPException(
            status_code=400,
            detail=f"Code DP inconnu : {patient.dp}. Codes valides : {list(encodeur_dp.classes_)}"
        )

    if patient.pathologie not in encodeur_pathologie.classes_:
        raise HTTPException(
            status_code=400,
            detail=f"Pathologie inconnue : {patient.pathologie}. Valides : {list(encodeur_pathologie.classes_)}"
        )

    dp_encode = encodeur_dp.transform([patient.dp])[0]
    pathologie_encode = encodeur_pathologie.transform([patient.pathologie])[0]

    X = np.array([[
        dp_encode,
        pathologie_encode,
        patient.nb_sejours_precedents,
        patient.mois_entree
    ]])

    proba_classes = modele.predict_proba(X)[0]
    if len(proba_classes) > 1:
        probabilite = float(proba_classes[1])
    else:
        probabilite = 0.0

    prediction = int(modele.predict(X)[0])

    if probabilite >= 0.7:
        niveau_risque = "ELEVE"
    elif probabilite >= 0.4:
        niveau_risque = "MODERE"
    else:
        niveau_risque = "FAIBLE"

    return {
        "dp": patient.dp,
        "pathologie": patient.pathologie,
        "nb_sejours_precedents": patient.nb_sejours_precedents,
        "mois_entree": patient.mois_entree,
        "probabilite_readmission_30j": round(probabilite, 3),
        "prediction": prediction,
        "niveau_risque": niveau_risque,
        "interpretation": f"Probabilite de readmission a 30 jours : {round(probabilite * 100, 1)}%"
    }