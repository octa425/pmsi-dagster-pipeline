-- ══════════════════════════════════════════════════════
-- MART : Survie AVC
-- Source  : int_cohorte_avc + ir_ben_r
-- Rôle    : Table finale analytique
--           Calcul mortalité J30 et J365
--           Prête pour Kaplan-Meier et régression
-- ══════════════════════════════════════════════════════

WITH cohorte AS (

    SELECT *
    FROM {{ ref('int_cohorte_avc') }}

),

beneficiaires AS (

    SELECT
        nir_ano_17          AS nir_patient,
        ben_dcd_dte         AS date_deces,
        ben_sex_cod         AS sexe_ben,
        ben_res_dpt         AS departement_residence

    FROM {{ source('pmsi_raw', 'ir_ben_r') }}

),

jointure AS (

    SELECT
        c.*,
        b.date_deces,
        b.departement_residence,

        -- Délai en jours entre AVC et décès
        CASE
            WHEN b.date_deces IS NULL THEN NULL
            ELSE b.date_deces - c.date_entree
        END AS delai_deces_jours,

        -- EVENT pour Kaplan-Meier
        -- 1 = décédé, 0 = censuré (vivant)
        CASE
            WHEN b.date_deces IS NULL THEN 0
            ELSE 1
        END AS event_deces,

        -- Mortalité à J30
        CASE
            WHEN b.date_deces IS NULL THEN 0
            WHEN b.date_deces - c.date_entree <= 30 THEN 1
            ELSE 0
        END AS deces_j30,

        -- Mortalité à J365
        CASE
            WHEN b.date_deces IS NULL THEN 0
            WHEN b.date_deces - c.date_entree <= 365 THEN 1
            ELSE 0
        END AS deces_j365,

        -- Survie à J30 (critère de jugement)
        CASE
            WHEN b.date_deces IS NULL THEN 1
            WHEN b.date_deces - c.date_entree <= 30 THEN 0
            ELSE 1
        END AS survie_j30,

        -- Survie à J365 (critère de jugement)
        CASE
            WHEN b.date_deces IS NULL THEN 1
            WHEN b.date_deces - c.date_entree <= 365 THEN 0
            ELSE 1
        END AS survie_j365

    FROM cohorte c
    LEFT JOIN beneficiaires b
        ON c.nir_patient = b.nir_patient

)

SELECT * FROM jointure
