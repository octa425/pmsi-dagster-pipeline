-- ══════════════════════════════════════════════════════
-- INTERMEDIATE : Filtres PMSI Guyane
-- Source  : stg_mco_b + stg_mco_c
-- Rôle    : Reproduction de FILTRESS973 (code SAS ORS)
--           Applique tous les filtres qualité PMSI
-- ══════════════════════════════════════════════════════

WITH base AS (

    -- Jointure T_MCO_B + T_MCO_C
    SELECT
        b.eta_num,
        b.rsa_num,
        b.diagnostic_principal,
        b.code_cim10_3,
        b.age_annees,
        b.sexe,
        b.departement,
        b.code_geo,
        b.mode_entree,
        b.mode_sortie,
        b.destination_sortie,
        b.type_sejour,
        c.nir_patient,
        c.date_entree,
        c.date_sortie,
        c.duree_sejour_jours

    FROM {{ ref('stg_mco_b') }} b
    LEFT JOIN {{ ref('stg_mco_c') }} c
        ON b.eta_num = c.eta_num
        AND b.rsa_num = c.rsa_num

),

filtres AS (

    SELECT *
    FROM base

    WHERE
        -- Filtre 1 — Guyane uniquement
        departement = '9C'

        -- Filtre 2 — Exclusion APHP APHM HCL
        AND eta_num NOT IN (
            '130780521','130783236','130783293',
            '130784234','130804297','130784259',
            '600100101','750041543','750100018',
            '750100042','750100075','750100083',
            '750100091','750100109','750100125',
            '750100166','750100208','750100216',
            '750100232','750100273','750100299',
            '750801441','750803447','750803454',
            '910100015','910100023','920100013',
            '920100021','920100039','920100047',
            '920100054','920100062','930100011',
            '930100037','930100045','940100027',
            '940100035','940100043','940100050',
            '940100068','950100016','690783154',
            '690784137','690784152','690784178',
            '690787478','830100558'
        )

        -- Filtre 3 — Exclusion inter-etablissements
        AND (type_sejour != 'B' OR type_sejour IS NULL)

        -- Filtre 4 — Age >= 18
        AND age_annees >= 18

        -- Filtre 5 — NIR patient renseigné
        AND nir_patient IS NOT NULL

)

SELECT * FROM filtres
