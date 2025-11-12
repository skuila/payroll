#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyser les périodes de paie dans la base de données"""
import sys

sys.path.insert(0, ".")

from app.services.data_repo import DataRepository
from app.config.config_manager import get_dsn

print("=" * 70)
print("ANALYSE DES PÉRIODES DE PAIE")
print("=" * 70)
print("")

repo = DataRepository(get_dsn())
conn = repo.get_connection().__enter__()
cur = conn.cursor()

# 1. Structure de la table pay_periods
print("1. STRUCTURE DE LA TABLE pay_periods:")
print("-" * 70)
cur.execute(
    """
    SELECT 
        column_name, 
        data_type, 
        column_default,
        is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'payroll' 
      AND table_name = 'pay_periods'
    ORDER BY ordinal_position
"""
)

colonnes = cur.fetchall()
for col_name, data_type, default, nullable in colonnes:
    default_str = f" (default: {default})" if default else ""
    null_str = "NULL" if nullable == "YES" else "NOT NULL"
    print(f"   - {col_name:<25} : {data_type:<20} {null_str}{default_str}")

print("")

# 2. Données réelles dans pay_periods
print("2. PÉRIODES EXISTANTES DANS LA BASE:")
print("-" * 70)

cur.execute(
    """
    SELECT 
        pay_date,
        pay_day,
        pay_month,
        pay_year,
        period_seq_in_year,
        status,
        created_at
    FROM payroll.pay_periods
    ORDER BY pay_date DESC
    LIMIT 20
"""
)

periodes = cur.fetchall()

if periodes:
    print(f"   Total périodes trouvées: {len(periodes)}")
    print(
        f"\n   {'Date':<12} {'Jour':<6} {'Mois':<6} {'Année':<8} {'Seq':<6} {'Status':<10} {'Créé le'}"
    )
    print("   " + "-" * 70)
    for p in periodes:
        date_val, day, month, year, seq, status, created = p
        print(
            f"   {str(date_val):<12} {day:<6} {month:<6} {year:<8} {seq:<6} {status:<10} {str(created)[:16]}"
        )

    # Analyser les intervalles
    if len(periodes) > 1:
        print("\n   Intervalles entre périodes:")
        dates = [p[0] for p in periodes]
        dates.sort()
        intervals = []
        for i in range(len(dates) - 1):
            delta = (dates[i + 1] - dates[i]).days
            intervals.append(delta)

        if intervals:
            print(f"   - Intervalle moyen: {sum(intervals) / len(intervals):.1f} jours")
            print(f"   - Intervalle min: {min(intervals)} jours")
            print(f"   - Intervalle max: {max(intervals)} jours")

            # Déterminer la fréquence
            avg_interval = sum(intervals) / len(intervals)
            if 6 <= avg_interval <= 8:
                print("\n   → Fréquence probable: HEBDOMADAIRE (toutes les ~7 jours)")
            elif 13 <= avg_interval <= 15:
                print(
                    "\n   → Fréquence probable: BI-HEBDOMADAIRE (toutes les ~14 jours)"
                )
            elif 14 <= avg_interval <= 16:
                print("\n   → Fréquence probable: BI-MENSUELLE (2 fois par mois)")
            elif 28 <= avg_interval <= 32:
                print("\n   → Fréquence probable: MENSUELLE (une fois par mois)")
            else:
                print(f"\n   → Fréquence: {avg_interval:.1f} jours (irrégulier)")
else:
    print("   WARN:  Aucune période trouvée dans pay_periods")

print("")

# 3. Dates distinctes dans imported_payroll_master
print("3. DATES DE PAIE DANS imported_payroll_master:")
print("-" * 70)

cur.execute(
    """
    SELECT 
        date_paie,
        COUNT(*) as nb_transactions,
        COUNT(DISTINCT matricule) as nb_employes
    FROM payroll.imported_payroll_master
    GROUP BY date_paie
    ORDER BY date_paie DESC
"""
)

dates_paie = cur.fetchall()

