# pmsi-dagster-pipeline
Pipeline ETL/ELT de données hospitalières PMSI-MCO — Dagster, Polars, PostgreSQL, DBT | Analyse épidémio-économique : BPCO, Insuffisance Cardiaque, Tarifs ATIH 2026
## Avertissement méthodologique

La jointure entre les séjours et les tarifs ATIH est realisee
sur la cle GHS/GHM a titre purement demonstratif.

Dans un contexte de production reel, cette jointure devrait
se baser sur une correspondance au NDA qui est le numéro de séjour et les GHM via le fichier ATIH pour éviter 
d'associer des tarifs de pathologies differentes partageant
le meme GHM.

Un patient avec hepatite B et un patient avec insuffisance
cardiaque peuvent partager le meme GHM - notre jointure
ramenerait alors un tarif incorrect.

Les resultats financiers presentes ne constituent pas
une analyse medico-economique certifiee. Ils sont produits
dans un contexte de demonstration technique, en l'absence
des tables de correspondance CIM-10 vers GHM officielles.
**Mode Entraînement :** Pour tester et exécuter ce pipeline Dagster, un jeu de données réaliste de près de 3 000 séjours simulés est mis à disposition directement dans le fichier `DATA_SET_SIMULE.csv`. Vous pouvez le télécharger pour vous exercer !
