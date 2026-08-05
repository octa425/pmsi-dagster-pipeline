# ══════════════════════════════════════════════════════
# INTERFACE STREAMLIT — Agent IA PMSI
# Avec authentification utilisateur + monitoring tracé
# ══════════════════════════════════════════════════════

import streamlit as st
import sys
import os
import time
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag"))

from agent_llm_pmsi import generer_sql, verifier_requete, executer_sql, reformuler_reponse

# ── Configuration de la page ──
st.set_page_config(
    page_title="Agent IA PMSI",
    page_icon="🏥",
    layout="wide"
)

# ══════════════════════════════════════════════════════
# ÉTAPE 1 — AUTHENTIFICATION
# ══════════════════════════════════════════════════════
if "utilisateur" not in st.session_state:
    st.session_state["utilisateur"] = None
if st.session_state["utilisateur"] is None:

    st.title("🏥 Agent IA PMSI Connexion")
    st.caption("Veuillez vous identifier avant de continuer")
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Identification")
        nom    = st.text_input("Votre nom :")
        prenom = st.text_input("Votre prénom :")
        service = st.selectbox(
            "Votre service :",
            [
                "DIM :Département d'Information Médicale",
                "Cardiologie",
                "Urgences",
                "Direction",
                "Recherche",
                "Informatique",
                "Autre"
            ]
        )

        if st.button("Se connecter 🔐", use_container_width=True):
            if nom.strip() and prenom.strip():
                try:
                    conn_auth = psycopg2.connect(
                        host=os.environ["DB_HOST"],
                        database=os.environ["DB_NAME"],
                        user=os.environ["DB_USER"],
                        password=os.environ["DB_PASSWORD"]
                    )
                    cursor = conn_auth.cursor()
                    cursor.execute("""
                        SELECT id, nom, prenom, service
                        FROM pmsi_mco_analytics.users
                        WHERE UPPER(nom)    = UPPER(%s)
                        AND   UPPER(prenom) = UPPER(%s)
                        AND   actif = TRUE
                    """, (nom.strip(), prenom.strip()))

                    user = cursor.fetchone()
                    cursor.close()
                    conn_auth.close()

                    if user:
                        st.session_state["utilisateur"] = {
                            "nom"    : user[1],
                            "prenom" : user[2],
                            "service": user[3]
                        }
                        st.rerun()
                    else:
                        st.error(
                            "Utilisateur non autorisé. "
                            "Contactez l'administrateur."
                        )

                except Exception as e:
                    st.error(f"Erreur de connexion : {e}")
            else:
                st.error("Veuillez entrer votre nom et prénom !")

    st.stop()   # ← ICI — en dehors du with col2 !

if st.session_state["utilisateur"] is None:

    st.title("🏥 Agent IA PMSI : Connexion")
    st.caption("Veuillez vous identifier avant de continuer")
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Identification")
        nom    = st.text_input("Votre nom :")
        prenom = st.text_input("Votre prénom :")
        service = st.selectbox(
            "Votre service :",
            [
                "DIM: Département d'Information Médicale",
                "Cardiologie",
                "Urgences",
                "Direction",
                "Recherche",
                "Informatique",
                "Autre"
            ]
        )

        if st.button("Se connecter 🔐", use_container_width=True):
            if nom.strip() and prenom.strip():
                try:
                    conn_auth = psycopg2.connect(
                        host=os.environ["DB_HOST"],
                        database=os.environ["DB_NAME"],
                        user=os.environ["DB_USER"],
                        password=os.environ["DB_PASSWORD"]
                    )
                    cursor = conn_auth.cursor()
                    cursor.execute("""
                        SELECT id, nom, prenom, service
                        FROM pmsi_mco_analytics.users
                        WHERE UPPER(nom)    = UPPER(%s)
                        AND   UPPER(prenom) = UPPER(%s)
                        AND   actif = TRUE
                    """, (nom.strip(), prenom.strip()))

                    user = cursor.fetchone()
                    cursor.close()
                    conn_auth.close()

                    if user:
                        st.session_state["utilisateur"] = {
                            "nom"    : user[1],
                            "prenom" : user[2],
                            "service": user[3]
                        }
                        st.rerun()
                    else:
                        st.error(
                            "Utilisateur non autorisé. "
                            "Contactez l'administrateur."
                        )

                except Exception as e:
                    st.error(f"Erreur de connexion : {e}")
            else:
                st.error("Veuillez entrer votre nom et prénom !")

    st.stop()   # ← ICI — en dehors du with col2 !
# ══════════════════════════════════════════════════════
# ÉTAPE 2 — INTERFACE PRINCIPALE (après connexion)
# ══════════════════════════════════════════════════════

# Récupérer l'utilisateur connecté
utilisateur   = st.session_state["utilisateur"]
nom_complet   = f"{utilisateur['prenom']} {utilisateur['nom']}"
service       = utilisateur["service"]

# ── Titre principal ──
st.title("🏥 Agent IA PMSI Insuffisance Cardiaque")
st.caption(f"Connecté : {nom_complet}  {service} | 100% local RGPD")

# Bouton déconnexion
if st.button("Se déconnecter 🚪", key="deconnexion"):
    st.session_state["utilisateur"] = None
    st.session_state["historique"]  = []
    st.rerun()

st.divider()

