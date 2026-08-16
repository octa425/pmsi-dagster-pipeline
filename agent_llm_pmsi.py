import os
import ollama
import psycopg2
from dotenv import load_dotenv
from monitoring import enregistrer_trace
import time

load_dotenv()

# ──────────────────────────────────────────────
# Configuration PostgreSQL (variables d'environnement, voir .env)
# ──────────────────────────────────────────────
DB_CONFIG = {

    "host": os.environ["DB_HOST"],
    "database": os.environ["DB_NAME"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"]
}

# ──────────────────────────────────────────────
# Mots interdits - Securite
# ──────────────────────────────────────────────
MOTS_INTERDITS = [
    "DELETE", "DROP", "TRUNCATE",
    "INSERT", "UPDATE", "ALTER",
    "CREATE", "GRANT", "REVOKE"
]

def verifier_requete(sql):
    sql_upper = sql.upper()
    for mot in MOTS_INTERDITS:
        if mot in sql_upper:
            return False, f"Requete refusee : contient '{mot}'"
    return True, "OK"

# ──────────────────────────────────────────────
# Schema de la base pour le LLM
# ──────────────────────────────────────────────
SCHEMA_BD = """
Tables disponibles dans PostgreSQL (base: hopital) :

1. pmsi_mco_analytics.ic_couts_sejours
   - nip (text) : identifiant patient
   - nda (text) : numero de sejour
   - dp (text) : diagnostic principal CIM-10
   - ghm (text) : groupe homogene de malades
   - ghs (text) : groupe homogene de sejours
   - date_entree (date) : date d'entree
   - date_sortie (date) : date de sortie
   - tarif_base (numeric) : tarif ATIH en euros
   - cout_sejour (numeric) : cout total du sejour
   
   # Après la description des colonnes, ajouter :

EXEMPLES DE REQUETES CORRECTES :
-- Femmes (sexe = 2) :
SELECT COUNT(*) FROM pmsi_mco_analytics.ic_couts_sejours WHERE sexe = 2;

-- Hommes (sexe = 1) :
SELECT COUNT(*) FROM pmsi_mco_analytics.ic_couts_sejours WHERE sexe = 1;

-- Cout total :
SELECT SUM(cout_sejour) FROM pmsi_mco_analytics.ic_couts_sejours;

-- Age moyen :
SELECT AVG(age) FROM pmsi_mco_analytics.ic_couts_sejours;

-- Duree moyenne :
SELECT AVG(duree_sejour) FROM pmsi_mco_analytics.ic_couts_sejours;

2. pmsi_mco_analytics.dataset_ml
   - nip, nda, date_entree, dp, pathologie
   - nb_sejours_precedents (integer)
   - readmis_30j (integer: 0 ou 1)

Toutes les donnees concernent l'Insuffisance Cardiaque (codes I50*).

IMPORTANT - Format exact des codes CIM-10 dans la colonne dp :
Les valeurs sont stockees SANS point et SANS tiret, sur 4 caracteres exacts.
Exemples de valeurs reelles presentes dans la table : I500, I501, I509, E119, J440.

Pour chercher TOUS les sejours d'une famille de diagnostics (ex : tous les I50.x),
utilise TOUJOURS un prefixe avec LIKE, jamais une egalite stricte :
  Correct   : WHERE dp LIKE 'I50%'
  Incorrect : WHERE dp = 'I50-'  (ne matchera jamais rien, ce format n'existe pas)
  Incorrect : WHERE dp = 'I50.x' (le point n'existe pas dans les donnees)

Pour chercher un code precis (ex : uniquement I50.9), utilise l'egalite stricte
avec le code complet exact : WHERE dp = 'I509'
"""

# ──────────────────────────────────────────────
# Generer le SQL depuis la question
# ──────────────────────────────────────────────
def generer_sql(question):
    prompt = f"""Tu es un expert SQL PostgreSQL specialise en donnees hospitalieres PMSI.

{SCHEMA_BD}

REGLES ABSOLUES :
- Tu generes UNIQUEMENT des requetes SELECT ou COUNT
- Tu n'utilises JAMAIS DELETE, DROP, UPDATE, INSERT, ALTER
- Tu reponds UNIQUEMENT avec la requete SQL, sans explication
- Pas de markdown, pas de backticks, juste le SQL pur
- Le FROM doit TOUJOURS utiliser le nom complet schema.table, jamais le schema seul.
  Exemple correct   : FROM pmsi_mco_analytics.ic_couts_sejours
  Exemple incorrect : FROM pmsi_mco_analytics

IMPORTANT - Regroupement (GROUP BY) :
Des que tu selectionnes une colonne agregee (COUNT, AVG, SUM...) EN MEME TEMPS
qu'une colonne normale (comme dp, ghm, urmp), tu dois OBLIGATOIREMENT ajouter
un GROUP BY sur cette colonne normale, sinon la requete echoue.
  Correct   : SELECT dp, COUNT(*) FROM ic_couts_sejours GROUP BY dp
  Incorrect : SELECT dp, COUNT(*) FROM ic_couts_sejours
Si tu veux juste un total sans repartition, ne selectionne PAS la colonne
normale : SELECT COUNT(*) FROM ic_couts_sejours

IMPORTANT - Sous-requetes correlees (comparaison a une moyenne PAR GROUPE) :
Si la question compare une valeur a la moyenne d'un GROUPE precis (ex: "superieur
a la moyenne du meme GHM", "au-dessus de la moyenne de son unite"), la sous-requete
DOIT etre correlee avec la ligne externe via un alias explicite. Un simple GROUP BY
isole dans la sous-requete est INCORRECT et provoque une erreur SQL (plusieurs
lignes renvoyees au lieu d'une seule valeur).
  Correct   : SELECT * FROM ic_couts_sejours a WHERE cout_sejour > (
                  SELECT AVG(cout_sejour) FROM ic_couts_sejours b WHERE b.ghm = a.ghm)
  Incorrect : SELECT * FROM ic_couts_sejours WHERE cout_sejour > (
                  SELECT AVG(cout_sejour) FROM ic_couts_sejours GROUP BY ghm)
Si la comparaison est a la moyenne GLOBALE (pas par groupe), une sous-requete simple
suffit, sans alias ni correlation :
  SELECT * FROM ic_couts_sejours WHERE cout_sejour > (SELECT AVG(cout_sejour) FROM ic_couts_sejours)

IMPORTANT - Perimetre des donnees disponibles :
Les tables ci-dessus ne contiennent QUE des donnees sur l'insuffisance cardiaque
en France (pas d'autres pays, pas d'autres pathologies que celles listees).
Si la question porte sur un sujet que ce schema ne permet manifestement pas
de traiter (autre pays, autre pathologie totalement absente du schema, sujet
sans rapport avec des sejours hospitaliers), reponds UNIQUEMENT avec le mot :
HORS_PERIMETRE
Ne genere PAS de requete SQL approximative dans ce cas - il vaut mieux
signaler l'incapacite a repondre que de produire une requete qui risque
d'echouer ou de renvoyer un resultat trompeur.

IMPORTANT - Concepts absents du schema (different de HORS_PERIMETRE) :
Certaines questions restent dans le domaine general (patients, sejours,
insuffisance cardiaque) mais portent sur un CONCEPT PRECIS qui n'a AUCUNE
colonne correspondante dans le schema ci-dessus. Ne genere JAMAIS une
requete qui approxime ou remplace ce concept par une colonne proche mais
differente.
Exemples de concepts ABSENTS du schema :
  - "mortalite", "deces", "taux de deces" -> n'existe pas (readmis_30j est
    la READMISSION, pas la mortalite, ne pas confondre)
  - "erreur de codage", "sejour mal code" -> n'existe pas
  - "soins critiques" comme categorie -> n'existe pas comme valeur de ghm/ghs
Si la question porte sur un concept absent (ou clairement similaire non
couvert), reponds UNIQUEMENT avec le mot :
CONCEPT_ABSENT

RAPPEL FINAL AVANT DE REPONDRE :
- Le FROM doit imperativement utiliser le nom complet pmsi_mco_analytics.nom_table
- Ne remplace jamais un concept absent (mortalite) par une colonne existante
  qui mesure autre chose (readmis_30j = readmission, pas mortalite)
- Si comparaison a une moyenne PAR GROUPE (ex: "moyenne du meme GHM") : la
  sous-requete doit utiliser DEUX alias distincts de la meme table (a et b),
  relies par WHERE b.colonne_groupe = a.colonne_groupe. Ne jamais mettre
  GROUP BY seul dans une sous-requete de comparaison, ca renvoie plusieurs
  lignes et fait echouer la requete.

Question : {question}
# Dans agent_llm_pmsi.py, ajouter dans SCHEMA_BD :

EXEMPLES SUPPLEMENTAIRES :
-- Sejours par unite medicale (urmp = Unite Medicale) :
SELECT urmp, COUNT(*) FROM pmsi_mco_analytics.ic_couts_sejours GROUP BY urmp;

-- Sejours en janvier 2024 (date est de type DATE, pas TEXT) :
SELECT COUNT(*) FROM pmsi_mco_analytics.ic_couts_sejours
WHERE EXTRACT(MONTH FROM date_entree) = 1
AND EXTRACT(YEAR FROM date_entree) = 2024;

-- Sejours de plus de 10 jours (duree_sejour est TEXT, cast obligatoire) :
SELECT COUNT(*) FROM pmsi_mco_analytics.ic_couts_sejours
WHERE CAST(duree_sejour AS INTEGER) > 10;

-- Patients readmis a J30 (readmis_30j = 1 dans dataset_ml, J30 = 30 jours pas un code CIM) :
SELECT COUNT(*) FROM pmsi_mco_analytics.dataset_ml
WHERE readmis_30j = 1;

SQL :"""

    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1}
        # Temperature basse (proche de 0) : reduit la variabilite du SQL genere.
        # On privilegie ici la reproductibilite a la creativite, ce qui est
        # le bon compromis pour une tache de generation de code structure.
    )
    return response["message"]["content"].strip()

