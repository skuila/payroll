-- ============================================================================
-- SCHÉMAS
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS paie;
CREATE SCHEMA IF NOT EXISTS payroll;
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS reference;
CREATE SCHEMA IF NOT EXISTS security;
CREATE SCHEMA IF NOT EXISTS superset;

-- ============================================================================
-- TABLES
-- ============================================================================
-- Note: Les définitions complètes sont dans les migrations SQL

-- ============================================================================
-- VUES (avec règles de calcul)
-- ============================================================================

-- Vue: core.v_employees_enriched
CREATE OR REPLACE VIEW core.v_employees_enriched AS
 SELECT e.employee_id,
    e.employee_key,
    e.matricule_norm,
    e.matricule_raw,
    e.nom_norm,
    e.prenom_norm,
    e.nom_complet,
    e.statut,
    e.source_system,
    e.created_at,
    e.updated_at,
    e.created_by,
    e.updated_by,
    count(DISTINCT t.pay_date) AS nb_periodes_paie,
    min(t.pay_date) AS premiere_paie,
    max(t.pay_date) AS derniere_paie,
    (sum(t.amount_cents) / 100.0) AS total_paie_lifetime
   FROM (core.employees e
     LEFT JOIN payroll.payroll_transactions t ON ((e.employee_id = t.employee_id)))
  GROUP BY e.employee_id;;


-- Vue: paie.v_anomalies_paie
CREATE OR REPLACE VIEW paie.v_anomalies_paie AS
 WITH stats_periode AS (
         SELECT t.periode_paie,
            avg(f.montant_cents) AS montant_moyen,
            stddev(f.montant_cents) AS montant_stddev
           FROM (paie.fact_paie f
             JOIN paie.dim_temps t ON ((f.temps_id = t.temps_id)))
          GROUP BY t.periode_paie
        )
 SELECT 'MONTANT_ABERRANT'::text AS type_anomalie,
    e.matricule,
    e.nom_prenom,
    t.periode_paie,
    c.code_paie,
    ((f.montant_cents)::numeric / 100.0) AS montant,
    'Montant > 3 écarts-types'::text AS description
   FROM ((((paie.fact_paie f
     JOIN paie.dim_employe e ON ((f.employe_id = e.employe_id)))
     JOIN paie.dim_temps t ON ((f.temps_id = t.temps_id)))
     JOIN paie.dim_code_paie c ON ((f.code_paie_id = c.code_paie_id)))
     JOIN stats_periode sp ON (((t.periode_paie)::text = (sp.periode_paie)::text)))
  WHERE (abs(((f.montant_cents)::numeric - sp.montant_moyen)) > ((3)::numeric * sp.montant_stddev))
UNION ALL
 SELECT 'SIGNE_INCOHERENT'::text AS type_anomalie,
    e.matricule,
    e.nom_prenom,
    t.periode_paie,
    c.code_paie,
    ((f.montant_cents)::numeric / 100.0) AS montant,
    'Gains négatif ou Déduction positive'::text AS description
   FROM (((paie.fact_paie f
     JOIN paie.dim_employe e ON ((f.employe_id = e.employe_id)))
     JOIN paie.dim_temps t ON ((f.temps_id = t.temps_id)))
     JOIN paie.dim_code_paie c ON ((f.code_paie_id = c.code_paie_id)))
  WHERE (((c.categorie_paie = 'Gains'::paie.categorie_paie_enum) AND (f.montant_cents < 0)) OR ((c.categorie_paie = ANY (ARRAY['Deductions'::paie.categorie_paie_enum, 'Deductions_legales'::paie.categorie_paie_enum, 'Assurances'::paie.categorie_paie_enum, 'Syndicats'::paie.categorie_paie_enum])) AND (f.montant_cents > 0)))
  ORDER BY 4 DESC, 1;;


-- Vue: paie.v_dedup_report
CREATE OR REPLACE VIEW paie.v_dedup_report AS
 SELECT source_batch_id,
    date_paie,
    count(*) AS nb_doublons,
    (sum(abs(montant_cents)) / 100.0) AS montant_total_ignore,
    string_agg(DISTINCT (code_paie)::text, ', '::text) AS codes_paie_concernes,
    string_agg(DISTINCT (matricule)::text, ', '::text) AS matricules_concernes
   FROM paie.dedup_log d
  GROUP BY source_batch_id, date_paie
  ORDER BY source_batch_id DESC;;


-- Vue: paie.v_employe_profil
CREATE OR REPLACE VIEW paie.v_employe_profil AS
 WITH base AS (
         SELECT t.employee_id,
            COALESCE(NULLIF(TRIM(BOTH FROM s.categorie_emploi), ''::text), 'Non dÃ©fini'::text) AS categorie_emploi,
            COALESCE(NULLIF(TRIM(BOTH FROM s.titre_emploi), ''::text), 'Non dÃ©fini'::text) AS titre_emploi,
            count(*) AS nb
           FROM (payroll.payroll_transactions t
             LEFT JOIN paie.stg_paie_transactions s ON ((((t.source_file)::text = (s.source_file)::text) AND (t.source_row_no = s.source_row_number))))
          GROUP BY t.employee_id, COALESCE(NULLIF(TRIM(BOTH FROM s.categorie_emploi), ''::text), 'Non dÃ©fini'::text), COALESCE(NULLIF(TRIM(BOTH FROM s.titre_emploi), ''::text), 'Non dÃ©fini'::text)
        ), ranked AS (
         SELECT b.employee_id,
            b.categorie_emploi,
            b.titre_emploi,
            b.nb,
            row_number() OVER (PARTITION BY b.employee_id ORDER BY b.nb DESC, b.categorie_emploi, b.titre_emploi) AS rn
           FROM base b
        )
 SELECT e.employee_id,
    e.matricule,
    COALESCE(TRIM(BOTH FROM e.nom), ''::text) AS nom,
    COALESCE(TRIM(BOTH FROM e.prenom), ''::text) AS prenom,
    r.categorie_emploi,
    r.titre_emploi,
    r.nb AS occurrences
   FROM (ranked r
     JOIN core.employees e ON ((e.employee_id = r.employee_id)))
  WHERE (r.rn = 1);;


-- Vue: paie.v_employes_groupes
CREATE OR REPLACE VIEW paie.v_employes_groupes AS
 SELECT categorie_emploi,
    titre_emploi,
    count(DISTINCT employee_id) AS nb_employes
   FROM paie.v_employe_profil p
  GROUP BY categorie_emploi, titre_emploi
  ORDER BY (count(DISTINCT employee_id)) DESC, categorie_emploi, titre_emploi;;


-- Vue: paie.v_kpi_mois
CREATE OR REPLACE VIEW paie.v_kpi_mois AS
 SELECT to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM'::text) AS periode_paie,
    to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM-DD'::text) AS date_paie,
    (COALESCE(sum(
        CASE
            WHEN (t.amount_cents > 0) THEN t.amount_cents
            ELSE (0)::bigint
        END), (0)::numeric) / 100.0) AS gains_brut,
    (COALESCE(sum(
        CASE
            WHEN (t.amount_cents < 0) THEN t.amount_cents
            ELSE (0)::bigint
        END), (0)::numeric) / 100.0) AS deductions_net,
    (COALESCE(sum(t.amount_cents), (0)::numeric) / 100.0) AS net_a_payer,
    COALESCE(sum(COALESCE(m.part_employeur, (0)::numeric)), (0)::numeric) AS part_employeur,
    ((COALESCE(sum(t.amount_cents), (0)::numeric) + COALESCE(sum(COALESCE((m.part_employeur * (100)::numeric), (0)::numeric)), (0)::numeric)) / 100.0) AS cout_total,
    (COALESCE(sum(
        CASE
            WHEN (t.amount_cents < 0) THEN abs(t.amount_cents)
            ELSE (0)::bigint
        END), (0)::numeric) / 100.0) AS cash_out_total,
        CASE
            WHEN (sum(
            CASE
                WHEN (t.amount_cents > 0) THEN t.amount_cents
                ELSE (0)::bigint
            END) > (0)::numeric) THEN ((COALESCE(sum(COALESCE((m.part_employeur * (100)::numeric), (0)::numeric)), (0)::numeric) / sum(
            CASE
                WHEN (t.amount_cents > 0) THEN t.amount_cents
                ELSE (0)::bigint
            END)) * 100.0)
            ELSE NULL::numeric
        END AS taux_part_employeur_pct,
    count(DISTINCT
        CASE
            WHEN (t.amount_cents <> 0) THEN t.employee_id
            ELSE NULL::integer
        END) AS nb_employes,
    count(*) AS nb_transactions
   FROM (payroll.payroll_transactions t
     LEFT JOIN payroll.imported_payroll_master m ON ((t.source_row_no = m.source_row_number)))
  GROUP BY (to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM'::text)), (to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM-DD'::text))
  ORDER BY (to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM'::text)), (to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM-DD'::text));;


-- Vue: paie.v_kpi_par_categorie_emploi
CREATE OR REPLACE VIEW paie.v_kpi_par_categorie_emploi AS
 SELECT em.categorie_emploi,
    t.periode_paie,
    count(DISTINCT f.employe_id) AS nb_employes,
    (sum(
        CASE
            WHEN (c.categorie_paie = 'Gains'::paie.categorie_paie_enum) THEN f.montant_cents
            ELSE (0)::bigint
        END) / 100.0) AS gains_brut,
    (sum(
        CASE
            WHEN (c.categorie_paie = ANY (ARRAY['Deductions'::paie.categorie_paie_enum, 'Deductions_legales'::paie.categorie_paie_enum, 'Assurances'::paie.categorie_paie_enum, 'Syndicats'::paie.categorie_paie_enum])) THEN abs(f.montant_cents)
            ELSE (0)::bigint
        END) / 100.0) AS deductions_totales,
    (sum(f.montant_cents) / 100.0) AS net_a_payer,
    (sum(f.part_employeur_cents) / 100.0) AS part_employeur,
    ((sum(f.montant_cents) / (NULLIF(count(DISTINCT f.employe_id), 0))::numeric) / 100.0) AS net_moyen_par_employe
   FROM (((paie.fact_paie f
     JOIN paie.dim_temps t ON ((f.temps_id = t.temps_id)))
     JOIN paie.dim_code_paie c ON ((f.code_paie_id = c.code_paie_id)))
     LEFT JOIN paie.dim_emploi em ON ((f.emploi_id = em.emploi_id)))
  WHERE (em.categorie_emploi IS NOT NULL)
  GROUP BY em.categorie_emploi, t.periode_paie
  ORDER BY t.periode_paie DESC, em.categorie_emploi;;


-- Vue: paie.v_kpi_par_code_paie
CREATE OR REPLACE VIEW paie.v_kpi_par_code_paie AS
 SELECT c.code_paie,
    c.libelle_paie,
    c.categorie_paie,
    t.periode_paie,
    count(DISTINCT f.employe_id) AS nb_employes_concernes,
    count(*) AS nb_transactions,
    (sum(f.montant_cents) / 100.0) AS montant_total,
    (avg(f.montant_cents) / 100.0) AS montant_moyen,
    ((min(f.montant_cents))::numeric / 100.0) AS montant_min,
    ((max(f.montant_cents))::numeric / 100.0) AS montant_max,
    (sum(f.part_employeur_cents) / 100.0) AS part_employeur_total
   FROM ((paie.fact_paie f
     JOIN paie.dim_temps t ON ((f.temps_id = t.temps_id)))
     JOIN paie.dim_code_paie c ON ((f.code_paie_id = c.code_paie_id)))
  GROUP BY c.code_paie, c.libelle_paie, c.categorie_paie, t.periode_paie
  ORDER BY t.periode_paie DESC, c.categorie_paie, c.code_paie;;


-- Vue: paie.v_kpi_par_employe
CREATE OR REPLACE VIEW paie.v_kpi_par_employe AS
 SELECT e.employe_id,
    e.matricule,
    e.nom_prenom,
    e.statut,
    count(DISTINCT t.periode_paie) AS nb_periodes,
    min(t.date_paie) AS premiere_paie,
    max(t.date_paie) AS derniere_paie,
    (sum(
        CASE
            WHEN (c.categorie_paie = 'Gains'::paie.categorie_paie_enum) THEN f.montant_cents
            ELSE (0)::bigint
        END) / 100.0) AS gains_cumules,
    (sum(
        CASE
            WHEN (c.categorie_paie = ANY (ARRAY['Deductions'::paie.categorie_paie_enum, 'Deductions_legales'::paie.categorie_paie_enum, 'Assurances'::paie.categorie_paie_enum, 'Syndicats'::paie.categorie_paie_enum])) THEN abs(f.montant_cents)
            ELSE (0)::bigint
        END) / 100.0) AS deductions_cumulees,
    (sum(f.montant_cents) / 100.0) AS net_cumule,
    (sum(f.part_employeur_cents) / 100.0) AS part_employeur_cumulee,
    (avg(f.montant_cents) / 100.0) AS net_moyen_par_periode,
    count(*) AS nb_transactions_totales
   FROM (((paie.dim_employe e
     LEFT JOIN paie.fact_paie f ON ((e.employe_id = f.employe_id)))
     LEFT JOIN paie.dim_temps t ON ((f.temps_id = t.temps_id)))
     LEFT JOIN paie.dim_code_paie c ON ((f.code_paie_id = c.code_paie_id)))
  GROUP BY e.employe_id, e.matricule, e.nom_prenom, e.statut
  ORDER BY e.nom_prenom;;


