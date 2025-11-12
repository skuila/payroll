#!/usr/bin/env python3
"""
Script pour ajouter des colonnes spécifiques à la base payroll
Exemples concrets d'ajouts de champs métier
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.providers.postgres_provider import PostgresProvider


def add_business_columns():
    """Ajouter des colonnes métier utiles"""

    p = PostgresProvider()

    print("=== AJOUT DE COLONNES MÉTIER ===\n")

    # Colonnes à ajouter à core.employees
    employee_columns = [
        ("department", "VARCHAR(100)", "NULL", "Département de l'employé"),
        ("job_title", "VARCHAR(150)", "NULL", "Poste occupé"),
        ("hire_date", "DATE", "NULL", "Date d'embauche"),
        (
            "manager_id",
            "INTEGER",
            "NULL",
            "ID du manager (clé étrangère vers employee_id)",
        ),
        ("salary_grade", "VARCHAR(20)", "NULL", "Échelon salarial"),
        ("contract_type", "VARCHAR(50)", "NULL", "Type de contrat (CDI, CDD, etc.)"),
        ("work_location", "VARCHAR(100)", "NULL", "Lieu de travail"),
        ("phone_number", "VARCHAR(20)", "NULL", "Numéro de téléphone"),
        ("email", "VARCHAR(150)", "NULL", "Adresse email"),
        ("birth_date", "DATE", "NULL", "Date de naissance"),
        ("nationality", "VARCHAR(50)", "NULL", "Nationalité"),
        ("emergency_contact", "VARCHAR(100)", "NULL", "Contact d'urgence"),
        ("emergency_phone", "VARCHAR(20)", "NULL", "Téléphone d'urgence"),
        ("iban", "VARCHAR(34)", "NULL", "IBAN pour virement"),
        ("social_security_number", "VARCHAR(15)", "NULL", "Numéro de sécurité sociale"),
        ("tax_id", "VARCHAR(20)", "NULL", "Numéro fiscal"),
        ("union_member", "BOOLEAN", "DEFAULT FALSE", "Membre d'un syndicat"),
        ("disability_status", "VARCHAR(50)", "NULL", "Statut handicap"),
        ("languages", "TEXT[]", "NULL", "Langues parlées (tableau)"),
        ("certifications", "TEXT[]", "NULL", "Certifications obtenues (tableau)"),
        ("last_performance_review", "DATE", "NULL", "Dernière évaluation"),
        ("next_performance_review", "DATE", "NULL", "Prochaine évaluation"),
        ("probation_end_date", "DATE", "NULL", "Fin de période d'essai"),
        ("notice_period_days", "INTEGER", "NULL", "Période de préavis en jours"),
        ("annual_leave_days", "INTEGER", "DEFAULT 25", "Jours de congé annuel"),
        ("sick_leave_days", "INTEGER", "DEFAULT 0", "Jours de congé maladie utilisés"),
        (
            "overtime_hours",
            "NUMERIC(8,2)",
            "DEFAULT 0",
            "Heures supplémentaires accumulées",
        ),
        ("training_budget", "NUMERIC(10,2)", "DEFAULT 0", "Budget formation annuel"),
        ("company_car", "BOOLEAN", "DEFAULT FALSE", "Véhicule de société"),
        ("parking_space", "VARCHAR(10)", "NULL", "Place de parking"),
        ("office_number", "VARCHAR(20)", "NULL", "Numéro de bureau"),
        ("extension_number", "VARCHAR(10)", "NULL", "Numéro de poste téléphonique"),
        ("slack_id", "VARCHAR(20)", "NULL", "ID Slack"),
        ("github_username", "VARCHAR(50)", "NULL", "Nom d'utilisateur GitHub"),
        ("preferred_name", "VARCHAR(100)", "NULL", "Nom préféré pour l'affichage"),
        ("pronouns", "VARCHAR(20)", "NULL", "Pronoms préférés"),
        ("timezone", "VARCHAR(50)", "DEFAULT 'America/Toronto'", "Fuseau horaire"),
        ("remote_work_allowed", "BOOLEAN", "DEFAULT FALSE", "Télétravail autorisé"),
        ("remote_work_days", "INTEGER[]", "NULL", "Jours de télétravail (tableau)"),
        ("equipment_provided", "TEXT[]", "NULL", "Équipement fourni (tableau)"),
        ("software_access", "TEXT[]", "NULL", "Accès logiciels (tableau)"),
        ("notes", "TEXT", "NULL", "Notes diverses sur l'employé"),
    ]

    print("Colonnes à ajouter à core.employees:")
    for col_name, col_type, constraints, description in employee_columns:
        sql = f"ALTER TABLE core.employees ADD COLUMN IF NOT EXISTS {col_name} {col_type} {constraints};"
        print(f"  - {col_name}: {description}")
        print(f"    SQL: {sql}")

        # Exécution (commentée pour sécurité)
        # try:
        #     p.repo.run_query(sql)
        #     print("    ✅ Ajouté")
        # except Exception as e:
        #     print(f"    ❌ Erreur: {e}")

    print(
        f"\n📊 Total: {len(employee_columns)} colonnes proposées pour core.employees\n"
    )

    # Colonnes à ajouter à payroll.payroll_transactions
    transaction_columns = [
        ("cost_center", "VARCHAR(50)", "NULL", "Centre de coût"),
        ("project_code", "VARCHAR(50)", "NULL", "Code projet"),
        (
            "work_location",
            "VARCHAR(100)",
            "NULL",
            "Lieu de travail pour cette transaction",
        ),
        (
            "overtime_multiplier",
            "NUMERIC(3,2)",
            "DEFAULT 1.0",
            "Multiplicateur heures sup (1.0=normal, 1.5=sup 50%, etc.)",
        ),
        ("taxable_amount", "BIGINT", "NULL", "Montant imposable en cents"),
        ("tax_deducted", "BIGINT", "DEFAULT 0", "Impôt déduit en cents"),
        (
            "social_contributions",
            "BIGINT",
            "DEFAULT 0",
            "Cotisations sociales en cents",
        ),
        ("employer_cost", "BIGINT", "NULL", "Coût total employeur en cents"),
        ("currency", "VARCHAR(3)", "DEFAULT 'CAD'", "Devise (CAD, USD, EUR)"),
        ("exchange_rate", "NUMERIC(10,6)", "DEFAULT 1.0", "Taux de change"),
        ("approved_by", "VARCHAR(100)", "NULL", "Approuvé par"),
        ("approved_at", "TIMESTAMP WITH TIME ZONE", "NULL", "Date d'approbation"),
        ("payment_method", "VARCHAR(50)", "NULL", "Méthode de paiement"),
        ("bank_reference", "VARCHAR(100)", "NULL", "Référence bancaire"),
        ("comments", "TEXT", "NULL", "Commentaires sur la transaction"),
        (
            "adjustment_reason",
            "VARCHAR(200)",
            "NULL",
            "Raison d'ajustement si applicable",
        ),
        ("retroactive", "BOOLEAN", "DEFAULT FALSE", "Paiement rétroactif"),
        ("bonus_type", "VARCHAR(50)", "NULL", "Type de bonus si applicable"),
        ("deduction_type", "VARCHAR(50)", "NULL", "Type de déduction si applicable"),
        ("tax_year", "INTEGER", "NULL", "Année fiscale de référence"),
        ("tax_period", "VARCHAR(10)", "NULL", "Période fiscale (T1, T2, T3, T4)"),
        ("union_dues", "BIGINT", "DEFAULT 0", "Cotisations syndicales en cents"),
        (
            "pension_contribution",
            "BIGINT",
            "DEFAULT 0",
            "Contribution retraite en cents",
        ),
        ("health_insurance", "BIGINT", "DEFAULT 0", "Assurance santé en cents"),
        ("dental_insurance", "BIGINT", "DEFAULT 0", "Assurance dentaire en cents"),
        ("life_insurance", "BIGINT", "DEFAULT 0", "Assurance vie en cents"),
        (
            "disability_insurance",
            "BIGINT",
            "DEFAULT 0",
            "Assurance invalidité en cents",
        ),
        ("vacation_accrual", "NUMERIC(8,4)", "DEFAULT 0", "Accumulation vacances"),
        ("sick_accrual", "NUMERIC(8,4)", "DEFAULT 0", "Accumulation maladie"),
        ("personal_days", "NUMERIC(8,4)", "DEFAULT 0", "Jours personnels"),
        ("bereavement_leave", "NUMERIC(8,4)", "DEFAULT 0", "Congé de deuil"),
        ("jury_duty", "NUMERIC(8,4)", "DEFAULT 0", "Service de jury"),
        ("military_leave", "NUMERIC(8,4)", "DEFAULT 0", "Congé militaire"),
        ("maternity_leave", "NUMERIC(8,4)", "DEFAULT 0", "Congé maternité"),
        ("paternity_leave", "NUMERIC(8,4)", "DEFAULT 0", "Congé paternité"),
        ("adoption_leave", "NUMERIC(8,4)", "DEFAULT 0", "Congé adoption"),
        ("educational_leave", "NUMERIC(8,4)", "DEFAULT 0", "Congé éducatif"),
        ("sabbatical", "NUMERIC(8,4)", "DEFAULT 0", "Congé sabbatique"),
        ("unpaid_leave", "NUMERIC(8,4)", "DEFAULT 0", "Congé sans solde"),
        ("comp_time", "NUMERIC(8,4)", "DEFAULT 0", "Temps compensatoire"),
        ("floating_holiday", "NUMERIC(8,4)", "DEFAULT 0", "Jour férié flottant"),
        ("holiday_pay", "BIGINT", "DEFAULT 0", "Paiement jour férié en cents"),
        ("vacation_pay", "BIGINT", "DEFAULT 0", "Paiement vacances en cents"),
        ("sick_pay", "BIGINT", "DEFAULT 0", "Paiement maladie en cents"),
        ("severance_pay", "BIGINT", "DEFAULT 0", "Indemnité de licenciement en cents"),
        (
            "termination_pay",
            "BIGINT",
            "DEFAULT 0",
            "Paiement de fin de contrat en cents",
        ),
        ("commission", "BIGINT", "DEFAULT 0", "Commission en cents"),
        ("bonus", "BIGINT", "DEFAULT 0", "Bonus en cents"),
        ("stock_options", "BIGINT", "DEFAULT 0", "Options d'achat d'actions en cents"),
        (
            "profit_sharing",
            "BIGINT",
            "DEFAULT 0",
            "Participation aux bénéfices en cents",
        ),
        (
            "tuition_reimbursement",
            "BIGINT",
            "DEFAULT 0",
            "Remboursement frais de scolarité en cents",
        ),
        (
            "relocation_allowance",
            "BIGINT",
            "DEFAULT 0",
            "Allocation de réinstallation en cents",
        ),
        ("travel_allowance", "BIGINT", "DEFAULT 0", "Allocation de voyage en cents"),
        ("meal_allowance", "BIGINT", "DEFAULT 0", "Allocation de repas en cents"),
        ("phone_allowance", "BIGINT", "DEFAULT 0", "Allocation téléphone en cents"),
        ("internet_allowance", "BIGINT", "DEFAULT 0", "Allocation internet en cents"),
        ("parking_allowance", "BIGINT", "DEFAULT 0", "Allocation parking en cents"),
        ("fitness_allowance", "BIGINT", "DEFAULT 0", "Allocation fitness en cents"),
        (
            "professional_development",
            "BIGINT",
            "DEFAULT 0",
            "Développement professionnel en cents",
        ),
        ("home_office", "BIGINT", "DEFAULT 0", "Bureau à domicile en cents"),
        ("uniform_allowance", "BIGINT", "DEFAULT 0", "Allocation uniforme en cents"),
        ("tool_allowance", "BIGINT", "DEFAULT 0", "Allocation outils en cents"),
        ("safety_equipment", "BIGINT", "DEFAULT 0", "Équipement de sécurité en cents"),
        ("shift_differential", "BIGINT", "DEFAULT 0", "Prime d'équipe en cents"),
        ("on_call_pay", "BIGINT", "DEFAULT 0", "Paiement d'astreinte en cents"),
        ("callback_pay", "BIGINT", "DEFAULT 0", "Paiement de rappel en cents"),
        ("standby_pay", "BIGINT", "DEFAULT 0", "Paiement de garde en cents"),
        ("hazard_pay", "BIGINT", "DEFAULT 0", "Prime de risque en cents"),
        ("longevity_pay", "BIGINT", "DEFAULT 0", "Prime d'ancienneté en cents"),
        ("merit_increase", "BIGINT", "DEFAULT 0", "Augmentation au mérite en cents"),
        (
            "cost_of_living_adjustment",
            "BIGINT",
            "DEFAULT 0",
            "Ajustement coût de la vie en cents",
        ),
        ("market_adjustment", "BIGINT", "DEFAULT 0", "Ajustement marché en cents"),
        (
            "promotion_increase",
            "BIGINT",
            "DEFAULT 0",
            "Augmentation promotion en cents",
        ),
        (
            "demotion_decrease",
            "BIGINT",
            "DEFAULT 0",
            "Diminution rétrogradation en cents",
        ),
        ("salary_reduction", "BIGINT", "DEFAULT 0", "Réduction salaire en cents"),
        ("furlough", "BIGINT", "DEFAULT 0", "Congé sans solde payé en cents"),
        ("loan_deduction", "BIGINT", "DEFAULT 0", "Déduction prêt en cents"),
        ("garnishment", "BIGINT", "DEFAULT 0", "Saisie sur salaire en cents"),
        ("child_support", "BIGINT", "DEFAULT 0", "Pension alimentaire en cents"),
        ("alimony", "BIGINT", "DEFAULT 0", "Pension conjugale en cents"),
        ("medical_deduction", "BIGINT", "DEFAULT 0", "Déduction médicale en cents"),
        ("dental_deduction", "BIGINT", "DEFAULT 0", "Déduction dentaire en cents"),
        ("vision_deduction", "BIGINT", "DEFAULT 0", "Déduction optique en cents"),
        ("retirement_deduction", "BIGINT", "DEFAULT 0", "Déduction retraite en cents"),
        ("savings_deduction", "BIGINT", "DEFAULT 0", "Déduction épargne en cents"),
        ("charity_deduction", "BIGINT", "DEFAULT 0", "Déduction charité en cents"),
        ("parking_deduction", "BIGINT", "DEFAULT 0", "Déduction parking en cents"),
        (
            "transit_deduction",
            "BIGINT",
            "DEFAULT 0",
            "Déduction transport en commun en cents",
        ),
        ("health_savings", "BIGINT", "DEFAULT 0", "Épargne santé en cents"),
        ("flexible_spending", "BIGINT", "DEFAULT 0", "Dépenses flexibles en cents"),
        ("dependent_care", "BIGINT", "DEFAULT 0", "Garde d'enfants en cents"),
        ("adoption_assistance", "BIGINT", "DEFAULT 0", "Assistance adoption en cents"),
        ("student_loan", "BIGINT", "DEFAULT 0", "Prêt étudiant en cents"),
        ("credit_union", "BIGINT", "DEFAULT 0", "Crédit coopératif en cents"),
        ("other_deductions", "BIGINT", "DEFAULT 0", "Autres déductions en cents"),
        ("other_earnings", "BIGINT", "DEFAULT 0", "Autres gains en cents"),
    ]

    print("Colonnes à ajouter à payroll.payroll_transactions:")
    for col_name, col_type, constraints, description in transaction_columns:
        sql = f"ALTER TABLE payroll.payroll_transactions ADD COLUMN IF NOT EXISTS {col_name} {col_type} {constraints};"
        print(f"  - {col_name}: {description}")
        # print(f"    SQL: {sql}")  # Commenté pour ne pas surcharger l'output

    print(
        f"\n📊 Total: {len(transaction_columns)} colonnes proposées pour payroll.payroll_transactions\n"
    )

    # Générer un script SQL complet
    generate_sql_script(employee_columns, transaction_columns)


def generate_sql_script(employee_columns, transaction_columns):
    """Génère un script SQL complet pour les ajouts de colonnes"""

    script_content = f"""-- Script d'ajout de colonnes métier - Généré le {datetime.now().isoformat()}
