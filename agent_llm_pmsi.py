import ollama
import psycopg2

# ──────────────────────────────────────────────
# Configuration PostgreSQL
# ──────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "database": "hopital",
    "user": "postgres",
    "password": "airflow2026"
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

2. pmsi_mco_analytics.dataset_ml
   - nip, nda, date_entree, dp, pathologie
   - nb_sejours_precedents (integer)
   - readmis_30j (integer: 0 ou 1)

Toutes les donnees concernent l'Insuffisance Cardiaque (codes I50*).
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

Question : {question}

SQL :"""

    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}]
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

Reponds en francais de facon claire et concise en donnant les chiffres exacts.
Ne mentionne pas la requete SQL dans ta reponse."""

    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"].strip()

# ──────────────────────────────────────────────
# Agent principal
# ──────────────────────────────────────────────
def agent_pmsi(question):
    print(f"\nQuestion : {question}")
    print("-" * 50)

    sql = generer_sql(question)

    valide, message = verifier_requete(sql)
    if not valide:
        print(f"⛔ SECURITE : {message}")
        return

    try:
        colonnes, resultats = executer_sql(sql)
        reponse = reformuler_reponse(question, sql, colonnes, resultats)
        print(f"Reponse : {reponse}")

    except Exception as e:
        print(f"Erreur : {e}")

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