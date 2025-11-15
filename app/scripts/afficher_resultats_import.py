#!/usr/bin/env python3
"""Affiche les résultats de l'import de nouveau.xlsx"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.connection_standard import get_dsn
from services.data_repo import DataRepository

repo = DataRepository(get_dsn())

sql = """
SELECT 
    COUNT(DISTINCT matricule) as nb_employes,
    COUNT(*) as nb_lignes,
    COALESCE(SUM(montant_employe), 0) as salaire_net_total,
    COALESCE(SUM(CASE WHEN montant_employe > 0 THEN montant_employe ELSE 0 END), 0) as gains_brut,
    COALESCE(SUM(CASE WHEN montant_employe < 0 THEN ABS(montant_employe) ELSE 0 END), 0) as deductions
FROM payroll.imported_payroll_master
WHERE date_paie = %(pay_date)s::date
"""

result = repo.run_query(sql, {"pay_date": "2025-08-28"}, fetch_one=True)

if result:
    nb_employes = result[0] or 0
    nb_lignes = result[1] or 0
    salaire_net_total = result[2] or 0.0
    gains_brut = result[3] or 0.0
    deductions = result[4] or 0.0

    print("=" * 70)
    print("RÉSULTATS DE L'IMPORT - nouveau.xlsx")
    print("=" * 70)
    print("Date de paie: 2025-08-28")
    print(f"Nombre d'employés: {nb_employes}")
    print(f"Nombre de lignes importées: {nb_lignes}")
    print(f"Salaire net global: {salaire_net_total:,.2f} $")
    print(f"Gains bruts: {gains_brut:,.2f} $")
    print(f"Déductions: {deductions:,.2f} $")
    print("=" * 70)
else:
    print("Aucune donnée trouvée")
