import csv
import random

# 1. Définition des en-têtes conformes à votre code
headers = [
    "NIP", "NDA", "URMP",
    "CIM principal", "Diag Relie", "Diag Rsm",
    "GHM", "GHS", "Duree sejour",
    "Date entree dossier", "Date sortie dossier"
]
headers += [f"CIM SIGN {i}" for i in range(1, 100)]

rows = []

# Fonction d'aide pour générer une ligne de base
def generer_sejour(id_unique, dp, dr="", das_list=[]):
    nip = f"100{id_unique:05d}"
    nda = f"200{id_unique:06d}"
    urmp = random.choice(["MED01", "CAR02", "REAH0", "REHA1", "PNEUM"])
    
    # Choix cohérent GHM/GHS pour l'insuffisance cardiaque ou BPCO
    if dp.startswith("I50") or dr.startswith("I50"):
        ghm = random.choice(["05M091", "05M092", "05M093"])
        ghs = random.choice(["1844", "1845", "1846"])
    else:
        ghm = "05M041"
        ghs = "1830"
        
    duree = str(random.randint(2, 15))
    
    # Dates en 2026
    jour = random.randint(1, 20)
    mois = random.randint(1, 12)
    date_entree = f"{jour:02d}/{mois:02d}/2026"
    date_sortie = f"{(jour + int(duree)):02d}/{mois:02d}/2026"
    
    # Remplissage des 99 CIM SIGN
    cim_sign = das_list + [""] * (99 - len(das_list))
    
    return [nip, nda, urmp, dp, dr, "", ghm, ghs, duree, date_entree, date_sortie] + cim_sign

print("⏳ Génération du jeu de données en cours...")

id_compteur = 1

# A. Génération de TOUS les séjours Insuffisance Cardiaque (2 312 lignes au total)
# Dispatchés intelligemment entre le DP, le DR et les DAS (CIM SIGN) pour valider votre fonction has_ic
for _ in range(1500):
    # En Diagnostic Principal
    rows.append(generer_sejour(id_compteur, dp=random.choice(["I500", "I501", "I509"]), das_list=["I10", "E119"]))
    id_compteur += 1

for _ in range(412):
    # En Diagnostic Relié
    rows.append(generer_sejour(id_compteur, dp="J440", dr="I509", das_list=["N183"]))
    id_compteur += 1

for _ in range(400):
    # Dans les diagnostics associés significatifs (CIM SIGN)
    rows.append(generer_sejour(id_compteur, dp="E119", das_list=["I10", "I500", "Z921"]))
    id_compteur += 1


# B. Génération des séjours BPCO (668 lignes)
for _ in range(668):
    rows.append(generer_sejour(id_compteur, dp=random.choice(["J440", "J441", "J449"]), das_list=["I10"]))
    id_compteur += 1


# C. Ajout de séjours "tout-venant" (autres pathologies) pour simuler la masse brute
# On complète pour atteindre environ 5 000 séjours au total
for _ in range(2020):
    rows.append(generer_sejour(id_compteur, dp=random.choice(["M160", "K529", "J189"]), das_list=["Z000"]))
    id_compteur += 1

# Shuffle pour mélanger les lignes comme dans un vrai fichier d'hôpital
random.shuffle(rows)

# 4. Écriture du fichier CSV final
chemin_destination = "DATA_SET_SIMULE.csv"

with open(chemin_destination, "w", encoding="windows-1252", newline="") as f:
    writer = csv.writer(f, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)

print("\n" + "="*50)
print(f"✅ Fichier volumétrique créé avec succès : {chemin_destination}")
print(f"📊 Nombre total de lignes générées : {len(rows)}")
print(f"🎯 Dont séjours Insuffisance Cardiaque (I50) configurés : 2312")
print(f"🎯 Dont séjours BPCO configurés : 668")
print("="*50)

import os
print(os.getcwd())



