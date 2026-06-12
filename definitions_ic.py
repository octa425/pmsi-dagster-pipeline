import psycopg2
import polars as pl
import pandas as pd
import csv
from datetime import datetime
from dagster import asset, Definitions


# ──────────────────────────────────────────────
# ASSET 1 — Lecture brute du CSV MCO
# ──────────────────────────────────────────────
@asset
def raw_mco_ic():
    """
    Lit le fichier CSV MCO et extrait toutes les colonnes
    utiles dont GHM et GHS pour la jointure ATIH.
    """
    fichier = "/mnt/d/BUREAU/EX780762_RAP_CCH_2021_22_8_2022.csv"

    with open(fichier, "r", encoding="windows-1252") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

    colonnes_voulues = [
        "NIP", "NDA", "URMP",
        "CIM principal", "Diag Relie", "Diag Rsm",
        "GHM", "GHS", "Duree sejour",
        "Date entree dossier", "Date sortie dossier"
    ]
    colonnes_voulues += [f"CIM SIGN {i}" for i in range(1, 100)]

    indices = []
    noms_colonnes_reels = []
    for col in colonnes_voulues:
        if col in header:
            indices.append(header.index(col))
            noms_colonnes_reels.append(col)

    print(f"Colonnes retenues : {len(indices)}")

    donnees = []
    with open(fichier, "r", encoding="windows-1252") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        for i, row in enumerate(reader):
            try:
                ligne = [row[idx] if idx < len(row) else "" for idx in indices]
                donnees.append(ligne)
            except Exception:
                pass
            if i % 50000 == 0 and i > 0:
                print(f"{i} lignes lues...")

    df = pl.DataFrame(donnees, schema=noms_colonnes_reels, orient="row")
    print(f"Lignes brutes lues : {df.height}")
    return df


# ──────────────────────────────────────────────
# ASSET 2 — Filtre Insuffisance Cardiaque (I50)
# ──────────────────────────────────────────────
@asset
def filter_insuffisance_cardiaque(raw_mco_ic):
    """
    Filtre les séjours avec un code CIM-10 I50*
    dans DP, DR, RSM ou n'importe quel DAS.
    Convertit les dates et garde GHM + GHS.
    """
    df = raw_mco_ic

    # Renommage
    rename_map = {
        "CIM principal": "DP",
        "Diag Relie": "DR",
        "Diag Rsm": "RSM",
        "Duree sejour": "DUREE_SEJOUR"
    }
    for old, new in rename_map.items():
        if old in df.columns:
            df = df.rename({old: new})

    # Conversion dates
    df = df.with_columns([
        pl.col("Date entree dossier")
        .str.strip_chars()
        .str.slice(0, 10)
        .str.strptime(pl.Date, "%d/%m/%Y", strict=False)
        .alias("DATE_ENTREE"),
        pl.col("Date sortie dossier")
        .str.strip_chars()
        .str.slice(0, 10)
        .str.strptime(pl.Date, "%d/%m/%Y", strict=False)
        .alias("DATE_SORTIE"),
    ]).filter(pl.col("DATE_ENTREE").is_not_null())

    # Colonnes diagnostics
    diag_cols = [c for c in ["DP", "DR", "RSM"] if c in df.columns]
    diag_cols += [
        f"CIM SIGN {i}" for i in range(1, 100)
        if f"CIM SIGN {i}" in df.columns
    ]

    # Masque Insuffisance Cardiaque I50*
    def has_ic(df):
        mask = pl.lit(False)
        for col in diag_cols:
            mask = mask | pl.col(col).str.starts_with("I50")
        return mask

    df = df.with_columns(
        has_ic(df).alias("is_ic")
    )

    df_ic = df.filter(pl.col("is_ic"))

    # Sélection colonnes finales
    cols_finales = [
        c for c in [
            "NIP", "NDA", "URMP", "DP", "DR", "RSM",
            "GHM", "GHS", "DUREE_SEJOUR",
            "DATE_ENTREE", "DATE_SORTIE"
        ] if c in df_ic.columns
    ]
    df_final = df_ic.select(cols_finales)

    print(f"Sejours Insuffisance Cardiaque identifies : {df_final.height}")
    return df_final


# ──────────────────────────────────────────────
# ASSET 3 — Lecture des tarifs ATIH 2026
# ──────────────────────────────────────────────
@asset
def tarifs_atih():
    fichier = "/mnt/d/DOSSIER TELECHARGEMENT/tarif_arrete_2026.xlsx"
    df_atih = pd.read_excel(fichier, header=3)
    df_atih.columns = [
        "GHS", "GHM", "LIBELLE",
        "BORNE_BASSE", "BORNE_HAUTE",
        "TARIF_BASE", "FORFAIT_EXB",
        "TARIF_EXB", "TARIF_EXH"
    ]
    df_atih = df_atih.dropna(subset=["GHS", "GHM", "TARIF_BASE"])
    df_atih["GHS"] = df_atih["GHS"].astype(int).astype(str).str.zfill(4)
    df_atih["GHM"] = df_atih["GHM"].astype(str).str.strip()
    df_atih["TARIF_BASE"] = pd.to_numeric(df_atih["TARIF_BASE"], errors="coerce")
    df_polars = pl.from_pandas(df_atih[["GHS", "GHM", "LIBELLE", "TARIF_BASE"]])
    print(f"Tarifs ATIH charges : {df_polars.height} GHS")
    return df_polars
