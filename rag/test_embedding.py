import os
"""
Script de test : vérifie qu'on peut bien générer un embedding
via Ollama et l'insérer dans PostgreSQL/pgvector, avant de lancer
l'ingestion complète des 34 documents.
"""
import ollama
import psycopg2

# --- 1. Lire un seul document de test ---
chemin_fichier = "documents/ghm/GHM_05M041.txt"
with open(chemin_fichier, "r", encoding="utf-8") as f:
    contenu = f.read()

print(f"Document lu : {chemin_fichier}")
print(f"Longueur du texte : {len(contenu)} caractères")

# --- 2. Générer l'embedding via Ollama ---
# ollama.embed() envoie le texte au modèle all-minilm, qui renvoie
# un vecteur de nombres représentant le "sens" du texte.
reponse = ollama.embed(model="all-minilm", input=contenu)
vecteur = reponse["embeddings"][0]

print(f"Embedding généré, dimension : {len(vecteur)}")
# On s'attend à 384 - si ce n'est pas le cas, la table SQL ne sera pas compatible

# --- 3. Se connecter à PostgreSQL et insérer ---
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=5432,
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    options="-c search_path=pmsi_mco_analytics"
)

cur = conn.cursor()

cur.execute(
    """
    INSERT INTO rag_documents (categorie, titre, contenu, embedding)
    VALUES (%s, %s, %s, %s)
    """,
    ("ghm", "GHM_05M041", contenu, vecteur)
)
conn.commit()

print("Insertion réussie dans rag_documents.")

cur.close()
conn.close()
