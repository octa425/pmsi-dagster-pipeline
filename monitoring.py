import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def enregistrer_trace(prompt, reponse, duree, type_requete, erreur, message_erreur):
    """
    Enregistre une trace d'appel LLM dans la table monitoring_llm :
    prompt envoyé, réponse obtenue, durée, type de requête,
    et éventuelle erreur rencontrée.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO pmsi_mco_analytics.monitoring_llm
        (prompt, reponse, duree_secondes, type_requete, erreur_sql, message_erreur)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (prompt, reponse, duree, type_requete, erreur, message_erreur)
    )
    conn.commit()
    cursor.close()
    conn.close()