# ── Sidebar ──
with st.sidebar:
    st.header("ℹ️ Informations")
    st.markdown(f"""
    **Utilisateur :** {nom_complet}
    
    **Service :** {service}
    
    **Base :** PostgreSQL `hopital`
    
    **Modèle :** llama3.2 (local)
    
    **Tables disponibles :**
    - `ic_couts_sejours` : 2 312 séjours IC
    - `dataset_ml` : Variables ML
    
    **Sécurité SQL :**
    - ✅ SELECT autorisé
    - ❌ DELETE bloqué
    - ❌ DROP bloqué
    - ❌ UPDATE bloqué
    """)

  # ── Monitoring ──
    st.divider()
    st.header("📈 Monitoring")

    if st.button("Voir les dernières traces", use_container_width=True):
        try:
            conn_monitoring = psycopg2.connect(
                host=os.environ["DB_HOST"],
                database=os.environ["DB_NAME"],
                user=os.environ["DB_USER"],
                password=os.environ["DB_PASSWORD"]
            )
            df_monitoring = pd.read_sql("""
                SELECT
                    utilisateur                        AS utilisateur,
                    LEFT(prompt, 35)                   AS question,
                    ROUND(duree_secondes::numeric, 1)  AS duree_s,
                    erreur_sql                         AS erreur,
                    message_erreur                     AS message
                FROM pmsi_mco_analytics.monitoring_llm
                ORDER BY horodatage DESC
                LIMIT 10
            """, conn_monitoring)
            conn_monitoring.close()
            st.dataframe(df_monitoring, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur monitoring : {e}")

    st.divider()
    st.header("💡 Exemples de questions")
    exemples = [
        "Quel est le coût moyen d'un séjour ?",
        "Combien de séjours au total ?",
        "Quel est le GHM le plus fréquent ?",
        "Quel GHM a le cout moyen le plus élevé ?",
        "Combien de séjours en janvier 2024 ?",
        "Quel est le tarif total ATIH ?",
        "Combien de séjours par unité médicale ?",
        "Combien de patients réadmis à J30 ?",
    ]
    for exemple in exemples:
        if st.button(exemple, use_container_width=True):
            st.session_state["question_selectionnee"] = exemple

# ── Initialiser session ──
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

# ── Traitement ──
if envoyer and question.strip():
    st.session_state["question_selectionnee"] = ""

    with st.spinner("L'agent réfléchit..."):
        debut = time.time()

        # Etape 1 — Génération SQL
        sql = generer_sql(question)

        # Etape 2 — Vérification sécurité
        valide, message_securite = verifier_requete(sql)

        if not valide:
            st.error(f"⛔ SÉCURITÉ : {message_securite}")
            st.code(sql, language="sql")

        elif "HORS_PERIMETRE" in sql.upper():
            st.warning("⚠️ Cette question est hors du périmètre des données disponibles.")

        elif "CONCEPT_ABSENT" in sql.upper():
            st.warning("⚠️ Ce concept n'existe pas dans les données disponibles.")

        else:
            try:
                # Etape 3 — Exécution PostgreSQL
                debut_pg = time.time()
                colonnes, resultats = executer_sql(sql)
                duree_pg = round(time.time() - debut_pg, 2)

                # Etape 4 — Reformulation
                debut_ref = time.time()
                reponse   = reformuler_reponse(
                    question, sql, colonnes, resultats
                )
                duree_ref = round(time.time() - debut_ref, 2)
                duree_sql = round(debut_pg - debut, 2)

                # Affichage réponse
                st.success(f"💬 {reponse}")

                # SQL généré
                with st.expander("🔍 Voir la requête SQL générée"):
                    st.code(sql, language="sql")
                    st.caption(
                        f"Génération SQL : {duree_sql}s | "
                        f"PostgreSQL : {duree_pg}s | "
                        f"Reformulation : {duree_ref}s"
                    )

                # Résultats bruts
                with st.expander("📊 Voir les résultats bruts"):
                    if resultats:
                        df = pd.DataFrame(resultats, columns=colonnes)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Aucun résultat retourné.")

                # Métriques
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Génération SQL", f"{duree_sql}s")
                with col_m2:
                    st.metric("PostgreSQL", f"{duree_pg}s")
                with col_m3:
                    st.metric("Reformulation", f"{duree_ref}s")

                # Ajouter à l'historique
                st.session_state["historique"].append({
                    "question"    : question,
                    "sql"         : sql,
                    "reponse"     : reponse,
                    "utilisateur" : nom_complet,
                    "duree"       : duree_sql + duree_pg + duree_ref
                })

            except Exception as e:
                st.error(f"❌ Erreur SQL : {e}")
                st.info("Essayez de reformuler votre question.")

# ── Historique ──
if st.session_state["historique"]:
    st.divider()
    st.subheader("📜 Historique de la session")

    for i, item in enumerate(reversed(st.session_state["historique"])):
        with st.expander(
            f"Q{len(st.session_state['historique'])-i} "
            f"— {item['utilisateur']} "
            f"— {item['question'][:50]}..."
        ):
            st.markdown(f"**Utilisateur :** {item['utilisateur']}")
            st.markdown(f"**Question :** {item['question']}")
            st.markdown(f"**Réponse :** {item['reponse']}")
            st.code(item["sql"], language="sql")
            st.caption(f"Durée totale : {round(item['duree'], 2)}s")

    if st.button("🗑️ Effacer l'historique"):
        st.session_state["historique"] = []
        st.rerun()

# ── Footer ──
st.divider()
st.caption(
    f"Agent IA PMSI {nom_complet} ({service}) — "
    "github.com/octa425/pmsi-dagster-pipeline — "
    "100% local - RGPD compliant"
)