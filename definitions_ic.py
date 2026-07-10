import os
import psycopg2
import polars as pl
import pandas as pd
import csv
from datetime import datetime
from dagster import asset, Definitions


# ──────────────────────────────────────────────
# ASSET 1 — Lecture brute du CSV MCO (INCHANGÉ)
# ──────────────────────────────────────────────
@asset
def raw_mco_ic():
    """
    Lit le fichier CSV MCO et extrait toutes les colonnes
    utiles dont GHM et GHS pour la jointure ATIH.
    """
    fichier = "/mnt/d/BUREAU/DATA_SET_SIMULE.csv"

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
#   CORRECTION : DR et les CIM SIGN (DAS) sont
#   désormais conservés dans cols_finales, au lieu
#   d'être jetés après avoir servi uniquement au
#   calcul du masque is_ic.
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
    das_cols = [
        f"CIM SIGN {i}" for i in range(1, 100)
        if f"CIM SIGN {i}" in df.columns
    ]
    diag_cols += das_cols

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
    # CORRECTION : on rajoute das_cols ici, elles ne sont plus perdues
    cols_finales = [
        c for c in (
            ["NIP", "NDA", "URMP", "DP", "DR", "RSM",
             "GHM", "GHS", "DUREE_SEJOUR",
             "DATE_ENTREE", "DATE_SORTIE"] + das_cols
        ) if c in df_ic.columns
    ]
    df_final = df_ic.select(cols_finales)

    print(f"Sejours Insuffisance Cardiaque identifies : {df_final.height}")
    return df_final


# ──────────────────────────────────────────────
# ASSET 3 — Lecture des tarifs ATIH 2026 (INCHANGÉ)
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
# ASSET 4 — Jointure et calcul des coûts (INCHANGÉ)
# ──────────────────────────────────────────────
@asset
def calcul_cout_sejours(filter_insuffisance_cardiaque, tarifs_atih):
    """
    Joint les séjours IC avec les tarifs ATIH sur le GHS.
    Calcule le coût total par séjour.
    """
    df_ic = filter_insuffisance_cardiaque
    df_tarifs = tarifs_atih

    df_ic = df_ic.with_columns(
        pl.col("GHS").str.strip_chars().alias("GHS")
    )

    df_joint = df_ic.join(
        df_tarifs,
        on="GHS",
        how="left"
    )

    df_joint = df_joint.with_columns([
        pl.col("DUREE_SEJOUR").cast(pl.Int32, strict=False).alias("DUREE_SEJOUR_INT"),
        pl.col("TARIF_BASE").cast(pl.Float64, strict=False).alias("TARIF_BASE")
    ])

    df_joint = df_joint.with_columns(
        (pl.col("TARIF_BASE")).alias("COUT_SEJOUR")
    )

    total_sejours = df_joint.height
    cout_total = df_joint["COUT_SEJOUR"].sum()
    cout_moyen = df_joint["COUT_SEJOUR"].mean()

    print(f"Sejours IC avec tarif : {total_sejours}")
    print(f"Cout total : {cout_total:,.2f} euros")
    print(f"Cout moyen par sejour : {cout_moyen:,.2f} euros")

    return df_joint


