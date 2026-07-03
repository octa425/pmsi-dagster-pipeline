"""
Routeur : analyse une question en langage naturel et decide vers quelle(s)
strategie(s) de reponse l'envoyer : Text-to-SQL, RAG, ou les deux.

Choix d'architecture : routeur a regles explicites (mots-cles), pas un
classifieur ML. Plus simple, plus rapide, et surtout entierement explicable :
chaque decision peut etre justifiee ligne par ligne.
"""

MOTS_CLES_SQL = [
    "combien", "nombre", "cout", "coût", "moyenne", "taux",
    "total", "somme", "pourcentage", "statistique", "duree moyenne",
    "durée moyenne", "compte", "quantite", "quantité",
]

MOTS_CLES_RAG = [
    "que signifie", "qu'est-ce que", "qu'est ce que", "pourquoi",
    "definition", "définition", "explique", "c'est quoi",
    "que veut dire", "a quoi correspond", "à quoi correspond",
]

def detecter_intention(question):
    """
    Retourne 'sql', 'rag' ou 'hybride' selon les mots-cles presents
    dans la question (recherche insensible a la casse).
    """
    question_normalisee = question.lower()

    contient_sql = any(mot in question_normalisee for mot in MOTS_CLES_SQL)
    contient_rag = any(mot in question_normalisee for mot in MOTS_CLES_RAG)

    if contient_sql and contient_rag:
        return "hybride"
    elif contient_sql:
        return "sql"
    elif contient_rag:
        return "rag"
    else:
        # Par defaut, si aucun mot-cle ne matche clairement,
        # on part sur le RAG : plus prudent qu'un SQL par defaut
        # (un mauvais SQL peut renvoyer un resultat trompeur sans le signaler,
        # alors que le RAG a son propre garde-fou de pertinence).
        return "rag"


if __name__ == "__main__":
    questions_test = [
        "Combien de séjours pour insuffisance cardiaque en 2026 ?",
        "Que signifie le GHM 05M091 ?",
        "Combien de séjours sont classés en 05M091 et à quoi correspond ce GHM ?",
        "Quel est le coût moyen des séjours BPCO ?",
    ]

    for q in questions_test:
        intention = detecter_intention(q)
        print(f"[{intention.upper():8}] {q}")
