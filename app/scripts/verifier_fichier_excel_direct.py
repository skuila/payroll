#!/usr/bin/env python3
"""Vérifie les données du fichier Excel directement"""

import pandas as pd

file_path = r"C:\Users\SZERTYUIOPMLMM\Desktop\APP\app\nouveau.xlsx"

df = pd.read_excel(file_path, engine="openpyxl")
df["montant_employe"] = pd.to_numeric(df["montant_employe"], errors="coerce")

total = df["montant_employe"].sum()
gains = df[df["montant_employe"] > 0]["montant_employe"].sum()
deductions = abs(df[df["montant_employe"] < 0]["montant_employe"].sum())
nb_employes = df["matricule"].nunique()
nb_lignes = len(df)

print("=" * 70)
print("RÉSULTATS DU FICHIER EXCEL - nouveau.xlsx")
print("=" * 70)
print(f"Nombre d'employés: {nb_employes}")
print(f"Nombre de lignes: {nb_lignes}")
print(f"Salaire net global: {total:,.2f} $")
print(f"Gains bruts: {gains:,.2f} $")
print(f"Déductions: {deductions:,.2f} $")
print("=" * 70)
