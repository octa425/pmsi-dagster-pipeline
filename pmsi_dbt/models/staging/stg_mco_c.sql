-- ══════════════════════════════════════════════════════
-- STAGING : T_MCO_C — Table de chaînage NIR
-- Source  : Table brute PMSI MCO
-- Rôle    : Nettoyer et standardiser T_MCO_C
--           Contrôles qualité NIR (7 variables RET)
-- ══════════════════════════════════════════════════════

SELECT
    -- Identifiants séjour
    eta_num                    AS eta_num,
    rsa_num                    AS rsa_num,

    -- Identifiant patient
    nir_ano_17                 AS nir_patient,

    -- Dates de séjour
    exe_soi_dtd                AS date_entree,
    exe_soi_dtf                AS date_sortie,

    -- Durée séjour en jours
    exe_soi_dtf - exe_soi_dtd  AS duree_sejour_jours,

    -- Numéro séjour
    sej_num                    AS numero_sejour,

    -- Contrôles qualité NIR
    nir_ret                    AS ctrl_nir,
    nai_ret                    AS ctrl_naissance,
    sex_ret                    AS ctrl_sexe,
    dat_ret                    AS ctrl_date,
    sej_ret                    AS ctrl_sejour,
    fho_ret                    AS ctrl_fho,
    pms_ret                    AS ctrl_pms

FROM {{ source('pmsi_raw', 't_mco_c') }}

WHERE
    -- Exclure NIR anonymes
    nir_ano_17 NOT IN (
        'xxxxxxxxxxxxxxxxx',
        'XXXXXXXXXXXXXXXXS'
    )
    -- 7 contrôles qualité NIR obligatoires
    AND nir_ret = '0'
    AND nai_ret = '0'
    AND sex_ret = '0'
    AND dat_ret = '0'
    AND sej_ret = '0'
    AND fho_ret = '0'
    AND pms_ret = '0'
