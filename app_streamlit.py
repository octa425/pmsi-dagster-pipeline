# ══════════════════════════════════════════════════════
# INTERFACE STREAMLIT — Agent IA PMSI
# Permet d'interroger PostgreSQL en langage naturel
# via une interface web simple et démontrable
# ══════════════════════════════════════════════════════

import streamlit as st
import sys
import os
import time

# Ajouter le dossier rag/ au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag"))

# Import de l'agent
from agent_llm_pmsi import generer_sql, verifier_requete, executer_sql, reformuler_reponse

# ── Configuration de la page ──
st.set_page_config(
    page_title="Agent IA PMSI",
    page_icon="🏥",
    layout="wide"
)

# ── Titre principal ──
st.title("🏥 Agent IA PMSI Insuffisance Cardiaque")
st.caption("Interrogez la base PostgreSQL en langage naturel:  100% local RGPD")

# ── Séparateur ──
st.divider()

# ── Sidebar — Informations ──
with st.sidebar:
    st.header("ℹ️ Informations")
    st.markdown("""
    **Base de données :** PostgreSQL `hopital`
    
    **Modèle LLM :** llama3.2 (local)
    
    **Tables disponibles :**
    - `ic_couts_sejours` — 2 312 séjours IC
    - `dataset_ml` — Variables ML
    
    **Sécurité SQL :**
    - ✅ SELECT autorisé
    - ❌ DELETE bloqué
    - ❌ DROP bloqué
    - ❌ UPDATE bloqué
    """)

    st.divider()
    st.header("💡 Exemples de questions")
    exemples = [
        "Quel est le coût moyen d'un séjour ?",
        "Combien de séjours au total ?",
        "Quel est le GHM le plus fréquent ?",
        "Combien de patients ont été réadmis à J30 ?",
        "Quelle est la durée moyenne de séjour ?",
        "Quel est le coût total de tous les séjours ?",
        "Combien de femmes dans la cohorte ?",
        "Quel est l'âge moyen des patients ?",
    ]
    for exemple in exemples:
        if st.button(exemple, use_container_width=True):
            st.session_state["question_selectionnee"] = exemple

# ── Initialiser l'historique ──
if "historique" not in st.session_state:
    st.session_state["historique"] = []

if "question_selectionnee" not in st.session_state:
    st.session_state["question_selectionnee"] = ""

# ── Zone de saisie ──
col1, col2 = st.columns([4, 1])

with col1:
    question = st.text_input(
        "Votre question :",
        value=st.session_state["question_selectionnee"],
        placeholder="Ex: Quel est le coût moyen d'un séjour ?",
        key="input_question"
    )

with col2:
    st.write("")
    st.write("")
    envoyer = st.button("Envoyer 🚀", use_container_width=True)

# ── Traitement de la question ──
if envoyer and question.strip():

    # Reset question selectionnee
    st.session_state["question_selectionnee"] = ""

    with st.spinner("L'agent réfléchit..."):

        # Etape 1 — Génération SQL
        debut = time.time()
        sql = generer_sql(question)
        duree_llm_sql = round(time.time() - debut, 2)

        # Etape 2 — Vérification sécurité
        valide, message_securite = verifier_requete(sql)

        if not valide:
            # Alerte sécurité
            st.error(f"⛔ SÉCURITÉ : {message_securite}")
            st.code(sql, language="sql")

        else:
            # Etape 3 — Exécution PostgreSQL
            try:
                debut_pg = time.time()
                colonnes, resultats = executer_sql(sql)
                duree_pg = round(time.time() - debut_pg, 2)

                # Etape 4 — Reformulation
                debut_reformul = time.time()
                reponse = reformuler_reponse(
                    question, sql, colonnes, resultats
                )
                duree_reformul = round(time.time() - debut_reformul, 2)

                # ── Affichage de la réponse ──
                st.success(f"💬 {reponse}")

                # ── Transparence — SQL généré ──
                with st.expander("🔍 Voir la requête SQL générée"):
                    st.code(sql, language="sql")
                    st.caption(f"Génération SQL : {duree_llm_sql}s | "
                               f"PostgreSQL : {duree_pg}s | "
                               f"Reformulation : {duree_reformul}s")

                # ── Résultats bruts ──
                with st.expander("📊 Voir les résultats bruts"):
                    if resultats:
                        import pandas as pd
                        df = pd.DataFrame(resultats, columns=colonnes)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Aucun résultat retourné.")

                # ── Métriques ──
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Génération SQL", f"{duree_llm_sql}s")
                with col_m2:
                    st.metric("Exécution PostgreSQL", f"{duree_pg}s")
                with col_m3:
                    st.metric("Reformulation", f"{duree_reformul}s")

                # ── Ajouter à l'historique ──
                st.session_state["historique"].append({
                    "question" : question,
                    "sql"      : sql,
                    "reponse"  : reponse,
                    "duree"    : duree_llm_sql + duree_pg + duree_reformul
                })

            except Exception as e:
                st.error(f"❌ Erreur SQL : {e}")
                st.info("Essayez de reformuler votre question.")

# ── Historique des questions ──
if st.session_state["historique"]:
    st.divider()
    st.subheader("📜 Historique de la session")

    for i, item in enumerate(reversed(
        st.session_state["historique"]
    )):
        with st.expander(
            f"Q{len(st.session_state['historique'])-i} — "
            f"{item['question'][:60]}..."
        ):
            st.markdown(f"**Question :** {item['question']}")
            st.markdown(f"**Réponse :** {item['reponse']}")
            st.code(item['sql'], language="sql")
            st.caption(f"Durée totale : {round(item['duree'], 2)}s")

    # Bouton effacer historique
    if st.button("🗑️ Effacer l'historique"):
        st.session_state["historique"] = []
        st.rerun()

# ── Footer ──
st.divider()
st.caption(
    "Agent IA PMSI — Octavien YAMESSE — "
    "github.com/octa425/pmsi-dagster-pipeline — "
    "100% local — RGPD compliant"
)
