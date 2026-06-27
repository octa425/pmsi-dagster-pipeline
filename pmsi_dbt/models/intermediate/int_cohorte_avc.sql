-- ══════════════════════════════════════════════════════
-- INTERMEDIATE : Cohorte AVC
-- Source  : int_filtres_pmsi + stg_mco_d
-- Rôle    : Sélectionner les patients AVC
--           I60-I64 en DP + G46 avec AVC en DA
--           Ajouter classes d'âge et libellés
-- ══════════════════════════════════════════════════════

WITH avc_dp AS (

    -- AVC en Diagnostic Principal (I60 à I64)
    SELECT
        eta_num,
        rsa_num,
        nir_patient,
        diagnostic_principal,
        code_cim10_3,
        age_annees,
        sexe,
        departement,
        code_geo,
        date_entree,
        date_sortie,
        duree_sejour_jours,
        mode_entree,
        mode_sortie,
        destination_sortie,

        -- Libellé type AVC
        CASE code_cim10_3
            WHEN 'I60' THEN 'Hemorragie meningee'
            WHEN 'I61' THEN 'Hemorragie intracerebrales'
            WHEN 'I62' THEN 'Autres hemorragies intracraniennes'
            WHEN 'I63' THEN 'Infarctus cerebral'
            WHEN 'I64' THEN 'AVC non precise'
            ELSE 'Autre'
        END AS type_avc,

        -- Classe age
        CASE
            WHEN age_annees BETWEEN 18 AND 64 THEN '1 - 18-64 ans'
            WHEN age_annees BETWEEN 65 AND 84 THEN '2 - 65-84 ans'
            WHEN age_annees >= 85             THEN '3 - 85 ans et plus'
        END AS classe_age,

        1 AS top_hosp_avc

    FROM {{ ref('int_filtres_pmsi') }}

    WHERE code_cim10_3 IN ('I60','I61','I62','I63','I64')

),

-- G46 en DP avec AVC en DA
g46_avec_avc_da AS (

    SELECT DISTINCT
        f.eta_num,
        f.rsa_num

    FROM {{ ref('int_filtres_pmsi') }} f
    INNER JOIN {{ ref('stg_mco_d') }} d
        ON f.eta_num = d.eta_num
        AND f.rsa_num = d.rsa_num

    WHERE
        -- G46 en DP
        f.code_cim10_3 = 'G46'
        -- AVC en DA
        AND d.code_cim10_3 IN ('I60','I61','I62','I63','I64')

),

g46_dp AS (

    SELECT
        f.eta_num,
        f.rsa_num,
        f.nir_patient,
        f.diagnostic_principal,
        f.code_cim10_3,
        f.age_annees,
        f.sexe,
        f.departement,
        f.code_geo,
        f.date_entree,
        f.date_sortie,
        f.duree_sejour_jours,
        f.mode_entree,
        f.mode_sortie,
        f.destination_sortie,
        'Syndrome vasculaire cerebral' AS type_avc,
        CASE
            WHEN f.age_annees BETWEEN 18 AND 64 THEN '1 - 18-64 ans'
            WHEN f.age_annees BETWEEN 65 AND 84 THEN '2 - 65-84 ans'
            WHEN f.age_annees >= 85             THEN '3 - 85 ans et plus'
        END AS classe_age,
        1 AS top_hosp_avc

    FROM {{ ref('int_filtres_pmsi') }} f
    INNER JOIN g46_avec_avc_da g
        ON f.eta_num = g.eta_num
        AND f.rsa_num = g.rsa_num

    WHERE f.code_cim10_3 = 'G46'

)

-- Union finale AVC DP + G46
SELECT * FROM avc_dp
UNION ALL
SELECT * FROM g46_dp