-- Base de données: payroll_db
-- Attention: Testez sur une base de développement avant production

\\c payroll_db

-- =============================================================================
-- AJOUT DE COLONNES À core.employees
-- =============================================================================

"""

    for col_name, col_type, constraints, description in employee_columns:
        script_content += f"-- {description}\n"
        script_content += f"ALTER TABLE core.employees ADD COLUMN IF NOT EXISTS {col_name} {col_type} {constraints};\n\n"

    script_content += """
-- =============================================================================
-- AJOUT DE COLONNES À payroll.payroll_transactions
-- =============================================================================

"""

    for col_name, col_type, constraints, description in transaction_columns:
        script_content += f"-- {description}\n"
        script_content += f"ALTER TABLE payroll.payroll_transactions ADD COLUMN IF NOT EXISTS {col_name} {col_type} {constraints};\n\n"

    script_content += """
-- =============================================================================
-- CRÉATION D'INDEX POUR LES NOUVELLES COLONNES
-- =============================================================================

-- Index sur les colonnes fréquemment utilisées dans core.employees
CREATE INDEX IF NOT EXISTS idx_employees_department ON core.employees(department);
CREATE INDEX IF NOT EXISTS idx_employees_hire_date ON core.employees(hire_date);
CREATE INDEX IF NOT EXISTS idx_employees_manager_id ON core.employees(manager_id);
CREATE INDEX IF NOT EXISTS idx_employees_email ON core.employees(email);
CREATE INDEX IF NOT EXISTS idx_employees_contract_type ON core.employees(contract_type);

