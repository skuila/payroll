#!/usr/bin/env python3
"""
Script simplifié pour créer les vues KPI dans le schéma public
"""

import sys
import os
from pathlib import Path
import psycopg
from dotenv import load_dotenv

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Propagate PAYROLL_DB_PASSWORD into PGPASSWORD for libpq/psycopg compatibility
try:
    if os.getenv("PAYROLL_DB_PASSWORD") and not os.getenv("PGPASSWORD"):
        os.environ["PGPASSWORD"] = os.getenv("PAYROLL_DB_PASSWORD")
except Exception:
    pass

# Configuration de connexion — éviter les secrets en dur
DSN = (
    os.getenv("DATABASE_URL")
    or os.getenv("PAYROLL_DSN")
    or (
        f"postgresql://{os.getenv('PAYROLL_DB_USER','payroll_app')}:"
        f"{os.getenv('PAYROLL_DB_PASSWORD','__SET_AT_DEPLOY__')}@"
        f"{os.getenv('PAYROLL_DB_HOST','localhost')}:{os.getenv('PAYROLL_DB_PORT','5432')}/"
        f"{os.getenv('PAYROLL_DB_NAME','payroll_db')}"
    )
)

if "__SET_AT_DEPLOY__" in DSN:
    print(
        "WARNING: PAYROLL_DB_PASSWORD non configuré dans l'environnement — vérifiez .env ou variables CI"
    )


def create_simple_kpi_views():
    """Crée les vues KPI simplifiées dans le schéma public"""
    try:
        print("🔧 CRÉATION DES VUES KPI SIMPLIFIÉES")
        print("=" * 50)

        with psycopg.connect(DSN) as conn:
            with conn.cursor() as cur:
                # Vue principale KPI
                print("📊 Création de la vue principale v_kpi_periode...")

                create_view_sql = """
                CREATE OR REPLACE VIEW v_kpi_periode AS
                SELECT 
                    TO_CHAR(pay_date, 'YYYY-MM') as periode,
                    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
                    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
                    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
                    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
                    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
                    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
                    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements
                FROM payroll.payroll_transactions
                GROUP BY TO_CHAR(pay_date, 'YYYY-MM'), TO_CHAR(pay_date, 'YYYY-MM-DD')
                ORDER BY periode, date_paie
                """

                cur.execute(create_view_sql)
                print("   ✅ Vue v_kpi_periode créée")

                # Vue par code de paie
                print("📊 Création de la vue v_kpi_par_code_paie...")

                create_code_view_sql = """
                CREATE OR REPLACE VIEW v_kpi_par_code_paie AS
                SELECT 
                    TO_CHAR(pay_date, 'YYYY-MM') as periode,
                    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
                    pay_code,
                    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
                    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
                    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
                    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
                    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
                    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements
                FROM payroll.payroll_transactions
                GROUP BY TO_CHAR(pay_date, 'YYYY-MM'), TO_CHAR(pay_date, 'YYYY-MM-DD'), pay_code
                ORDER BY periode, pay_code
                """

                cur.execute(create_code_view_sql)
                print("   ✅ Vue v_kpi_par_code_paie créée")

                # Vue par employé
                print("📊 Création de la vue v_kpi_par_employe_periode...")

                create_employee_view_sql = """
                CREATE OR REPLACE VIEW v_kpi_par_employe_periode AS
                SELECT 
                    TO_CHAR(pay_date, 'YYYY-MM') as periode,
                    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
                    employee_id,
                    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
                    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
                    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
                    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
                    1 as nb_employes,
                    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
                    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements
                FROM payroll.payroll_transactions
                GROUP BY TO_CHAR(pay_date, 'YYYY-MM'), TO_CHAR(pay_date, 'YYYY-MM-DD'), employee_id
                ORDER BY periode, employee_id
                """

                cur.execute(create_employee_view_sql)
                print("   ✅ Vue v_kpi_par_employe_periode créée")

                conn.commit()

                # Vérifier que les vues ont été créées
                cur.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'v_kpi_%'
                    ORDER BY table_name
                """
                )

                views = [row[0] for row in cur.fetchall()]
                print(f"\n📊 Vues KPI créées: {len(views)}")
                for view in views:
                    print(f"   ✅ {view}")

                # Test des données
                cur.execute("SELECT COUNT(*) FROM v_kpi_periode")
                count = cur.fetchone()[0]
                print(f"\n📈 Données dans v_kpi_periode: {count} lignes")

                if count > 0:
                    cur.execute(
                        "SELECT periode, gains_brut, nb_employes FROM v_kpi_periode LIMIT 3"
                    )
                    sample = cur.fetchall()
                    print(f"📋 Échantillon:")
                    for row in sample:
                        print(f"   {row[0]}: {row[1]:,.2f}€, {row[2]} employés")

                return True

    except Exception as e:
        print(f"❌ Erreur lors de la création des vues: {e}")
        return False


def main():
    """Fonction principale"""
    success = create_simple_kpi_views()

    if success:
        print("\n🎉 VUES KPI CRÉÉES AVEC SUCCÈS")
        print("✅ Vues créées dans le schéma public")
        print("✅ Contrat de colonnes harmonisé appliqué")
        print("✅ Données disponibles pour l'API")
        return 0
    else:
        print("\n❌ ÉCHEC DE LA CRÉATION DES VUES")
        print("🔧 Vérifiez la connexion à la base de données")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
