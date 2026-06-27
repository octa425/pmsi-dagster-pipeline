-- ══════════════════════════════════════════════════════
-- STAGING : T_MCO_D — Diagnostics Associés
-- Source  : Table brute PMSI MCO
-- Rôle    : Nettoyer les comorbidités
--           N lignes par séjour (1 par comorbidité)
-- ══════════════════════════════════════════════════════

SELECT
    -- Identifiants séjour
    eta_num                    AS eta_num,
    rsa_num                    AS rsa_num,

    -- Diagnostic associé
    ass_dgn                    AS code_comorbidite,
    SUBSTR(ass_dgn, 1, 3)      AS code_cim10_3,

    -- Famille de comorbidité
    CASE
        WHEN ass_dgn LIKE 'I10%' THEN 'HTA'
        WHEN ass_dgn LIKE 'E11%' THEN 'Diabete type 2'
        WHEN ass_dgn LIKE 'I48%' THEN 'Fibrillation auriculaire'
        WHEN ass_dgn LIKE 'I25%' THEN 'Cardiopathie ischemique'
        WHEN ass_dgn LIKE 'E78%' THEN 'Dyslipidemie'
        WHEN ass_dgn LIKE 'J44%' THEN 'BPCO'
        WHEN ass_dgn LIKE 'N18%' THEN 'Insuffisance renale'
        WHEN ass_dgn LIKE 'I50%' THEN 'Insuffisance cardiaque'
        WHEN ass_dgn LIKE 'E14%' THEN 'Diabete non precise'
        WHEN ass_dgn LIKE 'I20%' THEN 'Angor'
        ELSE 'Autre'
    END                        AS libelle_comorbidite

FROM {{ source('pmsi_raw', 't_mco_d') }}

WHERE
    -- Exclure codes vides
    ass_dgn IS NOT NULL
    AND ass_dgn != 'xxxx'
    AND ass_dgn != 'XXXX'
