"""
Agent RAG complet : question -> recherche documentaire -> filtre de pertinence
-> contexte -> reponse LLM.
Le LLM n'est appele que si au moins un document est juge suffisamment pertinent.
"""
from retriever import rechercher_documents
from context_builder import construire_contexte
from generator import generer_reponse

# Seuil de distance cosinus en dessous duquel on considere qu'un document
# est pertinent. Determine empiriquement sur nos tests :
#   - question dans le corpus  -> meilleure distance ~0.46
#   - question hors corpus     -> meilleure distance ~0.63
# Seuil fixe entre les deux. A ajuster si le corpus grandit.
SEUIL_PERTINENCE = 0.55

def repondre(question, top_k=3):
    print(f"[1/3] Recherche des documents pertinents pour : {question}")
    resultats = rechercher_documents(question, top_k=top_k)
    for categorie, titre, contenu, distance in resultats:
        print(f"       - [{categorie}] {titre} (distance {distance:.4f})")

    meilleure_distance = resultats[0][3]

    if meilleure_distance > SEUIL_PERTINENCE:
        reponse = (
            "Cette question semble hors du perimetre documentaire disponible "
            "(aucun document suffisamment pertinent trouve). "
            "Le systeme n'a pas sollicite le modele de langage pour eviter "
            "toute reponse non fiable."
        )
        print(f"\n[FILTRE] Distance minimale ({meilleure_distance:.4f}) > seuil ({SEUIL_PERTINENCE}) : LLM non appele.\n")
        print("=== REPONSE ===")
        print(reponse)
        return reponse

    print("[2/3] Construction du contexte...")
    contexte = construire_contexte(resultats)

    print("[3/3] Generation de la reponse via llama3.2...\n")
    reponse = generer_reponse(question, contexte)

    print("=== REPONSE ===")
    print(reponse)
    return reponse

if __name__ == "__main__":
    repondre("Que signifie le GHM 05M091 ?")