# ──────────────────────────────────────────────
# ASSET 5 — Chargement dans PostgreSQL
#   CORRECTION : "dr" ajouté au CREATE TABLE et
#   à la liste d'insertion (il était présent dans
#   le DataFrame mais explicitement exclu ici).
#   Les colonnes CIM SIGN ne sont plus sélectionnées
#   dans CETTE table : elles partent maintenant vers
#   une table séparée via das_long_format /
#   charger_das_postgres (voir plus bas).
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
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
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
            dr           TEXT,
            ghm          TEXT,
            ghs          TEXT,
            libelle      TEXT,
            duree_sejour TEXT,
            date_entree  DATE,
            date_sortie  DATE,
            tarif_base   NUMERIC(10,2),
            cout_sejour  NUMERIC(10,2),
            date_chargement TIMESTAMP DEFAULT NOW()
        );
    """)

    # CORRECTION : "DR" ajouté à cette liste
    cols = [
        c for c in [
            "NIP", "NDA", "URMP", "DP", "DR",
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
# ASSET 6 (NOUVEAU) — Transformation DAS large → long
#
#   Les 99 colonnes CIM SIGN sont en format "large"
#   (1 colonne par position, 90% de valeurs vides).
#   On les transforme en format "long" (aussi appelé
#   normalisé) : 1 ligne par diagnostic associé
#   réellement renseigné, avec son rang d'origine.
#   Opération = un "unpivot" (l'inverse d'un pivot
#   Excel), équivalent au .melt() de pandas.
# ──────────────────────────────────────────────
@asset
def das_long_format(filter_insuffisance_cardiaque):
    """
    Transforme les colonnes CIM SIGN 1 à 99 en format long :
    (NDA, rang, code_cim10), une ligne par DAS non vide.
    """
    df = filter_insuffisance_cardiaque
    das_cols = [c for c in df.columns if c.startswith("CIM SIGN")]

    if not das_cols:
        print("Aucune colonne CIM SIGN trouvee dans le DataFrame.")
        return pl.DataFrame({"NDA": [], "rang": [], "code_cim10": []})

    df_long = df.select(["NDA"] + das_cols).unpivot(
        index="NDA",
        on=das_cols,
        variable_name="colonne_das",
        value_name="code_cim10"
    )

    # Extraction du rang depuis "CIM SIGN 12" -> 12
    df_long = df_long.with_columns(
        pl.col("colonne_das")
        .str.extract(r"CIM SIGN (\d+)", 1)
        .cast(pl.Int32)
        .alias("rang")
    )

    # On ne garde que les DAS effectivement renseignes
    df_long = df_long.filter(
        pl.col("code_cim10").is_not_null()
        & (pl.col("code_cim10").str.strip_chars() != "")
    ).select(["NDA", "rang", "code_cim10"])

    print(f"{df_long.height} DAS non vides extraits (format long)")
    return df_long


# ──────────────────────────────────────────────
# ASSET 7 (NOUVEAU) — Chargement des DAS dans
#   une table normalisee separee
# ──────────────────────────────────────────────
@asset
def charger_das_postgres(das_long_format):
    """
    Charge les DAS (format long) dans une table normalisee
    diagnostics_associes : 1 ligne par (sejour, diagnostic associe).
    """
    df = das_long_format

    if df.height == 0:
        print("Aucun DAS a charger.")
        return False

    conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
) 
    cursor = conn.cursor()

    cursor.execute("CREATE SCHEMA IF NOT EXISTS pmsi_mco_analytics;")
    cursor.execute(
        "DROP TABLE IF EXISTS pmsi_mco_analytics.diagnostics_associes;"
    )
    cursor.execute("""
        CREATE TABLE pmsi_mco_analytics.diagnostics_associes (
            id          SERIAL PRIMARY KEY,
            nda         TEXT,
            rang        INTEGER,
            code_cim10  TEXT,
            CONSTRAINT uq_nda_rang UNIQUE (nda, rang)
        );
    """)
    # NOTE : pas de contrainte REFERENCES vers ic_couts_sejours(nda) ici,
    # car "nda" n'est pas defini comme cle primaire/unique dans cette
    # table aujourd'hui (contrairement a l'exemple du doc CODE_A_Z).
    # A ajouter plus tard si on decide de rendre nda unique la-bas.

    donnees = [
        tuple(row)
        for row in df.select(["NDA", "rang", "code_cim10"]).iter_rows()
    ]

    cursor.executemany("""
        INSERT INTO pmsi_mco_analytics.diagnostics_associes (nda, rang, code_cim10)
        VALUES (%s, %s, %s)
        ON CONFLICT (nda, rang) DO NOTHING
    """, donnees)

    conn.commit()
    cursor.close()
    conn.close()

    print(f"{df.height} DAS charges dans diagnostics_associes !")
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
        charger_cout_postgres,
        das_long_format,
        charger_das_postgres,
    ]
)