# ──────────────────────────────────────────────
# ASSET 4 — Jointure et calcul des coûts
# ──────────────────────────────────────────────
@asset
def calcul_cout_sejours(filter_insuffisance_cardiaque, tarifs_atih):
    """
    Joint les séjours IC avec les tarifs ATIH sur le GHS.
    Calcule le coût total par séjour.
    """
    df_ic = filter_insuffisance_cardiaque
    df_tarifs = tarifs_atih

    # Nettoyage GHS dans les deux tables
    df_ic = df_ic.with_columns(
        pl.col("GHS").str.strip_chars().alias("GHS")
    )

    # Jointure sur GHS
    df_joint = df_ic.join(
        df_tarifs,
        on="GHS",
        how="left"
    )

    # Calcul coût
    df_joint = df_joint.with_columns([
        pl.col("DUREE_SEJOUR").cast(pl.Int32, strict=False).alias("DUREE_SEJOUR_INT"),
        pl.col("TARIF_BASE").cast(pl.Float64, strict=False).alias("TARIF_BASE")
    ])

    df_joint = df_joint.with_columns(
        (pl.col("TARIF_BASE")).alias("COUT_SEJOUR")
    )

    # Stats
    total_sejours = df_joint.height
    cout_total = df_joint["COUT_SEJOUR"].sum()
    cout_moyen = df_joint["COUT_SEJOUR"].mean()

    print(f"Sejours IC avec tarif : {total_sejours}")
    print(f"Cout total : {cout_total:,.2f} euros")
    print(f"Cout moyen par sejour : {cout_moyen:,.2f} euros")

    return df_joint


# ──────────────────────────────────────────────
# ASSET 5 — Chargement dans PostgreSQL
# ──────────────────────────────────────────────
@asset
def charger_cout_postgres(calcul_cout_sejours):
    """
    Charge la table des coûts IC dans PostgreSQL.
    """
    df = calcul_cout_sejours

    if df.height == 0:
        print("Aucun sejour IC trouve.")
        return False

    conn = psycopg2.connect(
        "postgresql://postgres:airflow2026@localhost:5432/hopital"
    )
    cursor = conn.cursor()

    cursor.execute("CREATE SCHEMA IF NOT EXISTS pmsi_mco_analytics;")
    cursor.execute(
        "DROP TABLE IF EXISTS pmsi_mco_analytics.ic_couts_sejours;"
    )
    cursor.execute("""
        CREATE TABLE pmsi_mco_analytics.ic_couts_sejours (
            nip          TEXT,
            nda          TEXT,
            urmp         TEXT,
            dp           TEXT,
            ghm          TEXT,
            ghs          TEXT,
            libelle  TEXT,
            duree_sejour TEXT,
            date_entree  DATE,
            date_sortie  DATE,
            tarif_base   NUMERIC(10,2),
            cout_sejour  NUMERIC(10,2),
            date_chargement TIMESTAMP DEFAULT NOW()
        );
    """)

    # Sélection colonnes à insérer
    cols = [
        c for c in [
            "NIP", "NDA", "URMP", "DP",
            "GHM", "GHS", "LIBELLE",
            "DUREE_SEJOUR", "DATE_ENTREE", "DATE_SORTIE",
            "TARIF_BASE", "COUT_SEJOUR"
        ] if c in df.columns
    ]

    df_insert = df.select(cols).with_columns([
        pl.col("DATE_ENTREE").cast(pl.String),
        pl.col("DATE_SORTIE").cast(pl.String),
    ])

    donnees = [tuple(row) for row in df_insert.iter_rows()]

    cursor.executemany(f"""
        INSERT INTO pmsi_mco_analytics.ic_couts_sejours
        ({', '.join([c.lower() for c in cols])})
        VALUES ({', '.join(['%s'] * len(cols))})
    """, donnees)

    conn.commit()
    cursor.close()
    conn.close()

    print(f"{df.height} sejours IC charges avec leurs couts !")
    return True


# ──────────────────────────────────────────────
# CATALOGUE DAGSTER
# ──────────────────────────────────────────────
defs = Definitions(
    assets=[
        raw_mco_ic,
        filter_insuffisance_cardiaque,
        tarifs_atih,
        calcul_cout_sejours,
        charger_cout_postgres
    ]
)