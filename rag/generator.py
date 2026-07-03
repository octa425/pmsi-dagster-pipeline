"""
Generator : envoie la question + le contexte documentaire au LLM local
(llama3.2 via Ollama) et retourne une reponse redigee, en citant les sources.
"""
import ollama

PROMPT_SYSTEME = """Tu es un assistant medico-administratif specialise dans le PMSI (Programme de Medicalisation des Systemes d'Information).
Reponds a la question de l'utilisateur UNIQUEMENT a partir des documents sources fournis ci-dessous.
Si les documents ne contiennent pas l'information necessaire, dis-le clairement plutot que d'inventer une reponse.
Cite le nom du document source utilise dans ta reponse.
Reponds en francais, de maniere claire et concise."""

def generer_reponse(question, contexte):
    prompt_utilisateur = f"""Documents sources :
{contexte}

Question : {question}"""

    reponse = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": PROMPT_SYSTEME},
            {"role": "user", "content": prompt_utilisateur},
        ],
    )
    return reponse["message"]["content"]
