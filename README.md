# pmsi-dagster-pipeline

Pipeline ETL/ELT de données hospitalières PMSI-MCO: Dagster, Polars, PostgreSQL, DBT | Analyse épidémio-économique : BPCO, Insuffisance Cardiaque, Tarifs ATIH 2026

## ⚠️ Nature des données

L'ensemble des résultats présentés dans ce projet (volumétrie des séjours, coûts ATIH, taux de réadmission) a été produit à partir d'un jeu de données **entièrement simulé** (`DATA_SET_SIMULE.csv`, environ 3 000 séjours), généré pour reproduire la structure et la volumétrie d'un export PMSI réel (NIP, NDA, GHM, GHS, codes CIM-10, dates de séjour). **Aucune donnée patient réelle n'a été utilisée à aucune étape de ce projet.** Ce choix garantit la conformité RGPD tout en permettant de démontrer un pipeline ETL/ELT complet sur un cas d'usage réaliste. Le fichier est disponible dans ce repo pour reproduire le pipeline de bout en bout.

## Avertissement méthodologique

La jointure entre les séjours et les tarifs ATIH est réalisée sur la clé GHS/GHM à titre purement démonstratif.

Dans un contexte de production réel, cette jointure devrait se baser sur une correspondance au NDA (numéro de séjour) couplée aux GHM via le fichier ATIH, afin d'éviter d'associer des tarifs de pathologies différentes partageant le même GHM. Un patient avec hépatite B et un patient avec insuffisance cardiaque peuvent partager le même GHM : notre jointure ramènerait alors un tarif incorrect.

Les résultats financiers présentés ne constituent pas une analyse médico-économique certifiée. Ils sont produits dans un contexte de démonstration technique, en l'absence des tables de correspondance CIM-10 vers GHM officielles.
