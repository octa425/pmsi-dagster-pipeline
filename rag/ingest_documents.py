"""
Ingestion complete du corpus documentaire RAG :
lit tous les fichiers .txt du dossier documents/, genere leur embedding
via Ollama (all-minilm), et les insere dans PostgreSQL/pgvector.
"""
import os
from dotenv import load_dotenv
load_dotenv()
import ollama
import psycopg2

DOSSIER_DOCUMENTS = "documents"

CATEGORIES = {
    "ghm": "ghm",
    "cim10": "cim10",
    "comptes_rendus": "compte_rendu",
    "procedures": "procedure",
    "referentiels": "referentiel",
}

def lister_fichiers():
    fichiers = []
    for sous_dossier, categorie in CATEGORIES.items():
        chemin_dossier = os.path.join(DOSSIER_DOCUMENTS, sous_dossier)
        if not os.path.isdir(chemin_dossier):
            continue
        for nom_fichier in sorted(os.listdir(chemin_dossier)):
            if nom_fichier.endswith(".txt"):
                chemin_complet = os.path.join(chemin_dossier, nom_fichier)
                titre = nom_fichier.replace(".txt", "")
                fichiers.append((chemin_complet, categorie, titre))
    return fichiers

def main():
    fichiers = lister_fichiers()
    print(f"{len(fichiers)} documents trouves a ingerer.\n")

    conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=5432,
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    options="-c search_path=pmsi_mco_analytics"
)
    cur = conn.cursor()

    cur.execute("TRUNCATE TABLE rag_documents RESTART IDENTITY;")
    conn.commit()
    print("Table rag_documents videe (reset propre avant ingestion).\n")

    for chemin, categorie, titre in fichiers:
        with open(chemin, "r", encoding="utf-8") as f:
            contenu = f.read()

        reponse = ollama.embed(model="all-minilm", input=contenu)
        vecteur = reponse["embeddings"][0]

        cur.execute(
            """
            INSERT INTO rag_documents (categorie, titre, contenu, embedding)
            VALUES (%s, %s, %s, %s)
            """,
            (categorie, titre, contenu, vecteur)
        )
        print(f"  OK : [{categorie}] {titre}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nIngestion terminee : {len(fichiers)} documents inseres dans rag_documents.")

if __name__ == "__main__":
    main()
