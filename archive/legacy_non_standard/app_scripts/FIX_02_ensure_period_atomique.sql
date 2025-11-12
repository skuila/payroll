-- ========================================
-- CORRECTIF 2: Fonction ensure_period() Atomique
-- ========================================
-- But: Empêcher deux imports de fabriquer le même period_seq_in_year
-- Version: 2.0.1 (Production Hardened)

\echo '🔧 CORRECTIF 2: Numérotation périodes sans doublon...'

-- Transaction avec timeouts et search_path
BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL client_min_messages = warning;
SET LOCAL search_path = payroll, public;

-- Une date de paie = une seule période
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_pay_periods_date'
    ) THEN
        ALTER TABLE payroll.pay_periods ADD CONSTRAINT uq_pay_periods_date UNIQUE (pay_date);
        RAISE NOTICE 'Contrainte uq_pay_periods_date ajoutée';
    ELSE
        RAISE NOTICE 'Contrainte uq_pay_periods_date existe déjà';
    END IF;
END $$;

\echo '✅ Contrainte UNIQUE sur pay_date vérifiée'

-- Fonction atomique : crée/récupère la période avec verrou "léger" par année
CREATE OR REPLACE FUNCTION payroll.ensure_period(p_date date)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_id  uuid;
  v_y   int := EXTRACT(YEAR FROM p_date);
  v_seq int;
BEGIN
  -- Réduire les messages de log dans la fonction
  SET LOCAL client_min_messages = warning;
  
  SELECT period_id INTO v_id
  FROM payroll.pay_periods
  WHERE pay_date = p_date
  LIMIT 1;
  IF v_id IS NOT NULL THEN RETURN v_id; END IF;

  -- verrou conseil sur l'année (évite la course)
  PERFORM pg_advisory_xact_lock(hashtext('pay_periods_' || v_y::text));

  -- re-vérification après verrou
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
$$;

COMMENT ON FUNCTION payroll.ensure_period(date) IS 'Crée ou récupère une période de paie de manière atomique (thread-safe)';

\echo '✅ Fonction payroll.ensure_period() créée'
\echo ''
\echo 'Utilisation Python:'
\echo '  row = repo.run_query("SELECT payroll.ensure_period(%(d)s) AS period_id", {"d": pay_date.date()}, fetch_one=True)'
\echo '  period_id = row[0]'

-- Commit transaction
COMMIT;

\echo ''
\echo '✅ Transaction COMMIT réussie - Fonction installée de manière atomique'
\echo 'Pour vérification, exécuter: psql -U postgres -d payroll_db -f scripts/SELF_CHECK.sql'