-- Index sur les colonnes fréquemment utilisées dans payroll.payroll_transactions
CREATE INDEX IF NOT EXISTS idx_transactions_cost_center ON payroll.payroll_transactions(cost_center);
CREATE INDEX IF NOT EXISTS idx_transactions_project_code ON payroll.payroll_transactions(project_code);
CREATE INDEX IF NOT EXISTS idx_transactions_pay_date_cost_center ON payroll.payroll_transactions(pay_date, cost_center);
CREATE INDEX IF NOT EXISTS idx_transactions_tax_year ON payroll.payroll_transactions(tax_year);
CREATE INDEX IF NOT EXISTS idx_transactions_approved_at ON payroll.payroll_transactions(approved_at);

-- =============================================================================
-- CONTRAINTES SUPPLÉMENTAIRES (À AJOUTER SI NÉCESSAIRE)
-- =============================================================================

-- Exemples de contraintes (décommentez si nécessaire):

-- Contrainte sur l'email
-- ALTER TABLE core.employees ADD CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$');

-- Contrainte sur les dates
-- ALTER TABLE core.employees ADD CONSTRAINT chk_hire_date_past CHECK (hire_date <= CURRENT_DATE);
-- ALTER TABLE core.employees ADD CONSTRAINT chk_birth_date_reasonable CHECK (birth_date >= '1900-01-01' AND birth_date <= CURRENT_DATE - INTERVAL '16 years');

