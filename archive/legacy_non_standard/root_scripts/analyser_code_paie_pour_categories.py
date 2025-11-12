#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyser code_paie pour déterminer les catégories"""
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg
from app.config import settings
import logging

logger = logging.getLogger(__name__)

print("=" * 70)
print("ANALYSE: code_paie pour déterminer Gains vs Déductions")
print("=" * 70)
print("")

settings.bootstrap_env()
dsn = settings.get_dsn()
if not dsn:
    reason = settings.dsn_error_reason or "DSN non configuré"
    logger.error("Impossible d'obtenir un DSN valide: %s", reason)
    raise SystemExit(1)

try:
    conn = psycopg.connect(dsn)
    cur = conn.cursor()

    # Analyser code_paie par signe du montant
    print("1. ANALYSE: code_paie selon le signe de montant_employe:")
    print("-" * 70)

    cur.execute(
        """
        SELECT 
            code_paie,
            COUNT(*) AS nb_lignes,
            COUNT(CASE WHEN montant_employe > 0 THEN 1 END) AS nb_positifs,
            COUNT(CASE WHEN montant_employe < 0 THEN 1 END) AS nb_negatifs,
            COUNT(CASE WHEN montant_employe = 0 THEN 1 END) AS nb_zeros,
            SUM(CASE WHEN montant_employe > 0 THEN montant_employe ELSE 0 END) AS somme_positifs,
            SUM(CASE WHEN montant_employe < 0 THEN montant_employe ELSE 0 END) AS somme_negatifs
        FROM payroll.imported_payroll_master
        WHERE date_paie = '2025-08-28'
        GROUP BY code_paie
        ORDER BY nb_lignes DESC
        LIMIT 30
    """
    )

    codes = cur.fetchall()

    print("\n   Codes de paie (top 30):\n")

    for code, nb, nb_pos, nb_neg, nb_zero, somme_pos, somme_neg in codes:
        # Déterminer si c'est plutôt un gain ou une déduction
        if nb_pos > nb_neg:
            type_likely = "GAINS (majorité positifs)"
            ratio = f"{nb_pos}/{nb} positifs"
        elif nb_neg > nb_pos:
            type_likely = "DÉDUCTIONS (majorité négatifs)"
            ratio = f"{nb_neg}/{nb} négatifs"
        else:
            type_likely = "MIXTE"
            ratio = f"{nb_pos} pos, {nb_neg} neg"

        print(f"   {code}:")
        print(f"      {ratio} → {type_likely}")
        if somme_pos > 0:
            print(f"      Somme positifs: {somme_pos:,.2f}")
        if somme_neg < 0:
            print(f"      Somme négatifs: {somme_neg:,.2f}")
        print()

    # Règle de standardisation proposée
    print("\n2. RÈGLE STANDARD PROPOSÉE:")
    print("-" * 70)
    print("   Option A: Utiliser le signe du montant")
    print("      - montant_employe > 0 → GAINS")
    print("      - montant_employe < 0 → DÉDUCTIONS")
    print("      - total_net = SUM(montant_employe) (somme algébrique)")
    print()
    print("   Option B: Utiliser code_paie avec mapping")
    print("      - Besoin d'une table de mapping code_paie → catégorie")
    print()
    print("   Option C: Standardisé (somme simple, pas d'inversion)")
    print("      - total_net = SUM(montant_employe)")
    print("      - Pas de distinction Gains/Déductions dans le calcul")

    conn.close()

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()

print("")
