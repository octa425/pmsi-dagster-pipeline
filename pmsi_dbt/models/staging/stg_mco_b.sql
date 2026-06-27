-- ══════════════════════════════════════════════════════
-- STAGING : T_MCO_B — Résumés de Sortie Anonymisés
-- Source  : Table brute PMSI MCO
-- Rôle    : Nettoyer et standardiser T_MCO_B
--           avant les transformations métier
-- ══════════════════════════════════════════════════════

SELECT
    -- Identifiants séjour
    eta_num                          AS eta_num,
    rsa_num                          AS rsa_num,

    -- Diagnostic principal
    dgn_pal                          AS diagnostic_principal,
    SUBSTR(dgn_pal, 1, 3)            AS code_cim10_3,

    -- Données patient
    age_ann                          AS age_annees,
    cod_sex                          AS sexe,

    -- Géographie
    bdi_dep                          AS departement,
    bdi_cod                          AS code_geo,

    -- Mode entrée/sortie
    ent_mod                          AS mode_entree,
    sor_mod                          AS mode_sortie,
    sor_des                          AS destination_sortie,

    -- Type séjour
    sej_typ                          AS type_sejour

FROM {{ source('pmsi_raw', 't_mco_b') }}

WHERE
    -- Adultes uniquement
    age_ann >= 18

    -- Exclure NIR invalides
    AND bdi_cod IS NOT NULL

    -- Exclure codes géo 999
    AND SUBSTR(bdi_cod, 3, 3) != '999'