# ──────────────────────────────────────────────
# Executer la requete SQL
# ──────────────────────────────────────────────
def executer_sql(sql):
    # Securite : ajouter LIMIT si absent
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip(";") + " LIMIT 100;"
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(sql)
    colonnes = [desc[0] for desc in cursor.description]
    resultats = cursor.fetchall()
    cursor.close()
    conn.close()
    return colonnes, resultats
# ──────────────────────────────────────────────
# Reformuler la reponse en francais
# ──────────────────────────────────────────────
def reformuler_reponse(question, sql, colonnes, resultats):
    prompt = f"""Tu es un assistant specialise en donnees hospitalieres.

Question posee : {question}
Requete executee : {sql}
Colonnes : {colonnes}
Resultats : {resultats}

REGLES STRICTES :
- Reponds en francais, de facon claire et concise, en donnant les chiffres exacts.
- Ne mentionne PAS la requete SQL dans ta reponse.
- N'ajoute AUCUNE explication medicale, definition ou connaissance generale
  qui ne provient pas directement des resultats fournis ci-dessus.
- Limite-toi strictement a reformuler le resultat chiffre en une phrase.
- Si la question demande une definition ou un "pourquoi", indique que cette
  information n'est pas disponible via cette source de donnees chiffrees."""

    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"].strip()

