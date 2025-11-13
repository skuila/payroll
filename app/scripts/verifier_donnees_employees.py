"""
Verifie les donnees employes dans la base de donnees
"""

import sys
import os

# Ajouter le chemin pour importer les providers
sys.path.insert(0, os.path.dirname(__file__))

from app.providers.postgres_provider import PostgresProvider


def format_currency(amount):
    """Formate un montant en dollars canadiens"""
    return f"{amount:,.2f} $"


def main():
    print("=" * 80)
    print("VERIFICATION DES DONNEES EMPLOYES")
    print("=" * 80)

    try:
        # Utiliser le provider PostgreSQL existant avec les bons credentials
        # (mêmes que ceux utilisés par l'application par défaut)
        from config.config_manager import get_dsn

        dsn = get_dsn()
        provider = PostgresProvider(dsn=dsn)

        if not provider.repo:
            print("\nImpossible de se connecter a la base de donnees")
            return

        # 1. Periodes disponibles
        print("\nPERIODES DE PAIE DISPONIBLES:")
        print("-" * 80)

        sql_periods = """
            SELECT DISTINCT pay_date, COUNT(DISTINCT employee_id) as nb_employes
            FROM payroll.payroll_transactions
            GROUP BY pay_date
            ORDER BY pay_date DESC
            LIMIT 10
        """

        with provider.repo.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_periods)
                periods = cur.fetchall()

        if not periods:
            print("\nAUCUNE PERIODE TROUVEE !")
            print("\nVous devez importer des donnees avant de tester la page employes.")
            print("Utilisez la page Import dans l'application.")
            return

        print(f"\n{'Date de paie':<15} {'Nb employes':>12}")
        print("-" * 30)
        for pay_date, nb in periods:
            print(f"{str(pay_date):<15} {nb:>12}")

        # Utiliser la periode la plus recente
        latest_date = periods[0][0]

        # 2. Exemple d'employes pour cette periode
        print(f"\n\nEXEMPLE D'EMPLOYES POUR LE {latest_date}:")
        print("=" * 80)

        sql_employees = """
            WITH agg AS (
                SELECT 
                    e.employee_id,
                    COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm, '')) AS nom,
                    COALESCE(e.matricule_norm, '') AS matricule,
                    COALESCE(SUM(t.amount_cents) / 100.0, 0.0) AS salaire_net
                FROM payroll.payroll_transactions t
                JOIN core.employees e ON e.employee_id = t.employee_id
                WHERE t.pay_date = %s
                GROUP BY e.employee_id, e.nom_complet, e.nom_norm, e.prenom_norm, e.matricule_norm
            ),
            stg AS (
                SELECT
                    COALESCE(matricule::text, '') AS matricule,
                    MAX(categorie_emploi) AS categorie_emploi,
                    MAX(titre_emploi) AS titre_emploi
                FROM paie.stg_paie_transactions
                WHERE date_paie = %s AND is_valid = TRUE
                GROUP BY COALESCE(matricule::text, '')
            )
            SELECT
                agg.nom,
                agg.matricule,
                COALESCE(stg.categorie_emploi, '') AS categorie_emploi,
                COALESCE(stg.titre_emploi, '') AS titre_emploi,
                agg.salaire_net AS total_a_payer
            FROM agg
            LEFT JOIN stg ON stg.matricule = agg.matricule
            ORDER BY agg.nom
            LIMIT 10
        """

        with provider.repo.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_employees, (latest_date, latest_date))
                employees = cur.fetchall()

        if not employees:
            print("\nAUCUN EMPLOYE TROUVE POUR CETTE PERIODE !")
            return

        print(
            f"\n{'Nom':<35} {'Matricule':<12} {'Categorie':<20} {'Titre':<25} {'Salaire net':>15}"
        )
        print("-" * 120)

        total = 0
        for nom, matricule, categorie, titre, salaire in employees:
            print(
                f"{nom:<35} {matricule:<12} {categorie:<20} {titre:<25} {format_currency(salaire):>15}"
            )
            total += salaire

        print("-" * 120)
        print(f"{'TOTAL (10 premiers):':<92} {format_currency(total):>15}")

        # 3. Statistiques globales
        sql_stats = """
            SELECT 
                COUNT(DISTINCT employee_id) as nb_employes,
                SUM(amount_cents) / 100.0 as total_net
            FROM payroll.payroll_transactions
            WHERE pay_date = %s
        """

        with provider.repo.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_stats, (latest_date,))
                nb_total, montant_total = cur.fetchone()

        print(f"\n\nSTATISTIQUES GLOBALES POUR LE {latest_date}:")
        print("-" * 80)
        print(f"Nombre total d'employes : {nb_total}")
        print(f"Masse salariale nette    : {format_currency(montant_total)}")

        print("\n" + "=" * 80)
        print("LA PAGE EMPLOYES DEVRAIT AFFICHER CES DONNEES")
        print("=" * 80)
        print("\nLancez maintenant : python test_employees_correct.py")
        print("Ou directement     : python payroll_app_qt_Version4.py")

        provider.close()

    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
