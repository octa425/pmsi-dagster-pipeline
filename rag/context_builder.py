"""
Context builder : transforme une liste de documents (resultats du retriever)
en un bloc de texte structure, pret a etre donne au LLM comme contexte.
"""

def construire_contexte(resultats_recherche):
    """
    resultats_recherche : liste de tuples (categorie, titre, contenu, distance)
    Retourne un texte structure listant chaque document source.
    """
    blocs = []
    for categorie, titre, contenu, distance in resultats_recherche:
        bloc = f"--- Document source : {titre} (categorie : {categorie}) ---\n{contenu}"
        blocs.append(bloc)
    return "\n\n".join(blocs)