-- Vue: paie.v_kpi_par_employe_mois
CREATE OR REPLACE VIEW paie.v_kpi_par_employe_mois AS
 SELECT to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM'::text) AS periode_paie,
    to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM-DD'::text) AS date_paie,
    t.employee_id AS matricule,
    COALESCE(m.nom_employe, 'N/A'::text) AS nom_prenom,
    COALESCE(m.categorie_emploi, 'Non défini'::text) AS categorie_emploi,
    COALESCE(m.titre_emploi, 'Non défini'::text) AS titre_emploi,
    COALESCE(m.poste_budgetaire, 'Non défini'::text) AS poste_budgetaire,
    (COALESCE(sum(
        CASE
            WHEN (t.amount_cents > 0) THEN t.amount_cents
            ELSE (0)::bigint
        END), (0)::numeric) / 100.0) AS gains_brut,
    (COALESCE(sum(
        CASE
            WHEN (t.amount_cents < 0) THEN t.amount_cents
            ELSE (0)::bigint
        END), (0)::numeric) / 100.0) AS deductions,
    (COALESCE(sum(t.amount_cents), (0)::numeric) / 100.0) AS net,
    COALESCE(sum(COALESCE(m.part_employeur, (0)::numeric)), (0)::numeric) AS part_employeur,
    ((COALESCE(sum(t.amount_cents), (0)::numeric) + COALESCE(sum(COALESCE((m.part_employeur * (100)::numeric), (0)::numeric)), (0)::numeric)) / 100.0) AS cout_total,
        CASE
            WHEN (sum(
            CASE
                WHEN (t.amount_cents > 0) THEN t.amount_cents
                ELSE (0)::bigint
            END) > (0)::numeric) THEN ((COALESCE(sum(COALESCE((m.part_employeur * (100)::numeric), (0)::numeric)), (0)::numeric) / sum(
            CASE
                WHEN (t.amount_cents > 0) THEN t.amount_cents
                ELSE (0)::bigint
            END)) * 100.0)
            ELSE NULL::numeric
        END AS taux_part_employeur_pct
   FROM (payroll.payroll_transactions t
     LEFT JOIN payroll.imported_payroll_master m ON ((t.source_row_no = m.source_row_number)))
  GROUP BY (to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM'::text)), (to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM-DD'::text)), t.employee_id, m.nom_employe, m.categorie_emploi, m.titre_emploi, m.poste_budgetaire
  ORDER BY (to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM'::text)), (to_char((t.pay_date)::timestamp with time zone, 'YYYY-MM-DD'::text)), t.employee_id;;


-- Vue: paie.v_kpi_par_poste_budgetaire
CREATE OR REPLACE VIEW paie.v_kpi_par_poste_budgetaire AS
 SELECT p.poste_budgetaire,
    p.libelle_poste,
    p.segment_1,
    p.segment_2,
    p.segment_3,
    p.segment_4,
    t.periode_paie,
    count(DISTINCT f.employe_id) AS nb_employes,
    (sum(
        CASE
            WHEN (c.categorie_paie = 'Gains'::paie.categorie_paie_enum) THEN f.montant_cents
            ELSE (0)::bigint
        END) / 100.0) AS gains_brut,
    (sum(
        CASE
            WHEN (c.categorie_paie = ANY (ARRAY['Deductions'::paie.categorie_paie_enum, 'Deductions_legales'::paie.categorie_paie_enum, 'Assurances'::paie.categorie_paie_enum, 'Syndicats'::paie.categorie_paie_enum])) THEN abs(f.montant_cents)
            ELSE (0)::bigint
        END) / 100.0) AS deductions_totales,
    (sum(f.montant_cents) / 100.0) AS net_a_payer,
    (sum(f.part_employeur_cents) / 100.0) AS part_employeur,
    ((sum(f.montant_cents) + sum(f.part_employeur_cents)) / 100.0) AS cout_total
   FROM (((paie.fact_paie f
     JOIN paie.dim_temps t ON ((f.temps_id = t.temps_id)))
     JOIN paie.dim_code_paie c ON ((f.code_paie_id = c.code_paie_id)))
     JOIN paie.dim_poste_budgetaire p ON ((f.poste_budgetaire_id = p.poste_budgetaire_id)))
  GROUP BY p.poste_budgetaire, p.libelle_poste, p.segment_1, p.segment_2, p.segment_3, p.segment_4, t.periode_paie
  ORDER BY t.periode_paie DESC, p.segment_1, p.poste_budgetaire;;


-- Vue: payroll.v_import_required_check
CREATE OR REPLACE VIEW payroll.v_import_required_check AS
 SELECT raw_row_id,
    file_id,
    (("N de ligne" IS NOT NULL) AND ("N de ligne" <> ''::text)) AS ok_n_de_ligne,
    ("date de paie" IS NOT NULL) AS ok_date_de_paie,
    ((matricule IS NOT NULL) AND (matricule <> ''::text)) AS ok_matricule,
    (("employ+®" IS NOT NULL) AND ("employ+®" <> ''::text)) AS ok_employe,
    (("catégorie de paie" IS NOT NULL) AND ("catégorie de paie" <> ''::text)) AS ok_categorie_de_paie,
    (("code de paie" IS NOT NULL) AND ("code de paie" <> ''::text)) AS ok_code_de_paie,
    (("description du code de paie" IS NOT NULL) AND ("description du code de paie" <> ''::text)) AS ok_desc_code_de_paie,
    (("poste budgétaire" IS NOT NULL) AND ("poste budgétaire" <> ''::text)) AS ok_poste_budgetaire,
    (("description du poste budgétaire" IS NOT NULL) AND ("description du poste budgétaire" <> ''::text)) AS ok_desc_poste_budgetaire,
    (montant IS NOT NULL) AS ok_montant,
    ("part employeur" IS NOT NULL) AS has_part_employeur,
    ("montant combiné" IS NOT NULL) AS has_mnt_cmb,
    (("titre d'emploi" IS NOT NULL) AND ("titre d'emploi" <> ''::text)) AS has_titre_emploi,
    (("code emploi" IS NOT NULL) AND ("code emploi" <> ''::text)) AS has_code_emploi,
    (("catégorie d'emploi" IS NOT NULL) AND ("catégorie d'emploi" <> ''::text)) AS has_categorie_emploi
   FROM payroll_raw.raw_lines rl;;


-- Vue: payroll.v_imported_payroll_compat
CREATE OR REPLACE VIEW payroll.v_imported_payroll_compat AS
 SELECT e.matricule_raw AS "matricule ",
    e.nom_complet AS "employÃ© ",
    t.pay_date AS "date de paie ",
    t.pay_code AS "categorie de paie ",
    ((t.amount_cents)::numeric / 100.0) AS "montant ",
    t.employee_id,
    t.transaction_id
   FROM (payroll.payroll_transactions t
     JOIN core.employees e ON ((t.employee_id = e.employee_id)));;


-- Vue: payroll.v_nouveaux_par_batch
CREATE OR REPLACE VIEW payroll.v_nouveaux_par_batch AS
 WITH batches_avec_date AS (
         SELECT DISTINCT ib.batch_id,
            ib.filename,
            t.pay_date,
            ib.started_at
           FROM (payroll.import_batches ib
             JOIN payroll.payroll_transactions t ON ((t.import_batch_id = ib.batch_id)))
          WHERE ((ib.status)::text = 'completed'::text)
        ), matricules_par_batch AS (
         SELECT DISTINCT t.import_batch_id AS batch_id,
            b.pay_date,
            b.filename,
            e.employee_id,
            e.matricule_norm,
            e.nom_norm,
            e.prenom_norm,
                CASE
                    WHEN ((e.matricule_norm)::text ~ '^[0-9]+$'::text) THEN (e.matricule_norm)::integer
                    ELSE NULL::integer
                END AS matricule_int
           FROM ((payroll.payroll_transactions t
             JOIN core.employees e ON ((t.employee_id = e.employee_id)))
             JOIN batches_avec_date b ON ((b.batch_id = t.import_batch_id)))
          WHERE ((e.matricule_norm IS NOT NULL) AND ((e.matricule_norm)::text ~ '^[0-9]+$'::text) AND (t.amount_cents <> 0))
        ), max_par_batch AS (
         SELECT matricules_par_batch.batch_id,
            matricules_par_batch.pay_date,
            matricules_par_batch.filename,
            max(matricules_par_batch.matricule_int) AS max_matricule,
            count(DISTINCT matricules_par_batch.employee_id) AS nb_employes
           FROM matricules_par_batch
          GROUP BY matricules_par_batch.batch_id, matricules_par_batch.pay_date, matricules_par_batch.filename
        ), batches_avec_precedent AS (
         SELECT max_par_batch.batch_id,
            max_par_batch.pay_date,
            max_par_batch.filename,
            max_par_batch.max_matricule AS max_actuel,
            max_par_batch.nb_employes,
            lag(max_par_batch.max_matricule) OVER (ORDER BY max_par_batch.pay_date) AS max_precedent,
            lag(max_par_batch.pay_date) OVER (ORDER BY max_par_batch.pay_date) AS date_precedente
           FROM max_par_batch
        )
 SELECT mp.batch_id,
    mp.pay_date,
    mp.filename,
    mp.employee_id,
    mp.matricule_norm,
    mp.matricule_int,
    mp.nom_norm,
    mp.prenom_norm,
    bp.max_precedent,
    bp.max_actuel,
    bp.date_precedente,
        CASE
            WHEN (mp.matricule_int > COALESCE(bp.max_precedent, 0)) THEN true
            ELSE false
        END AS est_nouveau
   FROM (matricules_par_batch mp
     JOIN batches_avec_precedent bp ON ((mp.batch_id = bp.batch_id)))
  ORDER BY mp.pay_date DESC, mp.matricule_int;;


-- Vue: payroll.v_payroll_detail
CREATE OR REPLACE VIEW payroll.v_payroll_detail AS
 SELECT id,
    date_paie,
    (date_trunc('month'::text, (date_paie)::timestamp with time zone))::date AS mois_paie,
    (date_trunc('year'::text, (date_paie)::timestamp with time zone))::date AS annee_paie,
    to_char((date_paie)::timestamp with time zone, 'YYYY-MM'::text) AS periode_yyyymm,
    EXTRACT(year FROM date_paie) AS annee,
    EXTRACT(month FROM date_paie) AS mois,
    matricule,
    nom_employe,
    poste_budgetaire,
    categorie_paie,
    code_paie,
    description_code_paie,
    COALESCE(montant_employe, (0)::numeric) AS montant_employe,
    COALESCE(part_employeur, (0)::numeric) AS part_employeur,
    COALESCE(montant_combine, (0)::numeric) AS montant_combine,
    COALESCE(montant_employe, (0)::numeric) AS net
   FROM payroll.imported_payroll_master
  WHERE ((date_paie IS NOT NULL) AND (matricule IS NOT NULL) AND (TRIM(BOTH FROM COALESCE(matricule, ''::text)) <> ''::text));;


-- Vue: payroll.v_payroll_kpi
CREATE OR REPLACE VIEW payroll.v_payroll_kpi AS
 SELECT sum(COALESCE(montant_employe, (0)::numeric)) AS total_employe,
    sum(COALESCE(part_employeur, (0)::numeric)) AS total_employeur,
    sum(COALESCE(montant_combine, (0)::numeric)) AS total_combine,
    sum(COALESCE(montant_employe, (0)::numeric)) AS total_net,
    count(DISTINCT matricule) AS nb_employes_distincts,
    count(DISTINCT date_paie) AS nb_periodes_distinctes,
    count(DISTINCT COALESCE(NULLIF(TRIM(BOTH FROM poste_budgetaire), ''::text), 'Non classé'::text)) AS nb_postes_budgetaires_distincts,
    count(DISTINCT COALESCE(NULLIF(TRIM(BOTH FROM code_paie), ''::text), 'CODE_INCONNU'::text)) AS nb_codes_paie_distincts,
    count(*) AS nb_transactions_total,
    min(date_paie) AS date_min,
    max(date_paie) AS date_max
   FROM payroll.imported_payroll_master
  WHERE ((date_paie IS NOT NULL) AND (matricule IS NOT NULL) AND (TRIM(BOTH FROM COALESCE(matricule, ''::text)) <> ''::text));;


-- Vue: payroll.v_payroll_par_budget
CREATE OR REPLACE VIEW payroll.v_payroll_par_budget AS
 SELECT date_paie,
    (date_trunc('month'::text, (date_paie)::timestamp with time zone))::date AS mois_paie,
    to_char((date_paie)::timestamp with time zone, 'YYYY-MM'::text) AS periode_yyyymm,
    EXTRACT(year FROM date_paie) AS annee,
    EXTRACT(month FROM date_paie) AS mois,
    COALESCE(NULLIF(TRIM(BOTH FROM poste_budgetaire), ''::text), 'Non classé'::text) AS poste_budgetaire,
    sum(COALESCE(montant_employe, (0)::numeric)) AS total_employe,
    sum(COALESCE(part_employeur, (0)::numeric)) AS total_employeur,
    sum(COALESCE(montant_combine, (0)::numeric)) AS total_combine,
    sum(COALESCE(montant_employe, (0)::numeric)) AS total_net,
    count(DISTINCT matricule) AS nb_employes_distincts,
    count(*) AS nb_transactions
   FROM payroll.imported_payroll_master
  WHERE ((date_paie IS NOT NULL) AND (matricule IS NOT NULL) AND (TRIM(BOTH FROM COALESCE(matricule, ''::text)) <> ''::text))
  GROUP BY date_paie, (date_trunc('month'::text, (date_paie)::timestamp with time zone)), (to_char((date_paie)::timestamp with time zone, 'YYYY-MM'::text)), (EXTRACT(year FROM date_paie)), (EXTRACT(month FROM date_paie)), COALESCE(NULLIF(TRIM(BOTH FROM poste_budgetaire), ''::text), 'Non classé'::text)
  ORDER BY date_paie, COALESCE(NULLIF(TRIM(BOTH FROM poste_budgetaire), ''::text), 'Non classé'::text);;


-- Vue: payroll.v_payroll_par_code
CREATE OR REPLACE VIEW payroll.v_payroll_par_code AS
 SELECT date_paie,
    (date_trunc('month'::text, (date_paie)::timestamp with time zone))::date AS mois_paie,
    to_char((date_paie)::timestamp with time zone, 'YYYY-MM'::text) AS periode_yyyymm,
    EXTRACT(year FROM date_paie) AS annee,
    EXTRACT(month FROM date_paie) AS mois,
    COALESCE(NULLIF(TRIM(BOTH FROM code_paie), ''::text), 'CODE_INCONNU'::text) AS code_paie,
    COALESCE(NULLIF(TRIM(BOTH FROM description_code_paie), ''::text), 'Non décrit'::text) AS description_code_paie,
    COALESCE(NULLIF(TRIM(BOTH FROM categorie_paie), ''::text), 'Non classé'::text) AS categorie_paie,
    sum(COALESCE(montant_employe, (0)::numeric)) AS total_employe,
    sum(COALESCE(part_employeur, (0)::numeric)) AS total_employeur,
    sum(COALESCE(montant_combine, (0)::numeric)) AS total_combine,
    sum(COALESCE(montant_employe, (0)::numeric)) AS total_net,
    count(DISTINCT matricule) AS nb_employes_distincts,
    count(*) AS nb_transactions
   FROM payroll.imported_payroll_master
  WHERE ((date_paie IS NOT NULL) AND (matricule IS NOT NULL) AND (TRIM(BOTH FROM COALESCE(matricule, ''::text)) <> ''::text))
  GROUP BY date_paie, (date_trunc('month'::text, (date_paie)::timestamp with time zone)), (to_char((date_paie)::timestamp with time zone, 'YYYY-MM'::text)), (EXTRACT(year FROM date_paie)), (EXTRACT(month FROM date_paie)), COALESCE(NULLIF(TRIM(BOTH FROM code_paie), ''::text), 'CODE_INCONNU'::text), COALESCE(NULLIF(TRIM(BOTH FROM description_code_paie), ''::text), 'Non décrit'::text), COALESCE(NULLIF(TRIM(BOTH FROM categorie_paie), ''::text), 'Non classé'::text)
  ORDER BY date_paie, (sum(COALESCE(montant_combine, (0)::numeric))) DESC;;


-- Vue: payroll.v_payroll_par_periode
CREATE OR REPLACE VIEW payroll.v_payroll_par_periode AS
 SELECT date_paie,
    (date_trunc('month'::text, (date_paie)::timestamp with time zone))::date AS mois_paie,
    (date_trunc('year'::text, (date_paie)::timestamp with time zone))::date AS annee_paie,
    to_char((date_paie)::timestamp with time zone, 'YYYY-MM'::text) AS periode_yyyymm,
    EXTRACT(year FROM date_paie) AS annee,
    EXTRACT(month FROM date_paie) AS mois,
    EXTRACT(quarter FROM date_paie) AS trimestre,
    sum(COALESCE(montant_employe, (0)::numeric)) AS total_employe,
    sum(COALESCE(part_employeur, (0)::numeric)) AS total_employeur,
    sum(COALESCE(montant_combine, (0)::numeric)) AS total_combine,
    sum(COALESCE(montant_employe, (0)::numeric)) AS total_net,
    count(DISTINCT matricule) AS nb_employes_distincts,
    count(*) AS nb_transactions
   FROM payroll.imported_payroll_master
  WHERE ((date_paie IS NOT NULL) AND (matricule IS NOT NULL) AND (TRIM(BOTH FROM COALESCE(matricule, ''::text)) <> ''::text))
  GROUP BY date_paie, (date_trunc('month'::text, (date_paie)::timestamp with time zone)), (date_trunc('year'::text, (date_paie)::timestamp with time zone)), (to_char((date_paie)::timestamp with time zone, 'YYYY-MM'::text)), (EXTRACT(year FROM date_paie)), (EXTRACT(month FROM date_paie)), (EXTRACT(quarter FROM date_paie))
  ORDER BY date_paie;;

-- ============================================================================
-- FONCTIONS
-- ============================================================================

-- Fonction: core.compute_employee_key
CREATE OR REPLACE FUNCTION core.compute_employee_key(p_matricule text, p_nom text)
 RETURNS character varying
 LANGUAGE plpgsql
 IMMUTABLE STRICT
AS $function$
DECLARE
    v_matricule_clean TEXT;
    v_nom_norm TEXT;
BEGIN
    -- Nettoyer matricule (trim + retrait parasites)
    v_matricule_clean := NULLIF(
        BTRIM(regexp_replace(COALESCE(p_matricule, ''), '[^0-9A-Za-z\-]', '', 'g')),
        ''
    );
    
    -- Si matricule numÃ©rique â†’ retirer zÃ©ros en tÃªte
    IF v_matricule_clean IS NOT NULL AND v_matricule_clean ~ '^[0-9]+$' THEN
        v_matricule_clean := NULLIF(
            regexp_replace(v_matricule_clean, '^0+', ''),
            ''
        );
    END IF;
    
    -- Si matricule valide â†’ retourner
    IF v_matricule_clean IS NOT NULL THEN
        RETURN v_matricule_clean;
    END IF;
    
    -- Sinon fallback sur nom normalisÃ© (hashÃ©)
    v_nom_norm := regexp_replace(
        unaccent(LOWER(COALESCE(p_nom, ''))),
        '\s+', ' ', 'g'
    );
    
    RETURN MD5(v_nom_norm);
END;
$function$
;


-- Fonction: core.immutable_unaccent
CREATE OR REPLACE FUNCTION core.immutable_unaccent(text)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE PARALLEL SAFE
AS $function$
        BEGIN
            RETURN unaccent($1);
        END;
        $function$
;


-- Fonction: core.set_updated_at
CREATE OR REPLACE FUNCTION core.set_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$
;


-- Fonction: core.update_timestamp
CREATE OR REPLACE FUNCTION core.update_timestamp()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $function$
;


-- Fonction: core.update_updated_at_column
CREATE OR REPLACE FUNCTION core.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    NEW.updated_by = CURRENT_USER;
    RETURN NEW;
END;
$function$
;


-- Fonction: paie.generer_cle_metier
CREATE OR REPLACE FUNCTION paie.generer_cle_metier(p_date_paie date, p_matricule character varying, p_code_paie character varying, p_poste_budgetaire character varying, p_montant_cents bigint, p_part_employeur_cents bigint)
 RETURNS character varying
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    RETURN MD5(
        COALESCE(p_date_paie::TEXT, '') || '|' ||
        COALESCE(p_matricule, '') || '|' ||
        COALESCE(p_code_paie, '') || '|' ||
        COALESCE(p_poste_budgetaire, '') || '|' ||
        COALESCE(p_montant_cents::TEXT, '0') || '|' ||
        COALESCE(p_part_employeur_cents::TEXT, '0')
    );
END;
$function$
;


-- Fonction: paie.refresh_vues_materialisees
CREATE OR REPLACE FUNCTION paie.refresh_vues_materialisees()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
    RAISE NOTICE 'Début refresh vues matérialisées...';
    
    REFRESH MATERIALIZED VIEW CONCURRENTLY paie.v_kpi_temps_mensuel;
    RAISE NOTICE '  ✓ v_kpi_temps_mensuel refreshed';
    
    REFRESH MATERIALIZED VIEW CONCURRENTLY paie.v_kpi_temps_annuel;
    RAISE NOTICE '  ✓ v_kpi_temps_annuel refreshed';
    
    RAISE NOTICE 'Refresh terminé.';
END;
$function$
;


-- Fonction: paie.upsert_dim_temps
CREATE OR REPLACE FUNCTION paie.upsert_dim_temps(p_date_paie date)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_temps_id INTEGER;
BEGIN
    INSERT INTO paie.dim_temps (
        date_paie,
        jour_paie,
        mois_paie,
        annee_paie,
        trimestre,
        semestre,
        periode_paie,
        exercice_fiscal,
        is_fin_mois,
        is_fin_trimestre,
        is_fin_annee
    )
    VALUES (
        p_date_paie,
        EXTRACT(DAY FROM p_date_paie),
        EXTRACT(MONTH FROM p_date_paie),
        EXTRACT(YEAR FROM p_date_paie),
        EXTRACT(QUARTER FROM p_date_paie),
        CASE WHEN EXTRACT(MONTH FROM p_date_paie) <= 6 THEN 1 ELSE 2 END,
        TO_CHAR(p_date_paie, 'YYYY-MM'),
        EXTRACT(YEAR FROM p_date_paie),
        p_date_paie = (DATE_TRUNC('MONTH', p_date_paie) + INTERVAL '1 month - 1 day')::DATE,
        EXTRACT(MONTH FROM p_date_paie) IN (3, 6, 9, 12),
        EXTRACT(MONTH FROM p_date_paie) = 12
    )
    ON CONFLICT (date_paie) DO UPDATE SET
        date_paie = EXCLUDED.date_paie
    RETURNING temps_id INTO v_temps_id;
    
    RETURN v_temps_id;
END;
$function$
;


-- Fonction: payroll.auto_calc_period_seq
CREATE OR REPLACE FUNCTION payroll.auto_calc_period_seq()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            -- Si period_seq_in_year est NULL, le calculer automatiquement
            IF NEW.period_seq_in_year IS NULL THEN
                -- Calculer 1 + nombre de pay_date strictement antérieures dans la même année
                SELECT 1 + COUNT(*)
                INTO NEW.period_seq_in_year
                FROM payroll.pay_periods
                WHERE pay_year = NEW.pay_year
                AND pay_date < NEW.pay_date;
            END IF;
            
            RETURN NEW;
        END;
        $function$
;


-- Fonction: payroll.check_pay_date_consistency
CREATE OR REPLACE FUNCTION payroll.check_pay_date_consistency()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            -- Extraire composantes de pay_date
            IF EXTRACT(DAY FROM NEW.pay_date) != NEW.pay_day THEN
                RAISE EXCEPTION 'pay_day (%) ne correspond pas à pay_date (%) [jour=%]',
                    NEW.pay_day, NEW.pay_date, EXTRACT(DAY FROM NEW.pay_date);
            END IF;
            
            IF EXTRACT(MONTH FROM NEW.pay_date) != NEW.pay_month THEN
                RAISE EXCEPTION 'pay_month (%) ne correspond pas à pay_date (%) [mois=%]',
                    NEW.pay_month, NEW.pay_date, EXTRACT(MONTH FROM NEW.pay_date);
            END IF;
            
            IF EXTRACT(YEAR FROM NEW.pay_date) != NEW.pay_year THEN
                RAISE EXCEPTION 'pay_year (%) ne correspond pas à pay_date (%) [année=%]',
                    NEW.pay_year, NEW.pay_date, EXTRACT(YEAR FROM NEW.pay_date);
            END IF;
            
            RETURN NEW;
        END;
        $function$
;


-- Fonction: payroll.check_transaction_pay_date
CREATE OR REPLACE FUNCTION payroll.check_transaction_pay_date()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        DECLARE
            period_pay_date DATE;
        BEGIN
            -- Récupérer pay_date de la période
            SELECT pay_date INTO period_pay_date
            FROM payroll.pay_periods
            WHERE period_id = NEW.period_id;
            
            IF NOT FOUND THEN
                RAISE EXCEPTION 'period_id % inexistant dans pay_periods', NEW.period_id;
            END IF;
            
            -- Vérifier cohérence
            IF NEW.pay_date != period_pay_date THEN
                RAISE EXCEPTION 'pay_date transaction (%) diffère de pay_date période (%) pour period_id=%',
                    NEW.pay_date, period_pay_date, NEW.period_id;
            END IF;
            
            RETURN NEW;
        END;
        $function$
;


-- Fonction: payroll.ensure_period
CREATE OR REPLACE FUNCTION payroll.ensure_period(p_date date)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_id  uuid;
  v_y   int := EXTRACT(YEAR FROM p_date);
  v_seq int;
BEGIN
  -- RÃ©duire les messages de log dans la fonction
  SET LOCAL client_min_messages = warning;
  
  SELECT period_id INTO v_id
  FROM payroll.pay_periods
  WHERE pay_date = p_date
  LIMIT 1;
  IF v_id IS NOT NULL THEN RETURN v_id; END IF;

  -- verrou conseil sur l'annÃ©e (Ã©vite la course)
  PERFORM pg_advisory_xact_lock(hashtext('pay_periods_' || v_y::text));

  -- re-vÃ©rification aprÃ¨s verrou
  SELECT period_id INTO v_id
  FROM payroll.pay_periods
  WHERE pay_date = p_date
  LIMIT 1;
  IF v_id IS NOT NULL THEN RETURN v_id; END IF;

  SELECT COALESCE(MAX(period_seq_in_year),0)+1 INTO v_seq
  FROM payroll.pay_periods WHERE pay_year = v_y;

  INSERT INTO payroll.pay_periods(pay_date, pay_day, pay_month, pay_year, period_seq_in_year, status)
  VALUES (p_date, EXTRACT(DAY FROM p_date)::int, EXTRACT(MONTH FROM p_date)::int, v_y, v_seq, 'ouverte')
  RETURNING period_id INTO v_id;

  RETURN v_id;
END;
$function$
;


-- Fonction: payroll.get_stats_nouveaux_date
CREATE OR REPLACE FUNCTION payroll.get_stats_nouveaux_date(p_pay_date date)
 RETURNS TABLE(batch_id integer, pay_date date, filename character varying, total_employes bigint, nouveaux_employes bigint, anciens_employes bigint, max_precedent integer, max_actuel integer, date_precedente date, liste_nouveaux character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    RETURN QUERY
    SELECT 
        v.batch_id,
        v.pay_date,
        v.filename::VARCHAR(500),
        COUNT(DISTINCT v.employee_id)::BIGINT as total_employes,
        COUNT(DISTINCT v.employee_id) FILTER (WHERE v.est_nouveau = TRUE)::BIGINT as nouveaux,
        COUNT(DISTINCT v.employee_id) FILTER (WHERE v.est_nouveau = FALSE)::BIGINT as anciens,
        MAX(v.max_precedent) as max_prec,
        MAX(v.max_actuel) as max_act,
        MAX(v.date_precedente) as date_prec,
        STRING_AGG(
            DISTINCT v.matricule_norm, ', ' 
            ORDER BY v.matricule_norm
        ) FILTER (WHERE v.est_nouveau = TRUE)::VARCHAR(255) as liste_nouveaux
    FROM payroll.v_nouveaux_par_batch v
    WHERE v.pay_date = p_pay_date
    GROUP BY v.batch_id, v.pay_date, v.filename;
END;
$function$
;


-- Fonction: public.armor
CREATE OR REPLACE FUNCTION public.armor(bytea, text[], text[])
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_armor$function$
;


-- Fonction: public.armor
CREATE OR REPLACE FUNCTION public.armor(bytea)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_armor$function$
;


-- Fonction: public.cash_dist
CREATE OR REPLACE FUNCTION public.cash_dist(money, money)
 RETURNS money
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$cash_dist$function$
;


-- Fonction: public.crypt
CREATE OR REPLACE FUNCTION public.crypt(text, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_crypt$function$
;


-- Fonction: public.date_dist
CREATE OR REPLACE FUNCTION public.date_dist(date, date)
 RETURNS integer
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$date_dist$function$
;


-- Fonction: public.dearmor
CREATE OR REPLACE FUNCTION public.dearmor(text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_dearmor$function$
;


-- Fonction: public.decrypt
CREATE OR REPLACE FUNCTION public.decrypt(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_decrypt$function$
;


-- Fonction: public.decrypt_iv
CREATE OR REPLACE FUNCTION public.decrypt_iv(bytea, bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_decrypt_iv$function$
;


-- Fonction: public.digest
CREATE OR REPLACE FUNCTION public.digest(text, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_digest$function$
;


-- Fonction: public.digest
CREATE OR REPLACE FUNCTION public.digest(bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_digest$function$
;


-- Fonction: public.encrypt
CREATE OR REPLACE FUNCTION public.encrypt(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_encrypt$function$
;


-- Fonction: public.encrypt_iv
CREATE OR REPLACE FUNCTION public.encrypt_iv(bytea, bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_encrypt_iv$function$
;


-- Fonction: public.float4_dist
CREATE OR REPLACE FUNCTION public.float4_dist(real, real)
 RETURNS real
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$float4_dist$function$
;


-- Fonction: public.float8_dist
CREATE OR REPLACE FUNCTION public.float8_dist(double precision, double precision)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$float8_dist$function$
;


-- Fonction: public.gbt_bit_compress
CREATE OR REPLACE FUNCTION public.gbt_bit_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bit_compress$function$
;


-- Fonction: public.gbt_bit_consistent
CREATE OR REPLACE FUNCTION public.gbt_bit_consistent(internal, bit, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bit_consistent$function$
;


-- Fonction: public.gbt_bit_penalty
CREATE OR REPLACE FUNCTION public.gbt_bit_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bit_penalty$function$
;


-- Fonction: public.gbt_bit_picksplit
CREATE OR REPLACE FUNCTION public.gbt_bit_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bit_picksplit$function$
;


-- Fonction: public.gbt_bit_same
CREATE OR REPLACE FUNCTION public.gbt_bit_same(gbtreekey_var, gbtreekey_var, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bit_same$function$
;


-- Fonction: public.gbt_bit_union
CREATE OR REPLACE FUNCTION public.gbt_bit_union(internal, internal)
 RETURNS gbtreekey_var
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bit_union$function$
;


-- Fonction: public.gbt_bool_compress
CREATE OR REPLACE FUNCTION public.gbt_bool_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE STRICT
AS '$libdir/btree_gist', $function$gbt_bool_compress$function$
;


-- Fonction: public.gbt_bool_consistent
CREATE OR REPLACE FUNCTION public.gbt_bool_consistent(internal, boolean, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE STRICT
AS '$libdir/btree_gist', $function$gbt_bool_consistent$function$
;


-- Fonction: public.gbt_bool_fetch
CREATE OR REPLACE FUNCTION public.gbt_bool_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE STRICT
AS '$libdir/btree_gist', $function$gbt_bool_fetch$function$
;


-- Fonction: public.gbt_bool_penalty
CREATE OR REPLACE FUNCTION public.gbt_bool_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE STRICT
AS '$libdir/btree_gist', $function$gbt_bool_penalty$function$
;


-- Fonction: public.gbt_bool_picksplit
CREATE OR REPLACE FUNCTION public.gbt_bool_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE STRICT
AS '$libdir/btree_gist', $function$gbt_bool_picksplit$function$
;


-- Fonction: public.gbt_bool_same
CREATE OR REPLACE FUNCTION public.gbt_bool_same(gbtreekey2, gbtreekey2, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE STRICT
AS '$libdir/btree_gist', $function$gbt_bool_same$function$
;


-- Fonction: public.gbt_bool_union
CREATE OR REPLACE FUNCTION public.gbt_bool_union(internal, internal)
 RETURNS gbtreekey2
 LANGUAGE c
 IMMUTABLE STRICT
AS '$libdir/btree_gist', $function$gbt_bool_union$function$
;


-- Fonction: public.gbt_bpchar_compress
CREATE OR REPLACE FUNCTION public.gbt_bpchar_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bpchar_compress$function$
;


-- Fonction: public.gbt_bpchar_consistent
CREATE OR REPLACE FUNCTION public.gbt_bpchar_consistent(internal, character, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bpchar_consistent$function$
;


-- Fonction: public.gbt_bytea_compress
CREATE OR REPLACE FUNCTION public.gbt_bytea_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bytea_compress$function$
;


-- Fonction: public.gbt_bytea_consistent
CREATE OR REPLACE FUNCTION public.gbt_bytea_consistent(internal, bytea, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bytea_consistent$function$
;


-- Fonction: public.gbt_bytea_penalty
CREATE OR REPLACE FUNCTION public.gbt_bytea_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bytea_penalty$function$
;


-- Fonction: public.gbt_bytea_picksplit
CREATE OR REPLACE FUNCTION public.gbt_bytea_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bytea_picksplit$function$
;


-- Fonction: public.gbt_bytea_same
CREATE OR REPLACE FUNCTION public.gbt_bytea_same(gbtreekey_var, gbtreekey_var, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bytea_same$function$
;


-- Fonction: public.gbt_bytea_union
CREATE OR REPLACE FUNCTION public.gbt_bytea_union(internal, internal)
 RETURNS gbtreekey_var
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_bytea_union$function$
;


-- Fonction: public.gbt_cash_compress
CREATE OR REPLACE FUNCTION public.gbt_cash_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_cash_compress$function$
;


-- Fonction: public.gbt_cash_consistent
CREATE OR REPLACE FUNCTION public.gbt_cash_consistent(internal, money, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_cash_consistent$function$
;


-- Fonction: public.gbt_cash_distance
CREATE OR REPLACE FUNCTION public.gbt_cash_distance(internal, money, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_cash_distance$function$
;


-- Fonction: public.gbt_cash_fetch
CREATE OR REPLACE FUNCTION public.gbt_cash_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_cash_fetch$function$
;


-- Fonction: public.gbt_cash_penalty
CREATE OR REPLACE FUNCTION public.gbt_cash_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_cash_penalty$function$
;


-- Fonction: public.gbt_cash_picksplit
CREATE OR REPLACE FUNCTION public.gbt_cash_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_cash_picksplit$function$
;


-- Fonction: public.gbt_cash_same
CREATE OR REPLACE FUNCTION public.gbt_cash_same(gbtreekey16, gbtreekey16, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_cash_same$function$
;


-- Fonction: public.gbt_cash_union
CREATE OR REPLACE FUNCTION public.gbt_cash_union(internal, internal)
 RETURNS gbtreekey16
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_cash_union$function$
;


-- Fonction: public.gbt_date_compress
CREATE OR REPLACE FUNCTION public.gbt_date_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_date_compress$function$
;


-- Fonction: public.gbt_date_consistent
CREATE OR REPLACE FUNCTION public.gbt_date_consistent(internal, date, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_date_consistent$function$
;


-- Fonction: public.gbt_date_distance
CREATE OR REPLACE FUNCTION public.gbt_date_distance(internal, date, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_date_distance$function$
;


-- Fonction: public.gbt_date_fetch
CREATE OR REPLACE FUNCTION public.gbt_date_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_date_fetch$function$
;


-- Fonction: public.gbt_date_penalty
CREATE OR REPLACE FUNCTION public.gbt_date_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_date_penalty$function$
;


-- Fonction: public.gbt_date_picksplit
CREATE OR REPLACE FUNCTION public.gbt_date_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_date_picksplit$function$
;


-- Fonction: public.gbt_date_same
CREATE OR REPLACE FUNCTION public.gbt_date_same(gbtreekey8, gbtreekey8, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_date_same$function$
;


-- Fonction: public.gbt_date_union
CREATE OR REPLACE FUNCTION public.gbt_date_union(internal, internal)
 RETURNS gbtreekey8
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_date_union$function$
;


-- Fonction: public.gbt_decompress
CREATE OR REPLACE FUNCTION public.gbt_decompress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_decompress$function$
;


-- Fonction: public.gbt_enum_compress
CREATE OR REPLACE FUNCTION public.gbt_enum_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_enum_compress$function$
;


-- Fonction: public.gbt_enum_consistent
CREATE OR REPLACE FUNCTION public.gbt_enum_consistent(internal, anyenum, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_enum_consistent$function$
;


-- Fonction: public.gbt_enum_fetch
CREATE OR REPLACE FUNCTION public.gbt_enum_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_enum_fetch$function$
;


-- Fonction: public.gbt_enum_penalty
CREATE OR REPLACE FUNCTION public.gbt_enum_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_enum_penalty$function$
;


-- Fonction: public.gbt_enum_picksplit
CREATE OR REPLACE FUNCTION public.gbt_enum_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_enum_picksplit$function$
;


-- Fonction: public.gbt_enum_same
CREATE OR REPLACE FUNCTION public.gbt_enum_same(gbtreekey8, gbtreekey8, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_enum_same$function$
;


-- Fonction: public.gbt_enum_union
CREATE OR REPLACE FUNCTION public.gbt_enum_union(internal, internal)
 RETURNS gbtreekey8
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_enum_union$function$
;


-- Fonction: public.gbt_float4_compress
CREATE OR REPLACE FUNCTION public.gbt_float4_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float4_compress$function$
;


-- Fonction: public.gbt_float4_consistent
CREATE OR REPLACE FUNCTION public.gbt_float4_consistent(internal, real, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float4_consistent$function$
;


-- Fonction: public.gbt_float4_distance
CREATE OR REPLACE FUNCTION public.gbt_float4_distance(internal, real, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float4_distance$function$
;


-- Fonction: public.gbt_float4_fetch
CREATE OR REPLACE FUNCTION public.gbt_float4_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float4_fetch$function$
;


-- Fonction: public.gbt_float4_penalty
CREATE OR REPLACE FUNCTION public.gbt_float4_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float4_penalty$function$
;


-- Fonction: public.gbt_float4_picksplit
CREATE OR REPLACE FUNCTION public.gbt_float4_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float4_picksplit$function$
;


-- Fonction: public.gbt_float4_same
CREATE OR REPLACE FUNCTION public.gbt_float4_same(gbtreekey8, gbtreekey8, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float4_same$function$
;


-- Fonction: public.gbt_float4_union
CREATE OR REPLACE FUNCTION public.gbt_float4_union(internal, internal)
 RETURNS gbtreekey8
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float4_union$function$
;


-- Fonction: public.gbt_float8_compress
CREATE OR REPLACE FUNCTION public.gbt_float8_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float8_compress$function$
;


-- Fonction: public.gbt_float8_consistent
CREATE OR REPLACE FUNCTION public.gbt_float8_consistent(internal, double precision, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float8_consistent$function$
;


-- Fonction: public.gbt_float8_distance
CREATE OR REPLACE FUNCTION public.gbt_float8_distance(internal, double precision, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float8_distance$function$
;


-- Fonction: public.gbt_float8_fetch
CREATE OR REPLACE FUNCTION public.gbt_float8_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float8_fetch$function$
;


-- Fonction: public.gbt_float8_penalty
CREATE OR REPLACE FUNCTION public.gbt_float8_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float8_penalty$function$
;


-- Fonction: public.gbt_float8_picksplit
CREATE OR REPLACE FUNCTION public.gbt_float8_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float8_picksplit$function$
;


-- Fonction: public.gbt_float8_same
CREATE OR REPLACE FUNCTION public.gbt_float8_same(gbtreekey16, gbtreekey16, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float8_same$function$
;


-- Fonction: public.gbt_float8_union
CREATE OR REPLACE FUNCTION public.gbt_float8_union(internal, internal)
 RETURNS gbtreekey16
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_float8_union$function$
;


-- Fonction: public.gbt_inet_compress
CREATE OR REPLACE FUNCTION public.gbt_inet_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_inet_compress$function$
;


-- Fonction: public.gbt_inet_consistent
CREATE OR REPLACE FUNCTION public.gbt_inet_consistent(internal, inet, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_inet_consistent$function$
;


-- Fonction: public.gbt_inet_penalty
CREATE OR REPLACE FUNCTION public.gbt_inet_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_inet_penalty$function$
;


-- Fonction: public.gbt_inet_picksplit
CREATE OR REPLACE FUNCTION public.gbt_inet_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_inet_picksplit$function$
;


-- Fonction: public.gbt_inet_same
CREATE OR REPLACE FUNCTION public.gbt_inet_same(gbtreekey16, gbtreekey16, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_inet_same$function$
;


-- Fonction: public.gbt_inet_union
CREATE OR REPLACE FUNCTION public.gbt_inet_union(internal, internal)
 RETURNS gbtreekey16
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_inet_union$function$
;


-- Fonction: public.gbt_int2_compress
CREATE OR REPLACE FUNCTION public.gbt_int2_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int2_compress$function$
;


-- Fonction: public.gbt_int2_consistent
CREATE OR REPLACE FUNCTION public.gbt_int2_consistent(internal, smallint, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int2_consistent$function$
;


-- Fonction: public.gbt_int2_distance
CREATE OR REPLACE FUNCTION public.gbt_int2_distance(internal, smallint, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int2_distance$function$
;


-- Fonction: public.gbt_int2_fetch
CREATE OR REPLACE FUNCTION public.gbt_int2_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int2_fetch$function$
;


-- Fonction: public.gbt_int2_penalty
CREATE OR REPLACE FUNCTION public.gbt_int2_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int2_penalty$function$
;


-- Fonction: public.gbt_int2_picksplit
CREATE OR REPLACE FUNCTION public.gbt_int2_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int2_picksplit$function$
;


-- Fonction: public.gbt_int2_same
CREATE OR REPLACE FUNCTION public.gbt_int2_same(gbtreekey4, gbtreekey4, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int2_same$function$
;


-- Fonction: public.gbt_int2_union
CREATE OR REPLACE FUNCTION public.gbt_int2_union(internal, internal)
 RETURNS gbtreekey4
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int2_union$function$
;


-- Fonction: public.gbt_int4_compress
CREATE OR REPLACE FUNCTION public.gbt_int4_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int4_compress$function$
;


-- Fonction: public.gbt_int4_consistent
CREATE OR REPLACE FUNCTION public.gbt_int4_consistent(internal, integer, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int4_consistent$function$
;


-- Fonction: public.gbt_int4_distance
CREATE OR REPLACE FUNCTION public.gbt_int4_distance(internal, integer, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int4_distance$function$
;


-- Fonction: public.gbt_int4_fetch
CREATE OR REPLACE FUNCTION public.gbt_int4_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int4_fetch$function$
;


-- Fonction: public.gbt_int4_penalty
CREATE OR REPLACE FUNCTION public.gbt_int4_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int4_penalty$function$
;


-- Fonction: public.gbt_int4_picksplit
CREATE OR REPLACE FUNCTION public.gbt_int4_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int4_picksplit$function$
;


-- Fonction: public.gbt_int4_same
CREATE OR REPLACE FUNCTION public.gbt_int4_same(gbtreekey8, gbtreekey8, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int4_same$function$
;


-- Fonction: public.gbt_int4_union
CREATE OR REPLACE FUNCTION public.gbt_int4_union(internal, internal)
 RETURNS gbtreekey8
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int4_union$function$
;


-- Fonction: public.gbt_int8_compress
CREATE OR REPLACE FUNCTION public.gbt_int8_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int8_compress$function$
;


-- Fonction: public.gbt_int8_consistent
CREATE OR REPLACE FUNCTION public.gbt_int8_consistent(internal, bigint, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int8_consistent$function$
;


-- Fonction: public.gbt_int8_distance
CREATE OR REPLACE FUNCTION public.gbt_int8_distance(internal, bigint, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int8_distance$function$
;


-- Fonction: public.gbt_int8_fetch
CREATE OR REPLACE FUNCTION public.gbt_int8_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int8_fetch$function$
;


-- Fonction: public.gbt_int8_penalty
CREATE OR REPLACE FUNCTION public.gbt_int8_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int8_penalty$function$
;


-- Fonction: public.gbt_int8_picksplit
CREATE OR REPLACE FUNCTION public.gbt_int8_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int8_picksplit$function$
;


-- Fonction: public.gbt_int8_same
CREATE OR REPLACE FUNCTION public.gbt_int8_same(gbtreekey16, gbtreekey16, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int8_same$function$
;


-- Fonction: public.gbt_int8_union
CREATE OR REPLACE FUNCTION public.gbt_int8_union(internal, internal)
 RETURNS gbtreekey16
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_int8_union$function$
;


-- Fonction: public.gbt_intv_compress
CREATE OR REPLACE FUNCTION public.gbt_intv_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_intv_compress$function$
;


-- Fonction: public.gbt_intv_consistent
CREATE OR REPLACE FUNCTION public.gbt_intv_consistent(internal, interval, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_intv_consistent$function$
;


-- Fonction: public.gbt_intv_decompress
CREATE OR REPLACE FUNCTION public.gbt_intv_decompress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_intv_decompress$function$
;


-- Fonction: public.gbt_intv_distance
CREATE OR REPLACE FUNCTION public.gbt_intv_distance(internal, interval, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_intv_distance$function$
;


-- Fonction: public.gbt_intv_fetch
CREATE OR REPLACE FUNCTION public.gbt_intv_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_intv_fetch$function$
;


-- Fonction: public.gbt_intv_penalty
CREATE OR REPLACE FUNCTION public.gbt_intv_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_intv_penalty$function$
;


-- Fonction: public.gbt_intv_picksplit
CREATE OR REPLACE FUNCTION public.gbt_intv_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_intv_picksplit$function$
;


-- Fonction: public.gbt_intv_same
CREATE OR REPLACE FUNCTION public.gbt_intv_same(gbtreekey32, gbtreekey32, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_intv_same$function$
;


-- Fonction: public.gbt_intv_union
CREATE OR REPLACE FUNCTION public.gbt_intv_union(internal, internal)
 RETURNS gbtreekey32
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_intv_union$function$
;


-- Fonction: public.gbt_macad8_compress
CREATE OR REPLACE FUNCTION public.gbt_macad8_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad8_compress$function$
;


-- Fonction: public.gbt_macad8_consistent
CREATE OR REPLACE FUNCTION public.gbt_macad8_consistent(internal, macaddr8, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad8_consistent$function$
;


-- Fonction: public.gbt_macad8_fetch
CREATE OR REPLACE FUNCTION public.gbt_macad8_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad8_fetch$function$
;


-- Fonction: public.gbt_macad8_penalty
CREATE OR REPLACE FUNCTION public.gbt_macad8_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad8_penalty$function$
;


-- Fonction: public.gbt_macad8_picksplit
CREATE OR REPLACE FUNCTION public.gbt_macad8_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad8_picksplit$function$
;


-- Fonction: public.gbt_macad8_same
CREATE OR REPLACE FUNCTION public.gbt_macad8_same(gbtreekey16, gbtreekey16, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad8_same$function$
;


-- Fonction: public.gbt_macad8_union
CREATE OR REPLACE FUNCTION public.gbt_macad8_union(internal, internal)
 RETURNS gbtreekey16
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad8_union$function$
;


-- Fonction: public.gbt_macad_compress
CREATE OR REPLACE FUNCTION public.gbt_macad_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad_compress$function$
;


-- Fonction: public.gbt_macad_consistent
CREATE OR REPLACE FUNCTION public.gbt_macad_consistent(internal, macaddr, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad_consistent$function$
;


-- Fonction: public.gbt_macad_fetch
CREATE OR REPLACE FUNCTION public.gbt_macad_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad_fetch$function$
;


-- Fonction: public.gbt_macad_penalty
CREATE OR REPLACE FUNCTION public.gbt_macad_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad_penalty$function$
;


-- Fonction: public.gbt_macad_picksplit
CREATE OR REPLACE FUNCTION public.gbt_macad_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad_picksplit$function$
;


-- Fonction: public.gbt_macad_same
CREATE OR REPLACE FUNCTION public.gbt_macad_same(gbtreekey16, gbtreekey16, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad_same$function$
;


-- Fonction: public.gbt_macad_union
CREATE OR REPLACE FUNCTION public.gbt_macad_union(internal, internal)
 RETURNS gbtreekey16
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_macad_union$function$
;


-- Fonction: public.gbt_numeric_compress
CREATE OR REPLACE FUNCTION public.gbt_numeric_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_numeric_compress$function$
;


-- Fonction: public.gbt_numeric_consistent
CREATE OR REPLACE FUNCTION public.gbt_numeric_consistent(internal, numeric, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_numeric_consistent$function$
;


-- Fonction: public.gbt_numeric_penalty
CREATE OR REPLACE FUNCTION public.gbt_numeric_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_numeric_penalty$function$
;


-- Fonction: public.gbt_numeric_picksplit
CREATE OR REPLACE FUNCTION public.gbt_numeric_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_numeric_picksplit$function$
;


-- Fonction: public.gbt_numeric_same
CREATE OR REPLACE FUNCTION public.gbt_numeric_same(gbtreekey_var, gbtreekey_var, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_numeric_same$function$
;


-- Fonction: public.gbt_numeric_union
CREATE OR REPLACE FUNCTION public.gbt_numeric_union(internal, internal)
 RETURNS gbtreekey_var
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_numeric_union$function$
;


-- Fonction: public.gbt_oid_compress
CREATE OR REPLACE FUNCTION public.gbt_oid_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_oid_compress$function$
;


-- Fonction: public.gbt_oid_consistent
CREATE OR REPLACE FUNCTION public.gbt_oid_consistent(internal, oid, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_oid_consistent$function$
;


-- Fonction: public.gbt_oid_distance
CREATE OR REPLACE FUNCTION public.gbt_oid_distance(internal, oid, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_oid_distance$function$
;


-- Fonction: public.gbt_oid_fetch
CREATE OR REPLACE FUNCTION public.gbt_oid_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_oid_fetch$function$
;


-- Fonction: public.gbt_oid_penalty
CREATE OR REPLACE FUNCTION public.gbt_oid_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_oid_penalty$function$
;


-- Fonction: public.gbt_oid_picksplit
CREATE OR REPLACE FUNCTION public.gbt_oid_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_oid_picksplit$function$
;


-- Fonction: public.gbt_oid_same
CREATE OR REPLACE FUNCTION public.gbt_oid_same(gbtreekey8, gbtreekey8, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_oid_same$function$
;


-- Fonction: public.gbt_oid_union
CREATE OR REPLACE FUNCTION public.gbt_oid_union(internal, internal)
 RETURNS gbtreekey8
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_oid_union$function$
;


-- Fonction: public.gbt_text_compress
CREATE OR REPLACE FUNCTION public.gbt_text_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_text_compress$function$
;


-- Fonction: public.gbt_text_consistent
CREATE OR REPLACE FUNCTION public.gbt_text_consistent(internal, text, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_text_consistent$function$
;


-- Fonction: public.gbt_text_penalty
CREATE OR REPLACE FUNCTION public.gbt_text_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_text_penalty$function$
;


-- Fonction: public.gbt_text_picksplit
CREATE OR REPLACE FUNCTION public.gbt_text_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_text_picksplit$function$
;


-- Fonction: public.gbt_text_same
CREATE OR REPLACE FUNCTION public.gbt_text_same(gbtreekey_var, gbtreekey_var, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_text_same$function$
;


-- Fonction: public.gbt_text_union
CREATE OR REPLACE FUNCTION public.gbt_text_union(internal, internal)
 RETURNS gbtreekey_var
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_text_union$function$
;


-- Fonction: public.gbt_time_compress
CREATE OR REPLACE FUNCTION public.gbt_time_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_time_compress$function$
;


-- Fonction: public.gbt_time_consistent
CREATE OR REPLACE FUNCTION public.gbt_time_consistent(internal, time without time zone, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_time_consistent$function$
;


-- Fonction: public.gbt_time_distance
CREATE OR REPLACE FUNCTION public.gbt_time_distance(internal, time without time zone, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_time_distance$function$
;


-- Fonction: public.gbt_time_fetch
CREATE OR REPLACE FUNCTION public.gbt_time_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_time_fetch$function$
;


-- Fonction: public.gbt_time_penalty
CREATE OR REPLACE FUNCTION public.gbt_time_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_time_penalty$function$
;


-- Fonction: public.gbt_time_picksplit
CREATE OR REPLACE FUNCTION public.gbt_time_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_time_picksplit$function$
;


-- Fonction: public.gbt_time_same
CREATE OR REPLACE FUNCTION public.gbt_time_same(gbtreekey16, gbtreekey16, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_time_same$function$
;


-- Fonction: public.gbt_time_union
CREATE OR REPLACE FUNCTION public.gbt_time_union(internal, internal)
 RETURNS gbtreekey16
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_time_union$function$
;


-- Fonction: public.gbt_timetz_compress
CREATE OR REPLACE FUNCTION public.gbt_timetz_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_timetz_compress$function$
;


-- Fonction: public.gbt_timetz_consistent
CREATE OR REPLACE FUNCTION public.gbt_timetz_consistent(internal, time with time zone, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_timetz_consistent$function$
;


-- Fonction: public.gbt_ts_compress
CREATE OR REPLACE FUNCTION public.gbt_ts_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_ts_compress$function$
;


-- Fonction: public.gbt_ts_consistent
CREATE OR REPLACE FUNCTION public.gbt_ts_consistent(internal, timestamp without time zone, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_ts_consistent$function$
;


-- Fonction: public.gbt_ts_distance
CREATE OR REPLACE FUNCTION public.gbt_ts_distance(internal, timestamp without time zone, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_ts_distance$function$
;


-- Fonction: public.gbt_ts_fetch
CREATE OR REPLACE FUNCTION public.gbt_ts_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_ts_fetch$function$
;


-- Fonction: public.gbt_ts_penalty
CREATE OR REPLACE FUNCTION public.gbt_ts_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_ts_penalty$function$
;


-- Fonction: public.gbt_ts_picksplit
CREATE OR REPLACE FUNCTION public.gbt_ts_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_ts_picksplit$function$
;


-- Fonction: public.gbt_ts_same
CREATE OR REPLACE FUNCTION public.gbt_ts_same(gbtreekey16, gbtreekey16, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_ts_same$function$
;


-- Fonction: public.gbt_ts_union
CREATE OR REPLACE FUNCTION public.gbt_ts_union(internal, internal)
 RETURNS gbtreekey16
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_ts_union$function$
;


-- Fonction: public.gbt_tstz_compress
CREATE OR REPLACE FUNCTION public.gbt_tstz_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_tstz_compress$function$
;


-- Fonction: public.gbt_tstz_consistent
CREATE OR REPLACE FUNCTION public.gbt_tstz_consistent(internal, timestamp with time zone, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_tstz_consistent$function$
;


-- Fonction: public.gbt_tstz_distance
CREATE OR REPLACE FUNCTION public.gbt_tstz_distance(internal, timestamp with time zone, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_tstz_distance$function$
;


-- Fonction: public.gbt_uuid_compress
CREATE OR REPLACE FUNCTION public.gbt_uuid_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_uuid_compress$function$
;


-- Fonction: public.gbt_uuid_consistent
CREATE OR REPLACE FUNCTION public.gbt_uuid_consistent(internal, uuid, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_uuid_consistent$function$
;


-- Fonction: public.gbt_uuid_fetch
CREATE OR REPLACE FUNCTION public.gbt_uuid_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_uuid_fetch$function$
;


-- Fonction: public.gbt_uuid_penalty
CREATE OR REPLACE FUNCTION public.gbt_uuid_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_uuid_penalty$function$
;


-- Fonction: public.gbt_uuid_picksplit
CREATE OR REPLACE FUNCTION public.gbt_uuid_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_uuid_picksplit$function$
;


-- Fonction: public.gbt_uuid_same
CREATE OR REPLACE FUNCTION public.gbt_uuid_same(gbtreekey32, gbtreekey32, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_uuid_same$function$
;


-- Fonction: public.gbt_uuid_union
CREATE OR REPLACE FUNCTION public.gbt_uuid_union(internal, internal)
 RETURNS gbtreekey32
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_uuid_union$function$
;


-- Fonction: public.gbt_var_decompress
CREATE OR REPLACE FUNCTION public.gbt_var_decompress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_var_decompress$function$
;


-- Fonction: public.gbt_var_fetch
CREATE OR REPLACE FUNCTION public.gbt_var_fetch(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbt_var_fetch$function$
;


-- Fonction: public.gbtreekey16_in
CREATE OR REPLACE FUNCTION public.gbtreekey16_in(cstring)
 RETURNS gbtreekey16
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_in$function$
;


-- Fonction: public.gbtreekey16_out
CREATE OR REPLACE FUNCTION public.gbtreekey16_out(gbtreekey16)
 RETURNS cstring
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_out$function$
;


-- Fonction: public.gbtreekey2_in
CREATE OR REPLACE FUNCTION public.gbtreekey2_in(cstring)
 RETURNS gbtreekey2
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_in$function$
;


-- Fonction: public.gbtreekey2_out
CREATE OR REPLACE FUNCTION public.gbtreekey2_out(gbtreekey2)
 RETURNS cstring
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_out$function$
;


-- Fonction: public.gbtreekey32_in
CREATE OR REPLACE FUNCTION public.gbtreekey32_in(cstring)
 RETURNS gbtreekey32
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_in$function$
;


-- Fonction: public.gbtreekey32_out
CREATE OR REPLACE FUNCTION public.gbtreekey32_out(gbtreekey32)
 RETURNS cstring
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_out$function$
;


-- Fonction: public.gbtreekey4_in
CREATE OR REPLACE FUNCTION public.gbtreekey4_in(cstring)
 RETURNS gbtreekey4
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_in$function$
;


-- Fonction: public.gbtreekey4_out
CREATE OR REPLACE FUNCTION public.gbtreekey4_out(gbtreekey4)
 RETURNS cstring
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_out$function$
;


-- Fonction: public.gbtreekey8_in
CREATE OR REPLACE FUNCTION public.gbtreekey8_in(cstring)
 RETURNS gbtreekey8
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_in$function$
;


-- Fonction: public.gbtreekey8_out
CREATE OR REPLACE FUNCTION public.gbtreekey8_out(gbtreekey8)
 RETURNS cstring
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_out$function$
;


-- Fonction: public.gbtreekey_var_in
CREATE OR REPLACE FUNCTION public.gbtreekey_var_in(cstring)
 RETURNS gbtreekey_var
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_in$function$
;


-- Fonction: public.gbtreekey_var_out
CREATE OR REPLACE FUNCTION public.gbtreekey_var_out(gbtreekey_var)
 RETURNS cstring
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$gbtreekey_out$function$
;


-- Fonction: public.gen_random_bytes
CREATE OR REPLACE FUNCTION public.gen_random_bytes(integer)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_random_bytes$function$
;


-- Fonction: public.gen_random_uuid
CREATE OR REPLACE FUNCTION public.gen_random_uuid()
 RETURNS uuid
 LANGUAGE c
 PARALLEL SAFE
AS '$libdir/pgcrypto', $function$pg_random_uuid$function$
;


-- Fonction: public.gen_salt
CREATE OR REPLACE FUNCTION public.gen_salt(text, integer)
 RETURNS text
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_gen_salt_rounds$function$
;


-- Fonction: public.gen_salt
CREATE OR REPLACE FUNCTION public.gen_salt(text)
 RETURNS text
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_gen_salt$function$
;


-- Fonction: public.gin_extract_query_trgm
CREATE OR REPLACE FUNCTION public.gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gin_extract_query_trgm$function$
;


-- Fonction: public.gin_extract_value_trgm
CREATE OR REPLACE FUNCTION public.gin_extract_value_trgm(text, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gin_extract_value_trgm$function$
;


-- Fonction: public.gin_trgm_consistent
CREATE OR REPLACE FUNCTION public.gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gin_trgm_consistent$function$
;


-- Fonction: public.gin_trgm_triconsistent
CREATE OR REPLACE FUNCTION public.gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal)
 RETURNS "char"
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gin_trgm_triconsistent$function$
;


-- Fonction: public.gtrgm_compress
CREATE OR REPLACE FUNCTION public.gtrgm_compress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_compress$function$
;


-- Fonction: public.gtrgm_consistent
CREATE OR REPLACE FUNCTION public.gtrgm_consistent(internal, text, smallint, oid, internal)
 RETURNS boolean
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_consistent$function$
;


-- Fonction: public.gtrgm_decompress
CREATE OR REPLACE FUNCTION public.gtrgm_decompress(internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_decompress$function$
;


-- Fonction: public.gtrgm_distance
CREATE OR REPLACE FUNCTION public.gtrgm_distance(internal, text, smallint, oid, internal)
 RETURNS double precision
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_distance$function$
;


-- Fonction: public.gtrgm_in
CREATE OR REPLACE FUNCTION public.gtrgm_in(cstring)
 RETURNS gtrgm
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_in$function$
;


-- Fonction: public.gtrgm_options
CREATE OR REPLACE FUNCTION public.gtrgm_options(internal)
 RETURNS void
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE
AS '$libdir/pg_trgm', $function$gtrgm_options$function$
;


-- Fonction: public.gtrgm_out
CREATE OR REPLACE FUNCTION public.gtrgm_out(gtrgm)
 RETURNS cstring
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_out$function$
;


-- Fonction: public.gtrgm_penalty
CREATE OR REPLACE FUNCTION public.gtrgm_penalty(internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_penalty$function$
;


-- Fonction: public.gtrgm_picksplit
CREATE OR REPLACE FUNCTION public.gtrgm_picksplit(internal, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_picksplit$function$
;


-- Fonction: public.gtrgm_same
CREATE OR REPLACE FUNCTION public.gtrgm_same(gtrgm, gtrgm, internal)
 RETURNS internal
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_same$function$
;


-- Fonction: public.gtrgm_union
CREATE OR REPLACE FUNCTION public.gtrgm_union(internal, internal)
 RETURNS gtrgm
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$gtrgm_union$function$
;


-- Fonction: public.hmac
CREATE OR REPLACE FUNCTION public.hmac(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_hmac$function$
;


-- Fonction: public.hmac
CREATE OR REPLACE FUNCTION public.hmac(text, text, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_hmac$function$
;


-- Fonction: public.immutable_unaccent
CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$SELECT unaccent($1)$function$
;


-- Fonction: public.int2_dist
CREATE OR REPLACE FUNCTION public.int2_dist(smallint, smallint)
 RETURNS smallint
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$int2_dist$function$
;


-- Fonction: public.int4_dist
CREATE OR REPLACE FUNCTION public.int4_dist(integer, integer)
 RETURNS integer
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$int4_dist$function$
;


-- Fonction: public.int8_dist
CREATE OR REPLACE FUNCTION public.int8_dist(bigint, bigint)
 RETURNS bigint
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$int8_dist$function$
;


-- Fonction: public.interval_dist
CREATE OR REPLACE FUNCTION public.interval_dist(interval, interval)
 RETURNS interval
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$interval_dist$function$
;


-- Fonction: public.oid_dist
CREATE OR REPLACE FUNCTION public.oid_dist(oid, oid)
 RETURNS oid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$oid_dist$function$
;


-- Fonction: public.pgp_armor_headers
CREATE OR REPLACE FUNCTION public.pgp_armor_headers(text, OUT key text, OUT value text)
 RETURNS SETOF record
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_armor_headers$function$
;


-- Fonction: public.pgp_key_id
CREATE OR REPLACE FUNCTION public.pgp_key_id(bytea)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_key_id_w$function$
;


-- Fonction: public.pgp_pub_decrypt
CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt(bytea, bytea)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_text$function$
;


-- Fonction: public.pgp_pub_decrypt
CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt(bytea, bytea, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_text$function$
;


-- Fonction: public.pgp_pub_decrypt
CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt(bytea, bytea, text, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_text$function$
;


-- Fonction: public.pgp_pub_decrypt_bytea
CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_bytea$function$
;


-- Fonction: public.pgp_pub_decrypt_bytea
CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_bytea$function$
;


-- Fonction: public.pgp_pub_decrypt_bytea
CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_bytea$function$
;


-- Fonction: public.pgp_pub_encrypt
CREATE OR REPLACE FUNCTION public.pgp_pub_encrypt(text, bytea, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_encrypt_text$function$
;


-- Fonction: public.pgp_pub_encrypt
CREATE OR REPLACE FUNCTION public.pgp_pub_encrypt(text, bytea)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_encrypt_text$function$
;


-- Fonction: public.pgp_pub_encrypt_bytea
CREATE OR REPLACE FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_encrypt_bytea$function$
;


-- Fonction: public.pgp_pub_encrypt_bytea
CREATE OR REPLACE FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_encrypt_bytea$function$
;


-- Fonction: public.pgp_sym_decrypt
CREATE OR REPLACE FUNCTION public.pgp_sym_decrypt(bytea, text, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_decrypt_text$function$
;


-- Fonction: public.pgp_sym_decrypt
CREATE OR REPLACE FUNCTION public.pgp_sym_decrypt(bytea, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_decrypt_text$function$
;


-- Fonction: public.pgp_sym_decrypt_bytea
CREATE OR REPLACE FUNCTION public.pgp_sym_decrypt_bytea(bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_decrypt_bytea$function$
;


-- Fonction: public.pgp_sym_decrypt_bytea
CREATE OR REPLACE FUNCTION public.pgp_sym_decrypt_bytea(bytea, text, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_decrypt_bytea$function$
;


-- Fonction: public.pgp_sym_encrypt
CREATE OR REPLACE FUNCTION public.pgp_sym_encrypt(text, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_encrypt_text$function$
;


-- Fonction: public.pgp_sym_encrypt
CREATE OR REPLACE FUNCTION public.pgp_sym_encrypt(text, text, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_encrypt_text$function$
;


-- Fonction: public.pgp_sym_encrypt_bytea
CREATE OR REPLACE FUNCTION public.pgp_sym_encrypt_bytea(bytea, text, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_encrypt_bytea$function$
;


-- Fonction: public.pgp_sym_encrypt_bytea
CREATE OR REPLACE FUNCTION public.pgp_sym_encrypt_bytea(bytea, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_encrypt_bytea$function$
;


-- Fonction: public.set_limit
CREATE OR REPLACE FUNCTION public.set_limit(real)
 RETURNS real
 LANGUAGE c
 STRICT
AS '$libdir/pg_trgm', $function$set_limit$function$
;


-- Fonction: public.show_limit
CREATE OR REPLACE FUNCTION public.show_limit()
 RETURNS real
 LANGUAGE c
 STABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$show_limit$function$
;


-- Fonction: public.show_trgm
CREATE OR REPLACE FUNCTION public.show_trgm(text)
 RETURNS text[]
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$show_trgm$function$
;


-- Fonction: public.similarity
CREATE OR REPLACE FUNCTION public.similarity(text, text)
 RETURNS real
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$similarity$function$
;


-- Fonction: public.similarity_dist
CREATE OR REPLACE FUNCTION public.similarity_dist(text, text)
 RETURNS real
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$similarity_dist$function$
;


-- Fonction: public.similarity_op
CREATE OR REPLACE FUNCTION public.similarity_op(text, text)
 RETURNS boolean
 LANGUAGE c
 STABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$similarity_op$function$
;


-- Fonction: public.strict_word_similarity
CREATE OR REPLACE FUNCTION public.strict_word_similarity(text, text)
 RETURNS real
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$strict_word_similarity$function$
;


-- Fonction: public.strict_word_similarity_commutator_op
CREATE OR REPLACE FUNCTION public.strict_word_similarity_commutator_op(text, text)
 RETURNS boolean
 LANGUAGE c
 STABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$strict_word_similarity_commutator_op$function$
;


-- Fonction: public.strict_word_similarity_dist_commutator_op
CREATE OR REPLACE FUNCTION public.strict_word_similarity_dist_commutator_op(text, text)
 RETURNS real
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$strict_word_similarity_dist_commutator_op$function$
;


-- Fonction: public.strict_word_similarity_dist_op
CREATE OR REPLACE FUNCTION public.strict_word_similarity_dist_op(text, text)
 RETURNS real
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$strict_word_similarity_dist_op$function$
;


-- Fonction: public.strict_word_similarity_op
CREATE OR REPLACE FUNCTION public.strict_word_similarity_op(text, text)
 RETURNS boolean
 LANGUAGE c
 STABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$strict_word_similarity_op$function$
;


-- Fonction: public.time_dist
CREATE OR REPLACE FUNCTION public.time_dist(time without time zone, time without time zone)
 RETURNS interval
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$time_dist$function$
;


-- Fonction: public.ts_dist
CREATE OR REPLACE FUNCTION public.ts_dist(timestamp without time zone, timestamp without time zone)
 RETURNS interval
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$ts_dist$function$
;


-- Fonction: public.tstz_dist
CREATE OR REPLACE FUNCTION public.tstz_dist(timestamp with time zone, timestamp with time zone)
 RETURNS interval
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/btree_gist', $function$tstz_dist$function$
;


-- Fonction: public.unaccent
CREATE OR REPLACE FUNCTION public.unaccent(text)
 RETURNS text
 LANGUAGE c
 STABLE PARALLEL SAFE STRICT
AS '$libdir/unaccent', $function$unaccent_dict$function$
;


-- Fonction: public.unaccent
CREATE OR REPLACE FUNCTION public.unaccent(regdictionary, text)
 RETURNS text
 LANGUAGE c
 STABLE PARALLEL SAFE STRICT
AS '$libdir/unaccent', $function$unaccent_dict$function$
;


-- Fonction: public.unaccent_init
CREATE OR REPLACE FUNCTION public.unaccent_init(internal)
 RETURNS internal
 LANGUAGE c
 PARALLEL SAFE
AS '$libdir/unaccent', $function$unaccent_init$function$
;


-- Fonction: public.unaccent_lexize
CREATE OR REPLACE FUNCTION public.unaccent_lexize(internal, internal, internal, internal)
 RETURNS internal
 LANGUAGE c
 PARALLEL SAFE
AS '$libdir/unaccent', $function$unaccent_lexize$function$
;


-- Fonction: public.uuid_generate_v1
CREATE OR REPLACE FUNCTION public.uuid_generate_v1()
 RETURNS uuid
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v1$function$
;


-- Fonction: public.uuid_generate_v1mc
CREATE OR REPLACE FUNCTION public.uuid_generate_v1mc()
 RETURNS uuid
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v1mc$function$
;


-- Fonction: public.uuid_generate_v3
CREATE OR REPLACE FUNCTION public.uuid_generate_v3(namespace uuid, name text)
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v3$function$
;


-- Fonction: public.uuid_generate_v4
CREATE OR REPLACE FUNCTION public.uuid_generate_v4()
 RETURNS uuid
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v4$function$
;


-- Fonction: public.uuid_generate_v5
CREATE OR REPLACE FUNCTION public.uuid_generate_v5(namespace uuid, name text)
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v5$function$
;


-- Fonction: public.uuid_nil
CREATE OR REPLACE FUNCTION public.uuid_nil()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_nil$function$
;


-- Fonction: public.uuid_ns_dns
CREATE OR REPLACE FUNCTION public.uuid_ns_dns()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_ns_dns$function$
;


-- Fonction: public.uuid_ns_oid
CREATE OR REPLACE FUNCTION public.uuid_ns_oid()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_ns_oid$function$
;


-- Fonction: public.uuid_ns_url
CREATE OR REPLACE FUNCTION public.uuid_ns_url()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_ns_url$function$
;


-- Fonction: public.uuid_ns_x500
CREATE OR REPLACE FUNCTION public.uuid_ns_x500()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_ns_x500$function$
;


-- Fonction: public.word_similarity
CREATE OR REPLACE FUNCTION public.word_similarity(text, text)
 RETURNS real
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$word_similarity$function$
;


-- Fonction: public.word_similarity_commutator_op
CREATE OR REPLACE FUNCTION public.word_similarity_commutator_op(text, text)
 RETURNS boolean
 LANGUAGE c
 STABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$word_similarity_commutator_op$function$
;


-- Fonction: public.word_similarity_dist_commutator_op
CREATE OR REPLACE FUNCTION public.word_similarity_dist_commutator_op(text, text)
 RETURNS real
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$word_similarity_dist_commutator_op$function$
;


-- Fonction: public.word_similarity_dist_op
CREATE OR REPLACE FUNCTION public.word_similarity_dist_op(text, text)
 RETURNS real
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$word_similarity_dist_op$function$
;


-- Fonction: public.word_similarity_op
CREATE OR REPLACE FUNCTION public.word_similarity_op(text, text)
 RETURNS boolean
 LANGUAGE c
 STABLE PARALLEL SAFE STRICT
AS '$libdir/pg_trgm', $function$word_similarity_op$function$
;


-- Fonction: security.prevent_audit_delete
CREATE OR REPLACE FUNCTION security.prevent_audit_delete()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only: DELETE operation is forbidden';
        END;
        $function$
;


-- Fonction: superset.fiscal_month
CREATE OR REPLACE FUNCTION superset.fiscal_month(d date, end_month integer DEFAULT 6)
 RETURNS integer
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    -- Mois fiscal : décalage depuis mois de fin d'exercice + 1
    -- Ex: si end_month=6 (juin) : juillet=1, août=2, ..., juin=12
    RETURN ((EXTRACT(MONTH FROM d)::INT - end_month - 1 + 12) % 12) + 1;
END;
$function$
;


-- Fonction: superset.fiscal_year
CREATE OR REPLACE FUNCTION superset.fiscal_year(d date, end_month integer DEFAULT 6)
 RETURNS integer
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    -- Si mois > end_month (ex: juillet-décembre), exercice = année suivante
    -- Sinon exercice = année courante
    IF EXTRACT(MONTH FROM d) > end_month THEN
        RETURN EXTRACT(YEAR FROM d)::INT + 1;
    ELSE
        RETURN EXTRACT(YEAR FROM d)::INT;
    END IF;
END;
$function$
;

-- ============================================================================
-- INDEX
-- ============================================================================
-- Index: core.budget_posts_pkey sur core.budget_posts
CREATE UNIQUE INDEX budget_posts_pkey ON core.budget_posts USING btree (budget_post_id);

-- Index: core.idx_budget_posts_active sur core.budget_posts
CREATE INDEX idx_budget_posts_active ON core.budget_posts USING btree (active);

-- Index: core.uq_budget_posts_code sur core.budget_posts
CREATE UNIQUE INDEX uq_budget_posts_code ON core.budget_posts USING btree (code);

-- Index: core.employee_job_history_pkey sur core.employee_job_history
CREATE UNIQUE INDEX employee_job_history_pkey ON core.employee_job_history USING btree (history_id);

-- Index: core.excl_employee_job_history_no_overlap sur core.employee_job_history
CREATE INDEX excl_employee_job_history_no_overlap ON core.employee_job_history USING gist (employee_id, daterange(date_debut, COALESCE(date_fin, 'infinity'::date), '[]'::text));

-- Index: core.idx_emp_job_hist_code sur core.employee_job_history
CREATE INDEX idx_emp_job_hist_code ON core.employee_job_history USING btree (code_id);

-- Index: core.idx_emp_job_hist_dates sur core.employee_job_history
CREATE INDEX idx_emp_job_hist_dates ON core.employee_job_history USING btree (date_debut, date_fin);

-- Index: core.idx_emp_job_hist_employee sur core.employee_job_history
CREATE INDEX idx_emp_job_hist_employee ON core.employee_job_history USING btree (employee_id);

-- Index: core.employees_employee_key_key sur core.employees
CREATE UNIQUE INDEX employees_employee_key_key ON core.employees USING btree (employee_key);

-- Index: core.employees_pkey sur core.employees
CREATE UNIQUE INDEX employees_pkey ON core.employees USING btree (employee_id);

-- Index: core.idx_employees_key sur core.employees
CREATE UNIQUE INDEX idx_employees_key ON core.employees USING btree (employee_key);

-- Index: core.idx_employees_matricule sur core.employees
CREATE INDEX idx_employees_matricule ON core.employees USING btree (matricule_norm) WHERE (matricule_norm IS NOT NULL);

-- Index: core.idx_employees_matricule_trgm sur core.employees
CREATE INDEX idx_employees_matricule_trgm ON core.employees USING gin (matricule_norm gin_trgm_ops);

-- Index: core.idx_employees_nom sur core.employees
CREATE INDEX idx_employees_nom ON core.employees USING btree (nom_norm, prenom_norm);

-- Index: core.idx_employees_nom_trgm sur core.employees
CREATE INDEX idx_employees_nom_trgm ON core.employees USING gin (lower((nom_complet)::text) gin_trgm_ops);

-- Index: core.idx_employees_statut sur core.employees
CREATE INDEX idx_employees_statut ON core.employees USING btree (statut);

-- Index: core.ux_core_employees_matricule sur core.employees
CREATE UNIQUE INDEX ux_core_employees_matricule ON core.employees USING btree (matricule);

-- Index: core.ux_employees_matricule sur core.employees
CREATE UNIQUE INDEX ux_employees_matricule ON core.employees USING btree (matricule);

-- Index: core.job_categories_pkey sur core.job_categories
CREATE UNIQUE INDEX job_categories_pkey ON core.job_categories USING btree (category_id);

-- Index: core.uq_job_categories_nom sur core.job_categories
CREATE UNIQUE INDEX uq_job_categories_nom ON core.job_categories USING btree (nom);

-- Index: core.idx_job_codes_category sur core.job_codes
CREATE INDEX idx_job_codes_category ON core.job_codes USING btree (category_id);

-- Index: core.job_codes_pkey sur core.job_codes
CREATE UNIQUE INDEX job_codes_pkey ON core.job_codes USING btree (code_id);

-- Index: core.uq_job_codes_code sur core.job_codes
CREATE UNIQUE INDEX uq_job_codes_code ON core.job_codes USING btree (code);

-- Index: core.idx_pay_codes_active sur core.pay_codes
CREATE INDEX idx_pay_codes_active ON core.pay_codes USING btree (active);

-- Index: core.idx_pay_codes_category sur core.pay_codes
CREATE INDEX idx_pay_codes_category ON core.pay_codes USING btree (category);

-- Index: core.pay_codes_pkey sur core.pay_codes
CREATE UNIQUE INDEX pay_codes_pkey ON core.pay_codes USING btree (pay_code);

-- Index: paie.dedup_log_pkey sur paie.dedup_log
CREATE UNIQUE INDEX dedup_log_pkey ON paie.dedup_log USING btree (dedup_id);

-- Index: paie.idx_dedup_log_batch sur paie.dedup_log
CREATE INDEX idx_dedup_log_batch ON paie.dedup_log USING btree (source_batch_id);

-- Index: paie.idx_dedup_log_cle sur paie.dedup_log
CREATE INDEX idx_dedup_log_cle ON paie.dedup_log USING btree (cle_metier);

-- Index: paie.dim_code_paie_code_paie_key sur paie.dim_code_paie
CREATE UNIQUE INDEX dim_code_paie_code_paie_key ON paie.dim_code_paie USING btree (code_paie);

-- Index: paie.dim_code_paie_pkey sur paie.dim_code_paie
CREATE UNIQUE INDEX dim_code_paie_pkey ON paie.dim_code_paie USING btree (code_paie_id);

-- Index: paie.idx_dim_code_paie_actif sur paie.dim_code_paie
CREATE INDEX idx_dim_code_paie_actif ON paie.dim_code_paie USING btree (actif);

-- Index: paie.idx_dim_code_paie_categorie sur paie.dim_code_paie
CREATE INDEX idx_dim_code_paie_categorie ON paie.dim_code_paie USING btree (categorie_paie);

-- Index: paie.dim_emploi_code_emploi_key sur paie.dim_emploi
CREATE UNIQUE INDEX dim_emploi_code_emploi_key ON paie.dim_emploi USING btree (code_emploi);

-- Index: paie.dim_emploi_pkey sur paie.dim_emploi
CREATE UNIQUE INDEX dim_emploi_pkey ON paie.dim_emploi USING btree (emploi_id);

-- Index: paie.idx_dim_emploi_categorie sur paie.dim_emploi
CREATE INDEX idx_dim_emploi_categorie ON paie.dim_emploi USING btree (categorie_emploi);

-- Index: paie.dim_employe_matricule_key sur paie.dim_employe
CREATE UNIQUE INDEX dim_employe_matricule_key ON paie.dim_employe USING btree (matricule);

-- Index: paie.dim_employe_pkey sur paie.dim_employe
CREATE UNIQUE INDEX dim_employe_pkey ON paie.dim_employe USING btree (employe_id);

-- Index: paie.idx_dim_employe_matricule sur paie.dim_employe
CREATE INDEX idx_dim_employe_matricule ON paie.dim_employe USING btree (matricule);

-- Index: paie.idx_dim_employe_nom sur paie.dim_employe
CREATE INDEX idx_dim_employe_nom ON paie.dim_employe USING btree (nom_norm);

-- Index: paie.idx_dim_employe_statut sur paie.dim_employe
CREATE INDEX idx_dim_employe_statut ON paie.dim_employe USING btree (statut);

-- Index: paie.dim_poste_budgetaire_pkey sur paie.dim_poste_budgetaire
CREATE UNIQUE INDEX dim_poste_budgetaire_pkey ON paie.dim_poste_budgetaire USING btree (poste_budgetaire_id);

-- Index: paie.dim_poste_budgetaire_poste_budgetaire_key sur paie.dim_poste_budgetaire
CREATE UNIQUE INDEX dim_poste_budgetaire_poste_budgetaire_key ON paie.dim_poste_budgetaire USING btree (poste_budgetaire);

-- Index: paie.idx_dim_poste_budgetaire_actif sur paie.dim_poste_budgetaire
CREATE INDEX idx_dim_poste_budgetaire_actif ON paie.dim_poste_budgetaire USING btree (actif);

-- Index: paie.idx_dim_poste_budgetaire_segment1 sur paie.dim_poste_budgetaire
CREATE INDEX idx_dim_poste_budgetaire_segment1 ON paie.dim_poste_budgetaire USING btree (segment_1);

-- Index: paie.idx_dim_poste_fonction sur paie.dim_poste_budgetaire
CREATE INDEX idx_dim_poste_fonction ON paie.dim_poste_budgetaire USING btree (fonction);

-- Index: paie.idx_dim_poste_fonds sur paie.dim_poste_budgetaire
CREATE INDEX idx_dim_poste_fonds ON paie.dim_poste_budgetaire USING btree (fonds);

-- Index: paie.dim_temps_date_paie_key sur paie.dim_temps
CREATE UNIQUE INDEX dim_temps_date_paie_key ON paie.dim_temps USING btree (date_paie);

-- Index: paie.dim_temps_pkey sur paie.dim_temps
CREATE UNIQUE INDEX dim_temps_pkey ON paie.dim_temps USING btree (temps_id);

-- Index: paie.idx_dim_temps_annee sur paie.dim_temps
CREATE INDEX idx_dim_temps_annee ON paie.dim_temps USING btree (annee_paie);

-- Index: paie.idx_dim_temps_exercice sur paie.dim_temps
CREATE INDEX idx_dim_temps_exercice ON paie.dim_temps USING btree (exercice_fiscal);

-- Index: paie.idx_dim_temps_periode sur paie.dim_temps
CREATE INDEX idx_dim_temps_periode ON paie.dim_temps USING btree (periode_paie);

-- Index: paie.fact_paie_pkey sur paie.fact_paie
CREATE UNIQUE INDEX fact_paie_pkey ON paie.fact_paie USING btree (fact_id);

-- Index: paie.idx_fact_paie_batch sur paie.fact_paie
CREATE INDEX idx_fact_paie_batch ON paie.fact_paie USING btree (source_batch_id);

-- Index: paie.idx_fact_paie_cle_metier_unique sur paie.fact_paie
CREATE UNIQUE INDEX idx_fact_paie_cle_metier_unique ON paie.fact_paie USING btree (cle_metier);

-- Index: paie.idx_fact_paie_code_paie sur paie.fact_paie
CREATE INDEX idx_fact_paie_code_paie ON paie.fact_paie USING btree (code_paie_id);

-- Index: paie.idx_fact_paie_employe sur paie.fact_paie
CREATE INDEX idx_fact_paie_employe ON paie.fact_paie USING btree (employe_id);

-- Index: paie.idx_fact_paie_poste sur paie.fact_paie
CREATE INDEX idx_fact_paie_poste ON paie.fact_paie USING btree (poste_budgetaire_id);

-- Index: paie.idx_fact_paie_temps sur paie.fact_paie
CREATE INDEX idx_fact_paie_temps ON paie.fact_paie USING btree (temps_id);

-- Index: paie.uq_cle_metier sur paie.fact_paie
CREATE UNIQUE INDEX uq_cle_metier ON paie.fact_paie USING btree (cle_metier);

-- Index: paie.idx_import_batches_date sur paie.import_batches
CREATE INDEX idx_import_batches_date ON paie.import_batches USING btree (started_at);

-- Index: paie.idx_import_batches_statut sur paie.import_batches
CREATE INDEX idx_import_batches_statut ON paie.import_batches USING btree (statut);

-- Index: paie.import_batches_pkey sur paie.import_batches
CREATE UNIQUE INDEX import_batches_pkey ON paie.import_batches USING btree (batch_id);

-- Index: paie.idx_stg_batch sur paie.stg_paie_transactions
CREATE INDEX idx_stg_batch ON paie.stg_paie_transactions USING btree (source_batch_id);

-- Index: paie.idx_stg_date sur paie.stg_paie_transactions
CREATE INDEX idx_stg_date ON paie.stg_paie_transactions USING btree (date_paie);

-- Index: paie.idx_stg_valid sur paie.stg_paie_transactions
CREATE INDEX idx_stg_valid ON paie.stg_paie_transactions USING btree (is_valid);

-- Index: paie.stg_paie_transactions_pkey sur paie.stg_paie_transactions
CREATE UNIQUE INDEX stg_paie_transactions_pkey ON paie.stg_paie_transactions USING btree (stg_id);

-- Index: paie.idx_v_kpi_temps_annuel_annee sur paie.v_kpi_temps_annuel
CREATE UNIQUE INDEX idx_v_kpi_temps_annuel_annee ON paie.v_kpi_temps_annuel USING btree (annee_paie);

-- Index: paie.idx_v_kpi_temps_mensuel_mois sur paie.v_kpi_temps_mensuel
CREATE UNIQUE INDEX idx_v_kpi_temps_mensuel_mois ON paie.v_kpi_temps_mensuel USING btree (periode_paie);

-- Index: payroll.budget_posts_code_key sur payroll.budget_posts
CREATE UNIQUE INDEX budget_posts_code_key ON payroll.budget_posts USING btree (code);

-- Index: payroll.budget_posts_pkey sur payroll.budget_posts
CREATE UNIQUE INDEX budget_posts_pkey ON payroll.budget_posts USING btree (post_id);

-- Index: payroll.idx_batches_started sur payroll.import_batches
CREATE INDEX idx_batches_started ON payroll.import_batches USING btree (started_at DESC);

-- Index: payroll.idx_batches_status sur payroll.import_batches
CREATE INDEX idx_batches_status ON payroll.import_batches USING btree (status);

-- Index: payroll.import_batches_batch_uuid_key sur payroll.import_batches
CREATE UNIQUE INDEX import_batches_batch_uuid_key ON payroll.import_batches USING btree (batch_uuid);

-- Index: payroll.import_batches_pkey sur payroll.import_batches
CREATE UNIQUE INDEX import_batches_pkey ON payroll.import_batches USING btree (batch_id);

-- Index: payroll.idx_import_log_alert_type sur payroll.import_log
CREATE INDEX idx_import_log_alert_type ON payroll.import_log USING btree (alert_type);

-- Index: payroll.idx_import_log_run sur payroll.import_log
CREATE INDEX idx_import_log_run ON payroll.import_log USING btree (run_id);

-- Index: payroll.import_log_pkey sur payroll.import_log
CREATE UNIQUE INDEX import_log_pkey ON payroll.import_log USING btree (log_id);

-- Index: payroll.idx_import_runs_file sur payroll.import_runs
CREATE INDEX idx_import_runs_file ON payroll.import_runs USING btree (source_file);

-- Index: payroll.idx_import_runs_started sur payroll.import_runs
CREATE INDEX idx_import_runs_started ON payroll.import_runs USING btree (started_at DESC);

-- Index: payroll.import_runs_pkey sur payroll.import_runs
CREATE UNIQUE INDEX import_runs_pkey ON payroll.import_runs USING btree (run_id);

-- Index: payroll.idx_ipm_code_de_paie sur payroll.imported_payroll_master
CREATE INDEX idx_ipm_code_de_paie ON payroll.imported_payroll_master USING btree (code_paie) WHERE (code_paie IS NOT NULL);

-- Index: payroll.idx_ipm_code_paie sur payroll.imported_payroll_master
CREATE INDEX idx_ipm_code_paie ON payroll.imported_payroll_master USING btree (code_paie) WHERE (code_paie IS NOT NULL);

-- Index: payroll.idx_ipm_date_de_paie sur payroll.imported_payroll_master
CREATE INDEX idx_ipm_date_de_paie ON payroll.imported_payroll_master USING btree (date_paie);

-- Index: payroll.idx_ipm_date_paie sur payroll.imported_payroll_master
CREATE INDEX idx_ipm_date_paie ON payroll.imported_payroll_master USING btree (date_paie);

-- Index: payroll.idx_ipm_employe sur payroll.imported_payroll_master
CREATE INDEX idx_ipm_employe ON payroll.imported_payroll_master USING btree (nom_employe) WHERE (nom_employe IS NOT NULL);

-- Index: payroll.idx_ipm_matricule sur payroll.imported_payroll_master
CREATE INDEX idx_ipm_matricule ON payroll.imported_payroll_master USING btree (matricule) WHERE (matricule IS NOT NULL);

-- Index: payroll.idx_ipm_poste_budgetaire sur payroll.imported_payroll_master
CREATE INDEX idx_ipm_poste_budgetaire ON payroll.imported_payroll_master USING btree (poste_budgetaire) WHERE (poste_budgetaire IS NOT NULL);

-- Index: payroll.idx_ipm_source_file sur payroll.imported_payroll_master
CREATE INDEX idx_ipm_source_file ON payroll.imported_payroll_master USING btree (source_file);

-- Index: payroll.idx_payroll_master_code sur payroll.imported_payroll_master
CREATE INDEX idx_payroll_master_code ON payroll.imported_payroll_master USING btree (code_paie);

-- Index: payroll.idx_payroll_master_date_matricule sur payroll.imported_payroll_master
CREATE INDEX idx_payroll_master_date_matricule ON payroll.imported_payroll_master USING btree (date_paie DESC, matricule, id);

-- Index: payroll.idx_payroll_master_employe_trgm sur payroll.imported_payroll_master
CREATE INDEX idx_payroll_master_employe_trgm ON payroll.imported_payroll_master USING gin (nom_employe gin_trgm_ops);

-- Index: payroll.idx_payroll_master_matricule sur payroll.imported_payroll_master
CREATE INDEX idx_payroll_master_matricule ON payroll.imported_payroll_master USING btree (matricule);

-- Index: payroll.idx_payroll_master_source sur payroll.imported_payroll_master
CREATE INDEX idx_payroll_master_source ON payroll.imported_payroll_master USING btree (source_file, imported_at);

-- Index: payroll.idx_v_payroll_detail_date sur payroll.imported_payroll_master
CREATE INDEX idx_v_payroll_detail_date ON payroll.imported_payroll_master USING btree (date_paie) WHERE (date_paie IS NOT NULL);

-- Index: payroll.idx_v_payroll_detail_matricule sur payroll.imported_payroll_master
CREATE INDEX idx_v_payroll_detail_matricule ON payroll.imported_payroll_master USING btree (matricule) WHERE (matricule IS NOT NULL);

-- Index: payroll.imported_payroll_master_pkey sur payroll.imported_payroll_master
CREATE UNIQUE INDEX imported_payroll_master_pkey ON payroll.imported_payroll_master USING btree (id);

-- Index: payroll.idx_ing_profiles_client sur payroll.ingestion_profiles
CREATE INDEX idx_ing_profiles_client ON payroll.ingestion_profiles USING btree (client_key);

-- Index: payroll.idx_ing_profiles_mapping sur payroll.ingestion_profiles
CREATE INDEX idx_ing_profiles_mapping ON payroll.ingestion_profiles USING gin (mapping_json);

-- Index: payroll.ingestion_profiles_pkey sur payroll.ingestion_profiles
CREATE UNIQUE INDEX ingestion_profiles_pkey ON payroll.ingestion_profiles USING btree (profile_id);

-- Index: payroll.idx_kpi_snapshot_calculated sur payroll.kpi_snapshot
CREATE INDEX idx_kpi_snapshot_calculated ON payroll.kpi_snapshot USING btree (calculated_at);

-- Index: payroll.kpi_snapshot_pkey sur payroll.kpi_snapshot
CREATE UNIQUE INDEX kpi_snapshot_pkey ON payroll.kpi_snapshot USING btree (period);

-- Index: payroll.idx_pay_periods_date sur payroll.pay_periods
CREATE INDEX idx_pay_periods_date ON payroll.pay_periods USING btree (pay_date);

-- Index: payroll.idx_pay_periods_status sur payroll.pay_periods
CREATE INDEX idx_pay_periods_status ON payroll.pay_periods USING btree (status);

-- Index: payroll.idx_pay_periods_year sur payroll.pay_periods
CREATE INDEX idx_pay_periods_year ON payroll.pay_periods USING btree (pay_year);

-- Index: payroll.pay_periods_pkey sur payroll.pay_periods
CREATE UNIQUE INDEX pay_periods_pkey ON payroll.pay_periods USING btree (period_id);

-- Index: payroll.uq_pay_periods_date sur payroll.pay_periods
CREATE UNIQUE INDEX uq_pay_periods_date ON payroll.pay_periods USING btree (pay_date);

-- Index: payroll.uq_pay_periods_year_seq sur payroll.pay_periods
CREATE UNIQUE INDEX uq_pay_periods_year_seq ON payroll.pay_periods USING btree (pay_year, period_seq_in_year);

-- Index: payroll.idx_payroll_code sur payroll.payroll_transactions
CREATE INDEX idx_payroll_code ON ONLY payroll.payroll_transactions USING btree (pay_code);

-- Index: payroll.idx_payroll_date sur payroll.payroll_transactions
CREATE INDEX idx_payroll_date ON ONLY payroll.payroll_transactions USING btree (pay_date);

-- Index: payroll.idx_payroll_employee sur payroll.payroll_transactions
CREATE INDEX idx_payroll_employee ON ONLY payroll.payroll_transactions USING btree (employee_id);

-- Index: payroll.idx_payroll_employee_date sur payroll.payroll_transactions
CREATE INDEX idx_payroll_employee_date ON ONLY payroll.payroll_transactions USING btree (employee_id, pay_date);

-- Index: payroll.idx_payroll_period sur payroll.payroll_transactions
CREATE INDEX idx_payroll_period ON ONLY payroll.payroll_transactions USING btree (pay_year, pay_month);

-- Index: payroll.pk_payroll_transactions sur payroll.payroll_transactions
CREATE UNIQUE INDEX pk_payroll_transactions ON ONLY payroll.payroll_transactions USING btree (transaction_id, pay_date);

-- Index: payroll.payroll_transactions_2024_employee_id_idx sur payroll.payroll_transactions_2024
CREATE INDEX payroll_transactions_2024_employee_id_idx ON payroll.payroll_transactions_2024 USING btree (employee_id);

-- Index: payroll.payroll_transactions_2024_employee_id_pay_date_idx sur payroll.payroll_transactions_2024
CREATE INDEX payroll_transactions_2024_employee_id_pay_date_idx ON payroll.payroll_transactions_2024 USING btree (employee_id, pay_date);

-- Index: payroll.payroll_transactions_2024_pay_code_idx sur payroll.payroll_transactions_2024
CREATE INDEX payroll_transactions_2024_pay_code_idx ON payroll.payroll_transactions_2024 USING btree (pay_code);

-- Index: payroll.payroll_transactions_2024_pay_date_idx sur payroll.payroll_transactions_2024
CREATE INDEX payroll_transactions_2024_pay_date_idx ON payroll.payroll_transactions_2024 USING btree (pay_date);

-- Index: payroll.payroll_transactions_2024_pay_year_pay_month_idx sur payroll.payroll_transactions_2024
CREATE INDEX payroll_transactions_2024_pay_year_pay_month_idx ON payroll.payroll_transactions_2024 USING btree (pay_year, pay_month);

-- Index: payroll.payroll_transactions_2024_pkey sur payroll.payroll_transactions_2024
CREATE UNIQUE INDEX payroll_transactions_2024_pkey ON payroll.payroll_transactions_2024 USING btree (transaction_id, pay_date);

-- Index: payroll.payroll_transactions_2025_employee_id_idx sur payroll.payroll_transactions_2025
CREATE INDEX payroll_transactions_2025_employee_id_idx ON payroll.payroll_transactions_2025 USING btree (employee_id);

-- Index: payroll.payroll_transactions_2025_employee_id_pay_date_idx sur payroll.payroll_transactions_2025
CREATE INDEX payroll_transactions_2025_employee_id_pay_date_idx ON payroll.payroll_transactions_2025 USING btree (employee_id, pay_date);

-- Index: payroll.payroll_transactions_2025_pay_code_idx sur payroll.payroll_transactions_2025
CREATE INDEX payroll_transactions_2025_pay_code_idx ON payroll.payroll_transactions_2025 USING btree (pay_code);

-- Index: payroll.payroll_transactions_2025_pay_date_idx sur payroll.payroll_transactions_2025
CREATE INDEX payroll_transactions_2025_pay_date_idx ON payroll.payroll_transactions_2025 USING btree (pay_date);

-- Index: payroll.payroll_transactions_2025_pay_year_pay_month_idx sur payroll.payroll_transactions_2025
CREATE INDEX payroll_transactions_2025_pay_year_pay_month_idx ON payroll.payroll_transactions_2025 USING btree (pay_year, pay_month);

-- Index: payroll.payroll_transactions_2025_pkey sur payroll.payroll_transactions_2025
CREATE UNIQUE INDEX payroll_transactions_2025_pkey ON payroll.payroll_transactions_2025 USING btree (transaction_id, pay_date);

-- Index: payroll.payroll_transactions_2026_employee_id_idx sur payroll.payroll_transactions_2026
CREATE INDEX payroll_transactions_2026_employee_id_idx ON payroll.payroll_transactions_2026 USING btree (employee_id);

-- Index: payroll.payroll_transactions_2026_employee_id_pay_date_idx sur payroll.payroll_transactions_2026
CREATE INDEX payroll_transactions_2026_employee_id_pay_date_idx ON payroll.payroll_transactions_2026 USING btree (employee_id, pay_date);

-- Index: payroll.payroll_transactions_2026_pay_code_idx sur payroll.payroll_transactions_2026
CREATE INDEX payroll_transactions_2026_pay_code_idx ON payroll.payroll_transactions_2026 USING btree (pay_code);

-- Index: payroll.payroll_transactions_2026_pay_date_idx sur payroll.payroll_transactions_2026
CREATE INDEX payroll_transactions_2026_pay_date_idx ON payroll.payroll_transactions_2026 USING btree (pay_date);

-- Index: payroll.payroll_transactions_2026_pay_year_pay_month_idx sur payroll.payroll_transactions_2026
CREATE INDEX payroll_transactions_2026_pay_year_pay_month_idx ON payroll.payroll_transactions_2026 USING btree (pay_year, pay_month);

-- Index: payroll.payroll_transactions_2026_pkey sur payroll.payroll_transactions_2026
CREATE UNIQUE INDEX payroll_transactions_2026_pkey ON payroll.payroll_transactions_2026 USING btree (transaction_id, pay_date);

-- Index: payroll.idx_stg_batch sur payroll.stg_imported_payroll
CREATE INDEX idx_stg_batch ON payroll.stg_imported_payroll USING btree (import_batch_id);

-- Index: payroll.idx_stg_employee_key sur payroll.stg_imported_payroll
CREATE INDEX idx_stg_employee_key ON payroll.stg_imported_payroll USING btree (employee_key);

-- Index: payroll.idx_stg_valid sur payroll.stg_imported_payroll
CREATE INDEX idx_stg_valid ON payroll.stg_imported_payroll USING btree (is_valid);

-- Index: payroll_raw.ingestion_files_pkey sur payroll_raw.ingestion_files
CREATE UNIQUE INDEX ingestion_files_pkey ON payroll_raw.ingestion_files USING btree (file_id);

-- Index: payroll_raw.idx_raw_code_paie_trgm sur payroll_raw.raw_lines
CREATE INDEX idx_raw_code_paie_trgm ON payroll_raw.raw_lines USING gin ("code de paie" gin_trgm_ops);

-- Index: payroll_raw.idx_raw_date sur payroll_raw.raw_lines
CREATE INDEX idx_raw_date ON payroll_raw.raw_lines USING btree ("date de paie");

-- Index: payroll_raw.idx_raw_file sur payroll_raw.raw_lines
CREATE INDEX idx_raw_file ON payroll_raw.raw_lines USING btree (file_id);

-- Index: payroll_raw.idx_raw_matricule_trgm sur payroll_raw.raw_lines
CREATE INDEX idx_raw_matricule_trgm ON payroll_raw.raw_lines USING gin (matricule gin_trgm_ops);

-- Index: payroll_raw.raw_lines_pkey sur payroll_raw.raw_lines
CREATE UNIQUE INDEX raw_lines_pkey ON payroll_raw.raw_lines USING btree (raw_row_id);

-- Index: public.alembic_version_pkc sur public.alembic_version
CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num);

-- Index: ref.parameters_pkey sur ref.parameters
CREATE UNIQUE INDEX parameters_pkey ON ref.parameters USING btree (key);

-- Index: reference.budget_posts_code_key sur reference.budget_posts
CREATE UNIQUE INDEX budget_posts_code_key ON reference.budget_posts USING btree (code);

-- Index: reference.budget_posts_pkey sur reference.budget_posts
CREATE UNIQUE INDEX budget_posts_pkey ON reference.budget_posts USING btree (post_id);

-- Index: reference.idx_pay_code_mappings_pay_code sur reference.pay_code_mappings
CREATE INDEX idx_pay_code_mappings_pay_code ON reference.pay_code_mappings USING btree (pay_code);

-- Index: reference.idx_pay_code_mappings_source sur reference.pay_code_mappings
CREATE INDEX idx_pay_code_mappings_source ON reference.pay_code_mappings USING btree (source_column_name);

-- Index: reference.pay_code_mappings_pkey sur reference.pay_code_mappings
CREATE UNIQUE INDEX pay_code_mappings_pkey ON reference.pay_code_mappings USING btree (mapping_id);

-- Index: reference.idx_pay_codes_active sur reference.pay_codes
CREATE INDEX idx_pay_codes_active ON reference.pay_codes USING btree (is_active);

-- Index: reference.idx_pay_codes_type sur reference.pay_codes
CREATE INDEX idx_pay_codes_type ON reference.pay_codes USING btree (pay_code_type);

-- Index: reference.pay_codes_pay_code_key sur reference.pay_codes
CREATE UNIQUE INDEX pay_codes_pay_code_key ON reference.pay_codes USING btree (pay_code);

-- Index: reference.pay_codes_pkey sur reference.pay_codes
CREATE UNIQUE INDEX pay_codes_pkey ON reference.pay_codes USING btree (pay_code_id);

-- Index: reference.sign_policies_pkey sur reference.sign_policies
CREATE UNIQUE INDEX sign_policies_pkey ON reference.sign_policies USING btree (policy_id);

-- Index: reference.uq_sign_policies_pay_code sur reference.sign_policies
CREATE UNIQUE INDEX uq_sign_policies_pay_code ON reference.sign_policies USING btree (pay_code);

-- Index: security.audit_logs_pkey sur security.audit_logs
CREATE UNIQUE INDEX audit_logs_pkey ON ONLY security.audit_logs USING btree (log_id, created_at);

-- Index: security.idx_audit_action sur security.audit_logs
CREATE INDEX idx_audit_action ON ONLY security.audit_logs USING btree (action);

-- Index: security.idx_audit_created sur security.audit_logs
CREATE INDEX idx_audit_created ON ONLY security.audit_logs USING btree (created_at);

-- Index: security.idx_audit_table sur security.audit_logs
CREATE INDEX idx_audit_table ON ONLY security.audit_logs USING btree (table_name);

-- Index: security.idx_audit_user sur security.audit_logs
CREATE INDEX idx_audit_user ON ONLY security.audit_logs USING btree (user_id);

-- Index: security.audit_logs_2024_01_action_idx sur security.audit_logs_2024_01
CREATE INDEX audit_logs_2024_01_action_idx ON security.audit_logs_2024_01 USING btree (action);

-- Index: security.audit_logs_2024_01_created_at_idx sur security.audit_logs_2024_01
CREATE INDEX audit_logs_2024_01_created_at_idx ON security.audit_logs_2024_01 USING btree (created_at);

-- Index: security.audit_logs_2024_01_pkey sur security.audit_logs_2024_01
CREATE UNIQUE INDEX audit_logs_2024_01_pkey ON security.audit_logs_2024_01 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_01_table_name_idx sur security.audit_logs_2024_01
CREATE INDEX audit_logs_2024_01_table_name_idx ON security.audit_logs_2024_01 USING btree (table_name);

-- Index: security.audit_logs_2024_01_user_id_idx sur security.audit_logs_2024_01
CREATE INDEX audit_logs_2024_01_user_id_idx ON security.audit_logs_2024_01 USING btree (user_id);

-- Index: security.audit_logs_2024_02_action_idx sur security.audit_logs_2024_02
CREATE INDEX audit_logs_2024_02_action_idx ON security.audit_logs_2024_02 USING btree (action);

-- Index: security.audit_logs_2024_02_created_at_idx sur security.audit_logs_2024_02
CREATE INDEX audit_logs_2024_02_created_at_idx ON security.audit_logs_2024_02 USING btree (created_at);

-- Index: security.audit_logs_2024_02_pkey sur security.audit_logs_2024_02
CREATE UNIQUE INDEX audit_logs_2024_02_pkey ON security.audit_logs_2024_02 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_02_table_name_idx sur security.audit_logs_2024_02
CREATE INDEX audit_logs_2024_02_table_name_idx ON security.audit_logs_2024_02 USING btree (table_name);

-- Index: security.audit_logs_2024_02_user_id_idx sur security.audit_logs_2024_02
CREATE INDEX audit_logs_2024_02_user_id_idx ON security.audit_logs_2024_02 USING btree (user_id);

-- Index: security.audit_logs_2024_03_action_idx sur security.audit_logs_2024_03
CREATE INDEX audit_logs_2024_03_action_idx ON security.audit_logs_2024_03 USING btree (action);

-- Index: security.audit_logs_2024_03_created_at_idx sur security.audit_logs_2024_03
CREATE INDEX audit_logs_2024_03_created_at_idx ON security.audit_logs_2024_03 USING btree (created_at);

-- Index: security.audit_logs_2024_03_pkey sur security.audit_logs_2024_03
CREATE UNIQUE INDEX audit_logs_2024_03_pkey ON security.audit_logs_2024_03 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_03_table_name_idx sur security.audit_logs_2024_03
CREATE INDEX audit_logs_2024_03_table_name_idx ON security.audit_logs_2024_03 USING btree (table_name);

-- Index: security.audit_logs_2024_03_user_id_idx sur security.audit_logs_2024_03
CREATE INDEX audit_logs_2024_03_user_id_idx ON security.audit_logs_2024_03 USING btree (user_id);

-- Index: security.audit_logs_2024_04_action_idx sur security.audit_logs_2024_04
CREATE INDEX audit_logs_2024_04_action_idx ON security.audit_logs_2024_04 USING btree (action);

-- Index: security.audit_logs_2024_04_created_at_idx sur security.audit_logs_2024_04
CREATE INDEX audit_logs_2024_04_created_at_idx ON security.audit_logs_2024_04 USING btree (created_at);

-- Index: security.audit_logs_2024_04_pkey sur security.audit_logs_2024_04
CREATE UNIQUE INDEX audit_logs_2024_04_pkey ON security.audit_logs_2024_04 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_04_table_name_idx sur security.audit_logs_2024_04
CREATE INDEX audit_logs_2024_04_table_name_idx ON security.audit_logs_2024_04 USING btree (table_name);

-- Index: security.audit_logs_2024_04_user_id_idx sur security.audit_logs_2024_04
CREATE INDEX audit_logs_2024_04_user_id_idx ON security.audit_logs_2024_04 USING btree (user_id);

-- Index: security.audit_logs_2024_05_action_idx sur security.audit_logs_2024_05
CREATE INDEX audit_logs_2024_05_action_idx ON security.audit_logs_2024_05 USING btree (action);

-- Index: security.audit_logs_2024_05_created_at_idx sur security.audit_logs_2024_05
CREATE INDEX audit_logs_2024_05_created_at_idx ON security.audit_logs_2024_05 USING btree (created_at);

-- Index: security.audit_logs_2024_05_pkey sur security.audit_logs_2024_05
CREATE UNIQUE INDEX audit_logs_2024_05_pkey ON security.audit_logs_2024_05 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_05_table_name_idx sur security.audit_logs_2024_05
CREATE INDEX audit_logs_2024_05_table_name_idx ON security.audit_logs_2024_05 USING btree (table_name);

-- Index: security.audit_logs_2024_05_user_id_idx sur security.audit_logs_2024_05
CREATE INDEX audit_logs_2024_05_user_id_idx ON security.audit_logs_2024_05 USING btree (user_id);

-- Index: security.audit_logs_2024_06_action_idx sur security.audit_logs_2024_06
CREATE INDEX audit_logs_2024_06_action_idx ON security.audit_logs_2024_06 USING btree (action);

-- Index: security.audit_logs_2024_06_created_at_idx sur security.audit_logs_2024_06
CREATE INDEX audit_logs_2024_06_created_at_idx ON security.audit_logs_2024_06 USING btree (created_at);

-- Index: security.audit_logs_2024_06_pkey sur security.audit_logs_2024_06
CREATE UNIQUE INDEX audit_logs_2024_06_pkey ON security.audit_logs_2024_06 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_06_table_name_idx sur security.audit_logs_2024_06
CREATE INDEX audit_logs_2024_06_table_name_idx ON security.audit_logs_2024_06 USING btree (table_name);

-- Index: security.audit_logs_2024_06_user_id_idx sur security.audit_logs_2024_06
CREATE INDEX audit_logs_2024_06_user_id_idx ON security.audit_logs_2024_06 USING btree (user_id);

-- Index: security.audit_logs_2024_07_action_idx sur security.audit_logs_2024_07
CREATE INDEX audit_logs_2024_07_action_idx ON security.audit_logs_2024_07 USING btree (action);

-- Index: security.audit_logs_2024_07_created_at_idx sur security.audit_logs_2024_07
CREATE INDEX audit_logs_2024_07_created_at_idx ON security.audit_logs_2024_07 USING btree (created_at);

-- Index: security.audit_logs_2024_07_pkey sur security.audit_logs_2024_07
CREATE UNIQUE INDEX audit_logs_2024_07_pkey ON security.audit_logs_2024_07 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_07_table_name_idx sur security.audit_logs_2024_07
CREATE INDEX audit_logs_2024_07_table_name_idx ON security.audit_logs_2024_07 USING btree (table_name);

-- Index: security.audit_logs_2024_07_user_id_idx sur security.audit_logs_2024_07
CREATE INDEX audit_logs_2024_07_user_id_idx ON security.audit_logs_2024_07 USING btree (user_id);

-- Index: security.audit_logs_2024_08_action_idx sur security.audit_logs_2024_08
CREATE INDEX audit_logs_2024_08_action_idx ON security.audit_logs_2024_08 USING btree (action);

-- Index: security.audit_logs_2024_08_created_at_idx sur security.audit_logs_2024_08
CREATE INDEX audit_logs_2024_08_created_at_idx ON security.audit_logs_2024_08 USING btree (created_at);

-- Index: security.audit_logs_2024_08_pkey sur security.audit_logs_2024_08
CREATE UNIQUE INDEX audit_logs_2024_08_pkey ON security.audit_logs_2024_08 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_08_table_name_idx sur security.audit_logs_2024_08
CREATE INDEX audit_logs_2024_08_table_name_idx ON security.audit_logs_2024_08 USING btree (table_name);

-- Index: security.audit_logs_2024_08_user_id_idx sur security.audit_logs_2024_08
CREATE INDEX audit_logs_2024_08_user_id_idx ON security.audit_logs_2024_08 USING btree (user_id);

-- Index: security.audit_logs_2024_09_action_idx sur security.audit_logs_2024_09
CREATE INDEX audit_logs_2024_09_action_idx ON security.audit_logs_2024_09 USING btree (action);

-- Index: security.audit_logs_2024_09_created_at_idx sur security.audit_logs_2024_09
CREATE INDEX audit_logs_2024_09_created_at_idx ON security.audit_logs_2024_09 USING btree (created_at);

-- Index: security.audit_logs_2024_09_pkey sur security.audit_logs_2024_09
CREATE UNIQUE INDEX audit_logs_2024_09_pkey ON security.audit_logs_2024_09 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_09_table_name_idx sur security.audit_logs_2024_09
CREATE INDEX audit_logs_2024_09_table_name_idx ON security.audit_logs_2024_09 USING btree (table_name);

-- Index: security.audit_logs_2024_09_user_id_idx sur security.audit_logs_2024_09
CREATE INDEX audit_logs_2024_09_user_id_idx ON security.audit_logs_2024_09 USING btree (user_id);

-- Index: security.audit_logs_2024_10_action_idx sur security.audit_logs_2024_10
CREATE INDEX audit_logs_2024_10_action_idx ON security.audit_logs_2024_10 USING btree (action);

-- Index: security.audit_logs_2024_10_created_at_idx sur security.audit_logs_2024_10
CREATE INDEX audit_logs_2024_10_created_at_idx ON security.audit_logs_2024_10 USING btree (created_at);

-- Index: security.audit_logs_2024_10_pkey sur security.audit_logs_2024_10
CREATE UNIQUE INDEX audit_logs_2024_10_pkey ON security.audit_logs_2024_10 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_10_table_name_idx sur security.audit_logs_2024_10
CREATE INDEX audit_logs_2024_10_table_name_idx ON security.audit_logs_2024_10 USING btree (table_name);

-- Index: security.audit_logs_2024_10_user_id_idx sur security.audit_logs_2024_10
CREATE INDEX audit_logs_2024_10_user_id_idx ON security.audit_logs_2024_10 USING btree (user_id);

-- Index: security.audit_logs_2024_11_action_idx sur security.audit_logs_2024_11
CREATE INDEX audit_logs_2024_11_action_idx ON security.audit_logs_2024_11 USING btree (action);

-- Index: security.audit_logs_2024_11_created_at_idx sur security.audit_logs_2024_11
CREATE INDEX audit_logs_2024_11_created_at_idx ON security.audit_logs_2024_11 USING btree (created_at);

-- Index: security.audit_logs_2024_11_pkey sur security.audit_logs_2024_11
CREATE UNIQUE INDEX audit_logs_2024_11_pkey ON security.audit_logs_2024_11 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_11_table_name_idx sur security.audit_logs_2024_11
CREATE INDEX audit_logs_2024_11_table_name_idx ON security.audit_logs_2024_11 USING btree (table_name);

-- Index: security.audit_logs_2024_11_user_id_idx sur security.audit_logs_2024_11
CREATE INDEX audit_logs_2024_11_user_id_idx ON security.audit_logs_2024_11 USING btree (user_id);

-- Index: security.audit_logs_2024_12_action_idx sur security.audit_logs_2024_12
CREATE INDEX audit_logs_2024_12_action_idx ON security.audit_logs_2024_12 USING btree (action);

-- Index: security.audit_logs_2024_12_created_at_idx sur security.audit_logs_2024_12
CREATE INDEX audit_logs_2024_12_created_at_idx ON security.audit_logs_2024_12 USING btree (created_at);

-- Index: security.audit_logs_2024_12_pkey sur security.audit_logs_2024_12
CREATE UNIQUE INDEX audit_logs_2024_12_pkey ON security.audit_logs_2024_12 USING btree (log_id, created_at);

-- Index: security.audit_logs_2024_12_table_name_idx sur security.audit_logs_2024_12
CREATE INDEX audit_logs_2024_12_table_name_idx ON security.audit_logs_2024_12 USING btree (table_name);

-- Index: security.audit_logs_2024_12_user_id_idx sur security.audit_logs_2024_12
CREATE INDEX audit_logs_2024_12_user_id_idx ON security.audit_logs_2024_12 USING btree (user_id);

-- Index: security.audit_logs_2025_01_action_idx sur security.audit_logs_2025_01
CREATE INDEX audit_logs_2025_01_action_idx ON security.audit_logs_2025_01 USING btree (action);

-- Index: security.audit_logs_2025_01_created_at_idx sur security.audit_logs_2025_01
CREATE INDEX audit_logs_2025_01_created_at_idx ON security.audit_logs_2025_01 USING btree (created_at);

-- Index: security.audit_logs_2025_01_pkey sur security.audit_logs_2025_01
CREATE UNIQUE INDEX audit_logs_2025_01_pkey ON security.audit_logs_2025_01 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_01_table_name_idx sur security.audit_logs_2025_01
CREATE INDEX audit_logs_2025_01_table_name_idx ON security.audit_logs_2025_01 USING btree (table_name);

-- Index: security.audit_logs_2025_01_user_id_idx sur security.audit_logs_2025_01
CREATE INDEX audit_logs_2025_01_user_id_idx ON security.audit_logs_2025_01 USING btree (user_id);

-- Index: security.audit_logs_2025_02_action_idx sur security.audit_logs_2025_02
CREATE INDEX audit_logs_2025_02_action_idx ON security.audit_logs_2025_02 USING btree (action);

-- Index: security.audit_logs_2025_02_created_at_idx sur security.audit_logs_2025_02
CREATE INDEX audit_logs_2025_02_created_at_idx ON security.audit_logs_2025_02 USING btree (created_at);

-- Index: security.audit_logs_2025_02_pkey sur security.audit_logs_2025_02
CREATE UNIQUE INDEX audit_logs_2025_02_pkey ON security.audit_logs_2025_02 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_02_table_name_idx sur security.audit_logs_2025_02
CREATE INDEX audit_logs_2025_02_table_name_idx ON security.audit_logs_2025_02 USING btree (table_name);

-- Index: security.audit_logs_2025_02_user_id_idx sur security.audit_logs_2025_02
CREATE INDEX audit_logs_2025_02_user_id_idx ON security.audit_logs_2025_02 USING btree (user_id);

-- Index: security.audit_logs_2025_03_action_idx sur security.audit_logs_2025_03
CREATE INDEX audit_logs_2025_03_action_idx ON security.audit_logs_2025_03 USING btree (action);

-- Index: security.audit_logs_2025_03_created_at_idx sur security.audit_logs_2025_03
CREATE INDEX audit_logs_2025_03_created_at_idx ON security.audit_logs_2025_03 USING btree (created_at);

-- Index: security.audit_logs_2025_03_pkey sur security.audit_logs_2025_03
CREATE UNIQUE INDEX audit_logs_2025_03_pkey ON security.audit_logs_2025_03 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_03_table_name_idx sur security.audit_logs_2025_03
CREATE INDEX audit_logs_2025_03_table_name_idx ON security.audit_logs_2025_03 USING btree (table_name);

-- Index: security.audit_logs_2025_03_user_id_idx sur security.audit_logs_2025_03
CREATE INDEX audit_logs_2025_03_user_id_idx ON security.audit_logs_2025_03 USING btree (user_id);

-- Index: security.audit_logs_2025_04_action_idx sur security.audit_logs_2025_04
CREATE INDEX audit_logs_2025_04_action_idx ON security.audit_logs_2025_04 USING btree (action);

-- Index: security.audit_logs_2025_04_created_at_idx sur security.audit_logs_2025_04
CREATE INDEX audit_logs_2025_04_created_at_idx ON security.audit_logs_2025_04 USING btree (created_at);

-- Index: security.audit_logs_2025_04_pkey sur security.audit_logs_2025_04
CREATE UNIQUE INDEX audit_logs_2025_04_pkey ON security.audit_logs_2025_04 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_04_table_name_idx sur security.audit_logs_2025_04
CREATE INDEX audit_logs_2025_04_table_name_idx ON security.audit_logs_2025_04 USING btree (table_name);

-- Index: security.audit_logs_2025_04_user_id_idx sur security.audit_logs_2025_04
CREATE INDEX audit_logs_2025_04_user_id_idx ON security.audit_logs_2025_04 USING btree (user_id);

-- Index: security.audit_logs_2025_05_action_idx sur security.audit_logs_2025_05
CREATE INDEX audit_logs_2025_05_action_idx ON security.audit_logs_2025_05 USING btree (action);

-- Index: security.audit_logs_2025_05_created_at_idx sur security.audit_logs_2025_05
CREATE INDEX audit_logs_2025_05_created_at_idx ON security.audit_logs_2025_05 USING btree (created_at);

-- Index: security.audit_logs_2025_05_pkey sur security.audit_logs_2025_05
CREATE UNIQUE INDEX audit_logs_2025_05_pkey ON security.audit_logs_2025_05 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_05_table_name_idx sur security.audit_logs_2025_05
CREATE INDEX audit_logs_2025_05_table_name_idx ON security.audit_logs_2025_05 USING btree (table_name);

-- Index: security.audit_logs_2025_05_user_id_idx sur security.audit_logs_2025_05
CREATE INDEX audit_logs_2025_05_user_id_idx ON security.audit_logs_2025_05 USING btree (user_id);

-- Index: security.audit_logs_2025_06_action_idx sur security.audit_logs_2025_06
CREATE INDEX audit_logs_2025_06_action_idx ON security.audit_logs_2025_06 USING btree (action);

-- Index: security.audit_logs_2025_06_created_at_idx sur security.audit_logs_2025_06
CREATE INDEX audit_logs_2025_06_created_at_idx ON security.audit_logs_2025_06 USING btree (created_at);

-- Index: security.audit_logs_2025_06_pkey sur security.audit_logs_2025_06
CREATE UNIQUE INDEX audit_logs_2025_06_pkey ON security.audit_logs_2025_06 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_06_table_name_idx sur security.audit_logs_2025_06
CREATE INDEX audit_logs_2025_06_table_name_idx ON security.audit_logs_2025_06 USING btree (table_name);

-- Index: security.audit_logs_2025_06_user_id_idx sur security.audit_logs_2025_06
CREATE INDEX audit_logs_2025_06_user_id_idx ON security.audit_logs_2025_06 USING btree (user_id);

-- Index: security.audit_logs_2025_07_action_idx sur security.audit_logs_2025_07
CREATE INDEX audit_logs_2025_07_action_idx ON security.audit_logs_2025_07 USING btree (action);

-- Index: security.audit_logs_2025_07_created_at_idx sur security.audit_logs_2025_07
CREATE INDEX audit_logs_2025_07_created_at_idx ON security.audit_logs_2025_07 USING btree (created_at);

-- Index: security.audit_logs_2025_07_pkey sur security.audit_logs_2025_07
CREATE UNIQUE INDEX audit_logs_2025_07_pkey ON security.audit_logs_2025_07 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_07_table_name_idx sur security.audit_logs_2025_07
CREATE INDEX audit_logs_2025_07_table_name_idx ON security.audit_logs_2025_07 USING btree (table_name);

-- Index: security.audit_logs_2025_07_user_id_idx sur security.audit_logs_2025_07
CREATE INDEX audit_logs_2025_07_user_id_idx ON security.audit_logs_2025_07 USING btree (user_id);

-- Index: security.audit_logs_2025_08_action_idx sur security.audit_logs_2025_08
CREATE INDEX audit_logs_2025_08_action_idx ON security.audit_logs_2025_08 USING btree (action);

-- Index: security.audit_logs_2025_08_created_at_idx sur security.audit_logs_2025_08
CREATE INDEX audit_logs_2025_08_created_at_idx ON security.audit_logs_2025_08 USING btree (created_at);

-- Index: security.audit_logs_2025_08_pkey sur security.audit_logs_2025_08
CREATE UNIQUE INDEX audit_logs_2025_08_pkey ON security.audit_logs_2025_08 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_08_table_name_idx sur security.audit_logs_2025_08
CREATE INDEX audit_logs_2025_08_table_name_idx ON security.audit_logs_2025_08 USING btree (table_name);

-- Index: security.audit_logs_2025_08_user_id_idx sur security.audit_logs_2025_08
CREATE INDEX audit_logs_2025_08_user_id_idx ON security.audit_logs_2025_08 USING btree (user_id);

-- Index: security.audit_logs_2025_09_action_idx sur security.audit_logs_2025_09
CREATE INDEX audit_logs_2025_09_action_idx ON security.audit_logs_2025_09 USING btree (action);

-- Index: security.audit_logs_2025_09_created_at_idx sur security.audit_logs_2025_09
CREATE INDEX audit_logs_2025_09_created_at_idx ON security.audit_logs_2025_09 USING btree (created_at);

-- Index: security.audit_logs_2025_09_pkey sur security.audit_logs_2025_09
CREATE UNIQUE INDEX audit_logs_2025_09_pkey ON security.audit_logs_2025_09 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_09_table_name_idx sur security.audit_logs_2025_09
CREATE INDEX audit_logs_2025_09_table_name_idx ON security.audit_logs_2025_09 USING btree (table_name);

-- Index: security.audit_logs_2025_09_user_id_idx sur security.audit_logs_2025_09
CREATE INDEX audit_logs_2025_09_user_id_idx ON security.audit_logs_2025_09 USING btree (user_id);

-- Index: security.audit_logs_2025_10_action_idx sur security.audit_logs_2025_10
CREATE INDEX audit_logs_2025_10_action_idx ON security.audit_logs_2025_10 USING btree (action);

-- Index: security.audit_logs_2025_10_created_at_idx sur security.audit_logs_2025_10
CREATE INDEX audit_logs_2025_10_created_at_idx ON security.audit_logs_2025_10 USING btree (created_at);

-- Index: security.audit_logs_2025_10_pkey sur security.audit_logs_2025_10
CREATE UNIQUE INDEX audit_logs_2025_10_pkey ON security.audit_logs_2025_10 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_10_table_name_idx sur security.audit_logs_2025_10
CREATE INDEX audit_logs_2025_10_table_name_idx ON security.audit_logs_2025_10 USING btree (table_name);

-- Index: security.audit_logs_2025_10_user_id_idx sur security.audit_logs_2025_10
CREATE INDEX audit_logs_2025_10_user_id_idx ON security.audit_logs_2025_10 USING btree (user_id);

-- Index: security.audit_logs_2025_11_action_idx sur security.audit_logs_2025_11
CREATE INDEX audit_logs_2025_11_action_idx ON security.audit_logs_2025_11 USING btree (action);

-- Index: security.audit_logs_2025_11_created_at_idx sur security.audit_logs_2025_11
CREATE INDEX audit_logs_2025_11_created_at_idx ON security.audit_logs_2025_11 USING btree (created_at);

-- Index: security.audit_logs_2025_11_pkey sur security.audit_logs_2025_11
CREATE UNIQUE INDEX audit_logs_2025_11_pkey ON security.audit_logs_2025_11 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_11_table_name_idx sur security.audit_logs_2025_11
CREATE INDEX audit_logs_2025_11_table_name_idx ON security.audit_logs_2025_11 USING btree (table_name);

-- Index: security.audit_logs_2025_11_user_id_idx sur security.audit_logs_2025_11
CREATE INDEX audit_logs_2025_11_user_id_idx ON security.audit_logs_2025_11 USING btree (user_id);

-- Index: security.audit_logs_2025_12_action_idx sur security.audit_logs_2025_12
CREATE INDEX audit_logs_2025_12_action_idx ON security.audit_logs_2025_12 USING btree (action);

-- Index: security.audit_logs_2025_12_created_at_idx sur security.audit_logs_2025_12
CREATE INDEX audit_logs_2025_12_created_at_idx ON security.audit_logs_2025_12 USING btree (created_at);

-- Index: security.audit_logs_2025_12_pkey sur security.audit_logs_2025_12
CREATE UNIQUE INDEX audit_logs_2025_12_pkey ON security.audit_logs_2025_12 USING btree (log_id, created_at);

-- Index: security.audit_logs_2025_12_table_name_idx sur security.audit_logs_2025_12
CREATE INDEX audit_logs_2025_12_table_name_idx ON security.audit_logs_2025_12 USING btree (table_name);

-- Index: security.audit_logs_2025_12_user_id_idx sur security.audit_logs_2025_12
CREATE INDEX audit_logs_2025_12_user_id_idx ON security.audit_logs_2025_12 USING btree (user_id);

-- Index: security.audit_logs_2026_01_action_idx sur security.audit_logs_2026_01
CREATE INDEX audit_logs_2026_01_action_idx ON security.audit_logs_2026_01 USING btree (action);

-- Index: security.audit_logs_2026_01_created_at_idx sur security.audit_logs_2026_01
CREATE INDEX audit_logs_2026_01_created_at_idx ON security.audit_logs_2026_01 USING btree (created_at);

-- Index: security.audit_logs_2026_01_pkey sur security.audit_logs_2026_01
CREATE UNIQUE INDEX audit_logs_2026_01_pkey ON security.audit_logs_2026_01 USING btree (log_id, created_at);

-- Index: security.audit_logs_2026_01_table_name_idx sur security.audit_logs_2026_01
CREATE INDEX audit_logs_2026_01_table_name_idx ON security.audit_logs_2026_01 USING btree (table_name);

-- Index: security.audit_logs_2026_01_user_id_idx sur security.audit_logs_2026_01
CREATE INDEX audit_logs_2026_01_user_id_idx ON security.audit_logs_2026_01 USING btree (user_id);

-- Index: security.audit_logs_2026_02_action_idx sur security.audit_logs_2026_02
CREATE INDEX audit_logs_2026_02_action_idx ON security.audit_logs_2026_02 USING btree (action);

-- Index: security.audit_logs_2026_02_created_at_idx sur security.audit_logs_2026_02
CREATE INDEX audit_logs_2026_02_created_at_idx ON security.audit_logs_2026_02 USING btree (created_at);

-- Index: security.audit_logs_2026_02_pkey sur security.audit_logs_2026_02
CREATE UNIQUE INDEX audit_logs_2026_02_pkey ON security.audit_logs_2026_02 USING btree (log_id, created_at);

-- Index: security.audit_logs_2026_02_table_name_idx sur security.audit_logs_2026_02
CREATE INDEX audit_logs_2026_02_table_name_idx ON security.audit_logs_2026_02 USING btree (table_name);

-- Index: security.audit_logs_2026_02_user_id_idx sur security.audit_logs_2026_02
CREATE INDEX audit_logs_2026_02_user_id_idx ON security.audit_logs_2026_02 USING btree (user_id);

-- Index: security.audit_logs_2026_03_action_idx sur security.audit_logs_2026_03
CREATE INDEX audit_logs_2026_03_action_idx ON security.audit_logs_2026_03 USING btree (action);

-- Index: security.audit_logs_2026_03_created_at_idx sur security.audit_logs_2026_03
CREATE INDEX audit_logs_2026_03_created_at_idx ON security.audit_logs_2026_03 USING btree (created_at);

-- Index: security.audit_logs_2026_03_pkey sur security.audit_logs_2026_03
CREATE UNIQUE INDEX audit_logs_2026_03_pkey ON security.audit_logs_2026_03 USING btree (log_id, created_at);

-- Index: security.audit_logs_2026_03_table_name_idx sur security.audit_logs_2026_03
CREATE INDEX audit_logs_2026_03_table_name_idx ON security.audit_logs_2026_03 USING btree (table_name);

-- Index: security.audit_logs_2026_03_user_id_idx sur security.audit_logs_2026_03
CREATE INDEX audit_logs_2026_03_user_id_idx ON security.audit_logs_2026_03 USING btree (user_id);

-- Index: security.audit_logs_2026_04_action_idx sur security.audit_logs_2026_04
CREATE INDEX audit_logs_2026_04_action_idx ON security.audit_logs_2026_04 USING btree (action);

-- Index: security.audit_logs_2026_04_created_at_idx sur security.audit_logs_2026_04
CREATE INDEX audit_logs_2026_04_created_at_idx ON security.audit_logs_2026_04 USING btree (created_at);

-- Index: security.audit_logs_2026_04_pkey sur security.audit_logs_2026_04
CREATE UNIQUE INDEX audit_logs_2026_04_pkey ON security.audit_logs_2026_04 USING btree (log_id, created_at);

-- Index: security.audit_logs_2026_04_table_name_idx sur security.audit_logs_2026_04
CREATE INDEX audit_logs_2026_04_table_name_idx ON security.audit_logs_2026_04 USING btree (table_name);

-- Index: security.audit_logs_2026_04_user_id_idx sur security.audit_logs_2026_04
CREATE INDEX audit_logs_2026_04_user_id_idx ON security.audit_logs_2026_04 USING btree (user_id);

-- Index: security.audit_logs_2026_05_action_idx sur security.audit_logs_2026_05
CREATE INDEX audit_logs_2026_05_action_idx ON security.audit_logs_2026_05 USING btree (action);

-- Index: security.audit_logs_2026_05_created_at_idx sur security.audit_logs_2026_05
CREATE INDEX audit_logs_2026_05_created_at_idx ON security.audit_logs_2026_05 USING btree (created_at);

-- Index: security.audit_logs_2026_05_pkey sur security.audit_logs_2026_05
CREATE UNIQUE INDEX audit_logs_2026_05_pkey ON security.audit_logs_2026_05 USING btree (log_id, created_at);

-- Index: security.audit_logs_2026_05_table_name_idx sur security.audit_logs_2026_05
CREATE INDEX audit_logs_2026_05_table_name_idx ON security.audit_logs_2026_05 USING btree (table_name);

-- Index: security.audit_logs_2026_05_user_id_idx sur security.audit_logs_2026_05
CREATE INDEX audit_logs_2026_05_user_id_idx ON security.audit_logs_2026_05 USING btree (user_id);

-- Index: security.audit_logs_2026_06_action_idx sur security.audit_logs_2026_06
CREATE INDEX audit_logs_2026_06_action_idx ON security.audit_logs_2026_06 USING btree (action);

-- Index: security.audit_logs_2026_06_created_at_idx sur security.audit_logs_2026_06
CREATE INDEX audit_logs_2026_06_created_at_idx ON security.audit_logs_2026_06 USING btree (created_at);

-- Index: security.audit_logs_2026_06_pkey sur security.audit_logs_2026_06
CREATE UNIQUE INDEX audit_logs_2026_06_pkey ON security.audit_logs_2026_06 USING btree (log_id, created_at);

-- Index: security.audit_logs_2026_06_table_name_idx sur security.audit_logs_2026_06
CREATE INDEX audit_logs_2026_06_table_name_idx ON security.audit_logs_2026_06 USING btree (table_name);

-- Index: security.audit_logs_2026_06_user_id_idx sur security.audit_logs_2026_06
CREATE INDEX audit_logs_2026_06_user_id_idx ON security.audit_logs_2026_06 USING btree (user_id);

-- Index: security.audit_logs_future_action_idx sur security.audit_logs_future
CREATE INDEX audit_logs_future_action_idx ON security.audit_logs_future USING btree (action);

-- Index: security.audit_logs_future_created_at_idx sur security.audit_logs_future
CREATE INDEX audit_logs_future_created_at_idx ON security.audit_logs_future USING btree (created_at);

-- Index: security.audit_logs_future_pkey sur security.audit_logs_future
CREATE UNIQUE INDEX audit_logs_future_pkey ON security.audit_logs_future USING btree (log_id, created_at);

-- Index: security.audit_logs_future_table_name_idx sur security.audit_logs_future
CREATE INDEX audit_logs_future_table_name_idx ON security.audit_logs_future USING btree (table_name);

-- Index: security.audit_logs_future_user_id_idx sur security.audit_logs_future
CREATE INDEX audit_logs_future_user_id_idx ON security.audit_logs_future USING btree (user_id);

-- Index: security.idx_roles_permissions_role sur security.roles_permissions
CREATE INDEX idx_roles_permissions_role ON security.roles_permissions USING btree (role);

-- Index: security.idx_roles_permissions_table sur security.roles_permissions
CREATE INDEX idx_roles_permissions_table ON security.roles_permissions USING btree (table_name);

-- Index: security.roles_permissions_pkey sur security.roles_permissions
CREATE UNIQUE INDEX roles_permissions_pkey ON security.roles_permissions USING btree (role, table_name);

-- Index: security.idx_users_active sur security.users
CREATE INDEX idx_users_active ON security.users USING btree (active);

-- Index: security.idx_users_role sur security.users
CREATE INDEX idx_users_role ON security.users USING btree (role);

-- Index: security.uq_users_username sur security.users
CREATE UNIQUE INDEX uq_users_username ON security.users USING btree (username);

-- Index: security.users_pkey sur security.users
CREATE UNIQUE INDEX users_pkey ON security.users USING btree (user_id);

-- Index: superset.idx_v_emp_periode_empid sur superset.v_employes_par_periode
CREATE INDEX idx_v_emp_periode_empid ON superset.v_employes_par_periode USING btree (employee_id);

-- Index: superset.idx_v_emp_periode_matricule sur superset.v_employes_par_periode
CREATE INDEX idx_v_emp_periode_matricule ON superset.v_employes_par_periode USING btree (matricule);

-- Index: superset.idx_v_emp_periode_periode sur superset.v_employes_par_periode
CREATE INDEX idx_v_emp_periode_periode ON superset.v_employes_par_periode USING btree (periode);

-- Index: superset.idx_v_kpi_date sur superset.v_kpi_par_periode
CREATE INDEX idx_v_kpi_date ON superset.v_kpi_par_periode USING btree (pay_date);

-- Index: superset.idx_v_kpi_periode sur superset.v_kpi_par_periode
CREATE UNIQUE INDEX idx_v_kpi_periode ON superset.v_kpi_par_periode USING btree (periode, pay_date);

-- Index: superset.idx_v_ref_emp_id sur superset.v_referentiel_employes
CREATE UNIQUE INDEX idx_v_ref_emp_id ON superset.v_referentiel_employes USING btree (employee_id);

-- Index: superset.idx_v_ref_emp_matricule sur superset.v_referentiel_employes
CREATE INDEX idx_v_ref_emp_matricule ON superset.v_referentiel_employes USING btree (matricule);

-- Index: superset.idx_v_ref_emp_nom sur superset.v_referentiel_employes
CREATE INDEX idx_v_ref_emp_nom ON superset.v_referentiel_employes USING btree (nom, prenom);

-- Index: superset.idx_v_tend_periode sur superset.v_tendance_mensuelle
CREATE UNIQUE INDEX idx_v_tend_periode ON superset.v_tendance_mensuelle USING btree (periode);
