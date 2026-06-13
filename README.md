# pmsi-dagster-pipeline
Pipeline ETL/ELT de données hospitalières PMSI-MCO — Dagster, Polars, PostgreSQL, DBT | Analyse épidémio-économique : BPCO, Insuffisance Cardiaque, Tarifs ATIH 2026
## Avertissement méthodologique

La jointure entre les séjours et les tarifs ATIH est realisee
sur la cle GHS/GHM a titre purement demonstratif.

Dans un contexte de production reel, cette jointure devrait
se baser sur une correspondance stricte CIM-10 vers GHM via
les outils officiels ATIH (GENRSA, MAGIC), afin d'eviter
d'associer des tarifs de pathologies differentes partageant
le meme GHM.

Un patient avec hepatite B et un patient avec insuffisance
cardiaque peuvent partager le meme GHM - notre jointure
ramenerait alors un tarif incorrect.

Les resultats financiers presentes ne constituent pas
une analyse medico-economique certifiee. Ils sont produits
dans un contexte de demonstration technique, en l'absence
des tables de correspondance CIM-10 vers GHM officielles.