if dates_paie:
    print(f"   Dates distinctes: {len(dates_paie)}")
    print(f"\n   {'Date de paie':<12} {'Nb transactions':<18} {'Nb employés'}")
    print("   " + "-" * 45)
    for date_val, nb_tx, nb_emp in dates_paie[:10]:
        print(f"   {str(date_val):<12} {nb_tx:<18} {nb_emp}")

    # Analyser les intervalles
    if len(dates_paie) > 1:
        dates = [d[0] for d in dates_paie]
        dates.sort()
        intervals = []
        for i in range(len(dates) - 1):
            delta = (dates[i + 1] - dates[i]).days
            intervals.append(delta)

        if intervals:
            print("\n   Intervalles entre dates de paie:")
            print(f"   - Intervalle moyen: {sum(intervals) / len(intervals):.1f} jours")
            print(f"   - Intervalle min: {min(intervals)} jours")
            print(f"   - Intervalle max: {max(intervals)} jours")

            # Fréquence
            avg_interval = sum(intervals) / len(intervals)
            if 6 <= avg_interval <= 8:
                freq = "HEBDOMADAIRE"
            elif 13 <= avg_interval <= 15:
                freq = "BI-HEBDOMADAIRE"
            elif 14 <= avg_interval <= 16:
                freq = "BI-MENSUELLE"
            elif 28 <= avg_interval <= 32:
                freq = "MENSUELLE"
            else:
                freq = f"{avg_interval:.1f} jours (irrégulier)"

            print(f"\n   → Fréquence dans les données: {freq}")
else:
    print("   WARN:  Aucune date de paie trouvée")

print("")

# 4. Analyse period_seq_in_year
print("4. ANALYSE period_seq_in_year:")
print("-" * 70)

cur.execute(
    """
    SELECT 
        pay_year,
        COUNT(*) as nb_periodes,
        MIN(period_seq_in_year) as seq_min,
        MAX(period_seq_in_year) as seq_max,
        STRING_AGG(DISTINCT period_seq_in_year::text, ', ' ORDER BY period_seq_in_year::text) as sequences
    FROM payroll.pay_periods
    GROUP BY pay_year
    ORDER BY pay_year DESC
"""
)

sequences = cur.fetchall()

if sequences:
    for year, nb, seq_min, seq_max, seq_list in sequences:
        print(f"   Année {year}:")
        print(f"      - Nombre de périodes: {nb}")
        print(f"      - Séquence min: {seq_min}, max: {seq_max}")
        if seq_max <= 26:
            print(
                "      → Probable: BI-HEBDOMADAIRE (26 périodes/an = ~52 semaines / 2)"
            )
        elif seq_max <= 12:
            print("      → Probable: MENSUELLE (12 périodes/an)")
        elif seq_max <= 24:
            print("      → Probable: BI-MENSUELLE (24 périodes/an = 2 par mois)")
        else:
            print("      → Irrégulier ou hebdomadaire (53 max)")
        print(f"      - Séquences: {seq_list[:100]}")
        print("")
else:
    print("   WARN:  Aucune séquence trouvée")

print("")

# 5. Conclusion
print("=" * 70)
print("CONCLUSION:")
print("=" * 70)

print(
    """
DÉFINITION D'UNE PÉRIODE DE PAIE:

1. Une période de paie = UNE DATE DE PAIE SPÉCIFIQUE (pay_date)
   - Exemple: 2025-08-28 (28 août 2025)
   - Chaque date de paie = 1 période unique

2. Structure d'une période:
   - pay_date: DATE complète (jour/mois/année)
   - pay_day: Jour du mois (1-31)
   - pay_month: Mois (1-12)
   - pay_year: Année
   - period_seq_in_year: Numéro séquentiel dans l'année (1-53 max)

3. Fréquence:
   - La colonne period_seq_in_year suggère une fréquence BI-HEBDOMADAIRE
   - (1-26 pour bi-hebdo = 26 périodes par an)
   - Mais peut être adaptée: hebdomadaire (52), mensuelle (12), etc.

4. Statut:
   - ouverte: Période active, peut recevoir des imports
   - fermée: Période verrouillée, plus d'imports possibles
   - archivée: Période archivée

5. Unicité:
   - Une seule période par date (contrainte UNIQUE sur pay_date)
   - Une seule séquence par année (contrainte UNIQUE sur pay_year, period_seq_in_year)
"""
)

conn.__exit__(None, None, None)
repo.close()

print("")