-- Contrainte sur les montants positifs
-- ALTER TABLE payroll.payroll_transactions ADD CONSTRAINT chk_positive_amounts CHECK (amount_cents >= 0);

-- =============================================================================
-- FIN DU SCRIPT
-- =============================================================================

\\q
"""

    filename = f"add_business_columns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(script_content)

    print(f"✅ Script SQL généré: {filename}")
    print(f"   - {len(employee_columns)} colonnes pour core.employees")
    print(f"   - {len(transaction_columns)} colonnes pour payroll.payroll_transactions")
    print("   - Index et contraintes inclus")


def main():
    """Fonction principale"""
    print("AJOUT DE COLONNES METIER A LA BASE PAYROLL\n")

    try:
        add_business_columns()

        print("\n" + "=" * 80)
        print("📋 RÉSUMÉ DES MODIFICATIONS PROPOSÉES:")
        print(
            "• core.employees: +40 colonnes métier (département, poste, contact, etc.)"
        )
        print(
            "• payroll.payroll_transactions: +70 colonnes détaillées (charges sociales, avantages, etc.)"
        )
        print("• Index automatiques sur les colonnes fréquemment utilisées")
        print("• Script SQL complet généré pour exécution")
        print("=" * 80)
        print("\nWARN:  IMPORTANT:")
        print("• Testez d'abord sur une base de développement")
        print("• Faites une sauvegarde complète avant exécution")
        print("• Vérifiez l'impact sur les performances")
        print("• Mettez à jour l'application pour utiliser les nouvelles colonnes")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
