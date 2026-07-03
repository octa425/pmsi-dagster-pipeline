"""
Retriever : recherche les documents les plus pertinents dans rag_documents
par rapport a une question posee en langage naturel.
"""
import ollama
import psycopg2

def rechercher_documents(question, top_k=3):
    """
    Transforme la question en embedding, puis cherche dans PostgreSQL
    les 'top_k' documents dont le vecteur est le plus proche (similarite cosinus).
    """
    reponse = ollama.embed(model="all-minilm", input=question)
    vecteur_question = reponse["embeddings"][0]

    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        dbname="hopital",
        user="postgres",
        password="MOT_DE_PASSE_SUPPRIME",
        options="-c search_path=pmsi_mco_analytics"
    )
    cur = conn.cursor()

    # L'operateur <=> de pgvector calcule la distance cosinus entre deux vecteurs.
    # Plus la distance est petite, plus les documents sont proches en sens.
    # On trie du plus proche au plus eloigne, et on garde les top_k premiers.
    cur.execute(
        """
        SELECT categorie, titre, contenu, embedding <=> %s::vector AS distance
        FROM rag_documents
        ORDER BY distance ASC
        LIMIT %s
        """,
        (vecteur_question, top_k)
    )
    resultats = cur.fetchall()

    cur.close()
    conn.close()

    return resultats


if __name__ == "__main__":
    question_test = "Que signifie le GHM 05M091 ?"
    resultats = rechercher_documents(question_test, top_k=3)

    print(f"Question : {question_test}\n")
    print(f"Documents les plus pertinents trouves :\n")
    for categorie, titre, contenu, distance in resultats:
        print(f"  [{categorie}] {titre}  (distance : {distance:.4f})")
    print()
    print("--- Contenu du document le plus pertinent ---")
    print(resultats[0][2][:300], "...")
