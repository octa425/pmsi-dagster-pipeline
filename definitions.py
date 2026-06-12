import psycopg2
import polars as pl
import csv
from datetime import datetime
from dagster import asset, Definitions, Config


class ConfigPipeline(Config):
    chemin_csv: str = "/mnt/d/BUREAU/EX780762_RAP_CCH_2021_22_8_2022.csv"


@asset
def raw_patients(config: ConfigPipeline):
    fichier = config.chemin_csv
    print(f"Lecture de : {fichier}")

    with open(fichier, "r", encoding="windows-1252") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

    print(f"Colonnes detectees : {len(header)}")

    colonnes_voulues = [
        "NIP", "NDA", "Date entree dossier",
        "CIM principal", "Diag Relie", "Diag Rsm"
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

    print(f"Lecture finie : {len(donnees)} lignes")
    return pl.DataFrame(donnees, schema=noms_colonnes_reels, orient="row")


@asset
def clean_patients(raw_patients):
    df = raw_patients

    rename_map = {
        "CIM principal": "DP",
        "Diag Relie": "DR",
        "Diag Rsm": "RSM"
    }
    for old, new in rename_map.items():
        if old in df.columns:
            df = df.rename({old: new})

    df = df.with_columns(
        pl.col("Date entree dossier")
        .str.strip_chars()
        .str.slice(0, 10)
        .str.strptime(pl.Date, "%d/%m/%Y", strict=False)
        .alias("DATE_ENTREE")
    ).filter(pl.col("DATE_ENTREE").is_not_null())

    date_min = df["DATE_ENTREE"].min()
    if date_min and date_min.year >= 2022:
        df = df.filter(pl.col("DATE_ENTREE") >= datetime(2022, 6, 1).date())
    else:
        df = df.filter(pl.col("DATE_ENTREE") <= datetime(2021, 12, 31).date())

    diag_cols = [c for c in ["DP", "DR", "RSM"] if c in df.columns]
    diag_cols += [
        f"CIM SIGN {i}" for i in range(1, 100)
        if f"CIM SIGN {i}" in df.columns
    ]

    def has_code(patterns):
        mask = pl.lit(False)
        for col in diag_cols:
            for pat in patterns:
                mask = mask | pl.col(col).str.contains(f"^{pat}$")
        return mask

    df = df.with_columns([
        has_code(["J440"]).alias("has_J440"),
        has_code(["J441"]).alias("has_J441"),
        has_code(["J40", "J41", "J42", "J43", "J448", "J449"]).alias("has_bpco_general"),
        has_code(["J1", "J2"]).alias("has_infection"),
        has_code(["J960"]).alias("has_insuff_resp"),
    ]).with_columns([
        (pl.col("has_J440") | pl.col("has_J441")).alias("direct_exacerbation"),
        (pl.col("has_bpco_general") & pl.col("has_infection")).alias("indirect_infection"),
        (pl.col("has_bpco_general") & pl.col("has_insuff_resp")).alias("indirect_ir"),
    ]).with_columns(
        (
            pl.col("direct_exacerbation") |
            pl.col("indirect_infection") |
            pl.col("indirect_ir")
        ).alias("to_include")
    )

    cols_finales = [
        c for c in ["NIP", "NDA", "DATE_ENTREE", "DP", "DR", "RSM"]
        if c in df.columns
    ]
    df_final = df.filter(pl.col("to_include")).select(cols_finales)

    print(f"Sejours BPCO identifies : {df_final.height}")
    return df_final


@asset
def charger_postgres_patients(clean_patients):
    df = clean_patients

    if df.height == 0:
        print("Aucun sejour BPCO trouve.")
        return False

    conn = psycopg2.connect(
        "postgresql://postgres:airflow2026@localhost:5432/hopital"
    )
    cursor = conn.cursor()

    cursor.execute("CREATE SCHEMA IF NOT EXISTS pmsi_mco_analytics;")
    cursor.execute(
        "DROP TABLE IF EXISTS pmsi_mco_analytics.patients_bpco_dagster;"
    )
    cursor.execute("""
        CREATE TABLE pmsi_mco_analytics.patients_bpco_dagster (
            nip             TEXT,
            nda             TEXT,
            date_entree     DATE,
            dp              TEXT,
            dr              TEXT,
            rsm             TEXT,
            date_chargement TIMESTAMP DEFAULT NOW()
        );
    """)

    df = df.with_columns(pl.col("DATE_ENTREE").cast(pl.String))
    donnees = [tuple(row) for row in df.iter_rows()]

    cursor.executemany("""
        INSERT INTO pmsi_mco_analytics.patients_bpco_dagster
        (nip, nda, date_entree, dp, dr, rsm)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, donnees)

    conn.commit()
    cursor.close()
    conn.close()

    print(f"{df.height} sejours BPCO charges dans PostgreSQL !")
    return True


defs = Definitions(
    assets=[raw_patients, clean_patients, charger_postgres_patients]
)