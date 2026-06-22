import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# Chargement des donnees
df = pd.read_csv("/tmp/dataset_ml.csv")
df["date_entree"] = pd.to_datetime(df["date_entree"])
df["mois_entree"] = df["date_entree"].dt.month

# Encodeurs
encodeur_dp = LabelEncoder()
df["dp_encode"] = encodeur_dp.fit_transform(df["dp"])

encodeur_pathologie = LabelEncoder()
df["pathologie_encode"] = encodeur_pathologie.fit_transform(df["pathologie"])

# Variables et cible
X = df[["dp_encode", "pathologie_encode",
        "nb_sejours_precedents", "mois_entree"]]
y = df["readmis_30j"]

# Separation entrainement / test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Entrainement
modele = RandomForestClassifier(
    n_estimators=200,
    class_weight="balanced",
    random_state=42
)
modele.fit(X_train, y_train)

# Sauvegarde du modele ET des encodeurs
joblib.dump(modele, "model_rf.pkl")
joblib.dump(encodeur_dp, "encodeur_dp.pkl")
joblib.dump(encodeur_pathologie, "encodeur_pathologie.pkl")

print("Modele et encodeurs sauvegardes avec succes !")
print(f"Classes dp connues : {list(encodeur_dp.classes_[:5])}...")
print(f"Classes pathologie : {list(encodeur_pathologie.classes_)}")