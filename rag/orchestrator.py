"""
Orchestrateur final : point d'entree unique de l'agent PMSI hybride.
Utilise le routeur pour decider de la strategie, puis appelle le RAG
et/ou le Text-to-SQL en consequence.

Architecture :
    Question -> Router -> [SQL] et/ou [RAG] -> Reponse finale
"""
import sys
import os

# Permet d'importer agent_llm_pmsi.py qui se trouve un dossier au-dessus
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from router import detecter_intention
from agent_rag import repondre as repondre_rag
from agent_llm_pmsi import agent_pmsi as repondre_sql


def repondre(question):
    intention = detecter_intention(question)
    print(f"[ROUTEUR] Question orientee vers : {intention.upper()}\n")

    if intention == "sql":
        reponse = repondre_sql(question)
        return f"[Reponse via Text-to-SQL]\n{reponse}"

    elif intention == "rag":
        reponse = repondre_rag(question)
        return f"[Reponse via RAG documentaire]\n{reponse}"

    else:  # hybride
        print("--- Partie SQL ---")
        reponse_sql = repondre_sql(question)
        print("\n--- Partie RAG ---")
        reponse_rag = repondre_rag(question)

        return (
            f"[Reponse combinee SQL + RAG]\n\n"
            f"Donnees chiffrees (SQL) :\n{reponse_sql}\n\n"
            f"Contexte documentaire (RAG) :\n{reponse_rag}"
        )


if __name__ == "__main__":
    print("Agent PMSI hybride (SQL + RAG) - Tapez 'quitter' pour arreter")
    print("=" * 60)

    while True:
        question = input("\nVotre question : ").strip()
        if question.lower() == "quitter":
            print("Au revoir !")
            break
        if not question:
            continue

        reponse_finale = repondre(question)
        print(f"\n=== REPONSE FINALE ===\n{reponse_finale}")