# ──────────────────────────────────────────────
# Agent principal
# ──────────────────────────────────────────────

def agent_pmsi(question):
    debut = time.time()
    erreur = False
    message_erreur = None
    reponse = None

    try:
        sql = generer_sql(question)

        if "HORS_PERIMETRE" in sql.upper():
            reponse = ("Cette question porte sur un sujet hors du perimetre des "
                       "donnees disponibles (insuffisance cardiaque, France). "
                       "Aucune requete n'a ete executee.")
            print(reponse)
            fin = time.time()
            enregistrer_trace(question, reponse, fin - debut, "SQL", False, "hors_perimetre")
            return reponse

        if "CONCEPT_ABSENT" in sql.upper():
            reponse = ("Cette question porte sur un concept qui n'existe pas dans "
                       "les donnees disponibles (par exemple la mortalite, alors que "
                       "seule la readmission a 30 jours est mesuree). Aucune requete "
                       "n'a ete executee pour eviter une reponse trompeuse.")
            print(reponse)
            fin = time.time()
            enregistrer_trace(question, reponse, fin - debut, "SQL", False, "concept_absent")
            return reponse

        valide, message = verifier_requete(sql)
        if not valide:
            raise Exception(message)
        colonnes, resultats = executer_sql(sql)
        reponse = reformuler_reponse(question, sql, colonnes, resultats)
        print(f"Réponse : {reponse}")
    except Exception as e:
        erreur = True
        message_erreur = str(e)
        reponse = f"Erreur lors de l'execution SQL : {e}"
        print(f"Erreur : {e}")

    fin = time.time()
    duree = fin - debut
    enregistrer_trace(question, reponse, duree, "SQL", erreur, message_erreur)

    return reponse

# ──────────────────────────────────────────────
# Test avec plusieurs questions
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("Agent LLM PMSI - Interrogation en langage naturel")
    print("=" * 60)
    print("Tapez 'quitter' pour arreter l'agent")
    print()

    while True:
        question = input("Votre question : ").strip()
        
        if question.lower() == "quitter":
            print("Au revoir !")
            break
            
        if not question:
            continue
            
        agent_pmsi(question)
        print()