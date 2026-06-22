# pmsi-dagster-pipeline

Pipeline ETL/ELT de données hospitalières PMSI-MCO — Dagster, Polars, PostgreSQL, DBT | Analyse épidémio-économique : BPCO, Insuffisance Cardiaque, Tarifs ATIH 2026

## ⚠️ Nature des données

L'ensemble des résultats présentés dans ce projet (volumétrie des séjours, coûts ATIH, taux de réadmission) a été produit à partir d'un jeu de données **entièrement simulé** (`DATA_SET_SIMULE.csv`, environ 3 000 séjours), généré pour reproduire la structure et la volumétrie d'un export PMSI réel (NIP, NDA, GHM, GHS, codes CIM-10, dates de séjour). **Aucune donnée patient réelle n'a été utilisée à aucune étape de ce projet.** Ce choix garantit la conformité RGPD tout en permettant de démontrer un pipeline ETL/ELT complet sur un cas d'usage réaliste. Le fichier est disponible dans ce repo pour reproduire le pipeline de bout en bout.

## Avertissement méthodologique

La jointure entre les séjours et les tarifs ATIH est réalisée sur la clé GHS/GHM à titre purement démonstratif.

Dans un contexte de production réel, cette jointure devrait se baser sur une correspondance au NDA (numéro de séjour) couplée aux GHM via le fichier ATIH, afin d'éviter d'associer des tarifs de pathologies différentes partageant le même GHM. Un patient avec hépatite B et un patient avec insuffisance cardiaque peuvent partager le même GHM — notre jointure ramènerait alors un tarif incorrect.

Les résultats financiers présentés ne constituent pas une analyse médico-économique certifiée. Ils sont produits dans un contexte de démonstration technique, en l'absence des tables de correspondance CIM-10 vers GHM officielles.
## 🚀 Démarrage rapide — Reproduire le pipeline

### Prérequis

- Windows 10/11 avec WSL2 activé
- Ubuntu 24.04 (via Microsoft Store)
- Python 3.11+
- Git
- Docker (optionnel)
- Ollama (optionnel pour l'agent IA)

---

### Étape 1 — Cloner le dépôt

```bash
git clone https://github.com/octa425/pmsi-dagster-pipeline.git
cd pmsi-dagster-pipeline
```

---

### Étape 2 — Installer PostgreSQL

```bash
sudo apt update
sudo apt install postgresql -y
sudo service postgresql start
```

Définir un mot de passe PostgreSQL :

```bash
sudo -u postgres psql
```

Puis dans psql :

```sql
ALTER USER postgres PASSWORD '<CHANGE_ME>';
\q
```

---

### Étape 3 — Créer la base de données

```bash
sudo -u postgres createdb hopital
```

Vérifier la création :

```bash
psql -h localhost -U postgres -l
```

---

### Étape 4 — Créer l'environnement virtuel

```bash
python3 -m venv dagster_env
source dagster_env/bin/activate
```

---

### Étape 5 — Installer les dépendances

```bash
pip install -r requirements_docker.txt
```

---

### Étape 6 — Lancer Dagster

```bash
dagster dev -f definitions_ic.py -h 0.0.0.0 -p 3000
```

Ouvrir ensuite **http://localhost:3000** puis cliquer sur **Materialize All**
afin d'exécuter l'ensemble du pipeline.

---

### Étape 7 — Vérifier les données chargées

```bash
psql -h localhost -U postgres -d hopital
```

```sql
SELECT COUNT(*) FROM pmsi_mco_analytics.ic_couts_sejours;
```

Le résultat attendu est **2 312 séjours** chargés dans PostgreSQL.

---

### Étape 8 — Lancer l'agent IA (optionnel)

Installer Ollama :

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Télécharger le modèle :

```bash
ollama pull llama3.2
```

Installer les dépendances Python :

```bash
pip install ollama psycopg2-binary
```

Lancer l'agent :

```bash
python3 agent_llm_pmsi.py
```

Exemples de questions :
Combien y a-t-il de séjours au total ?

Quel est le coût moyen d'un séjour ?

Quel est le coût total des séjours ?
L'agent :

1. Comprend la question en français
2. Génère automatiquement une requête SQL
3. Interroge PostgreSQL
4. Restitue la réponse en langage naturel

#### 🔒 Sécurité de l'agent IA

L'agent implémente un filtrage empêchant l'exécution de commandes destructrices :
`DROP` `DELETE` `UPDATE` `ALTER` `TRUNCATE` `CREATE` `GRANT` `REVOKE`

Exemple :
Question : DROP TABLE ic_couts_sejours

⛔ SECURITE : Requete refusee : contient 'DROP'
---

### Étape 9 — Docker (optionnel)

Construire l'image :

```bash
docker build -t pmsi-dagster .
```

Exécuter le conteneur :

```bash
docker run -p 3000:3000 pmsi-dagster
```

> **Remarque** : cette étape suppose qu'une instance PostgreSQL
> est disponible ou configurée via les variables d'environnement.

---

## 🛠️ Technologies utilisées

| Technologie | Usage |
|---|---|
| Python | Langage principal |
| PostgreSQL | Base de données relationnelle |
| Dagster | Orchestration du pipeline |
| Polars | Transformation des données |
| DBT | Modélisation SQL |
| Docker | Conteneurisation |
| GitHub Actions | CI/CD automatisé |
| Ollama + Llama 3.2 | Agent LLM local |
| Linux / WSL | Environnement d'exécution |

---
