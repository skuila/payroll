#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corriger l'erreur 'does not exist' dans les charts"""
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# requests n'est plus utilisé (suppression API)
import json

print("=" * 70)
print("CORRECTION ERREUR 'DOES NOT EXIST' DANS LES CHARTS")
print("=" * 70)
print("")

# Authentification
# session HTTP supprimée
response = session.post(
    "http://localhost:8088/api/v1/security/login",
    json={"username": "admin", "password": "admin", "provider": "db", "refresh": True},
)
access_token = response.json().get("access_token")
session.headers.update(
    {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
)

csrf_response = session.get(
    "http://localhost:8088/api/v1/security/csrf_token/", timeout=10
)
if csrf_response.status_code == 200:
    csrf_data = csrf_response.json()
    csrf_token = (
        csrf_data.get("result", {}).get("csrf_token")
        if isinstance(csrf_data.get("result"), dict)
        else csrf_data.get("result")
    )
    if csrf_token:
        session.headers.update({"X-CSRFToken": csrf_token})

print("✅ Authentifié")
print("")

# 1. Récupérer les datasets et leurs colonnes/métriques
print("1. DATASETS ET LEURS COLONNES/MÉTRIQUES:")
print("-" * 70)

response = session.get(
    "http://localhost:8088/api/v1/dataset/?q=(page:0,page_size:100)", timeout=10
)
datasets = response.json().get("result", [])

datasets_vues = {}
for ds in datasets:
    if ds.get("table_name", "").startswith("v_payroll_"):
        ds_id = ds.get("id")
        ds_name = ds.get("table_name")

        # Récupérer via l'API de liste (qui fonctionne)
        # Utiliser l'endpoint qui liste les colonnes
        try:
            # Essayer de récupérer via l'explore endpoint
            explore_response = session.get(
                f"http://localhost:8088/api/v1/dataset/{ds_id}/", timeout=10
            )
            if explore_response.status_code == 200:
                ds_detail = explore_response.json().get("result", {})
                columns = ds_detail.get("columns", [])
                metrics = ds_detail.get("metrics", [])

                datasets_vues[ds_id] = {
                    "name": ds_name,
                    "columns": {col.get("column_name"): col for col in columns},
                    "metrics": {m.get("metric_name"): m for m in metrics},
                }

                print(f"\n   Dataset: {ds_name} (ID: {ds_id})")
                print(f"      Colonnes: {len(columns)}")
                for col in columns[:10]:
                    print(f"         - {col.get('column_name')} ({col.get('type')})")

                print(f"      Métriques: {len(metrics)}")
                for m in metrics:
                    print(
                        f"         - {m.get('metric_name')}: {m.get('expression', 'N/A')[:60]}"
                    )
        except Exception as e:
            print(f"   WARN:  Erreur récupération {ds_name}: {str(e)[:100]}")

print("")

# 2. Vérifier les charts et leurs métriques/colonnes
print("2. CHARTS ET LEURS MÉTRIQUES/COLONNES:")
print("-" * 70)

response = session.get(
    "http://localhost:8088/api/v1/chart/?q=(page:0,page_size:100)", timeout=10
)
all_charts = response.json().get("result", [])

payroll_charts = [
    c
    for c in all_charts
    if c.get("id") in [112, 113, 114, 115, 116, 117, 118, 119, 120]
]

print(f"   Charts à vérifier: {len(payroll_charts)}\n")

charts_to_fix = []

for chart in payroll_charts:
    chart_id = chart.get("id")
    chart_name = chart.get("slice_name", "N/A")
    ds_id = chart.get("datasource_id")

    print(f"   Chart: {chart_name} (ID: {chart_id}, Dataset: {ds_id})")

    # Récupérer les params du chart depuis la liste (qui contient déjà params)
    params_str = chart.get("params", "{}")
    if isinstance(params_str, str):
        try:
            params = json.loads(params_str)
        except Exception as _exc:
            params = {}
    else:
        params = params_str

    # Métriques utilisées
    metrics_used = params.get("metrics", [])
    groupby_used = params.get("groupby", [])

    print(f"      Métriques utilisées: {metrics_used}")
    print(f"      Groupby: {groupby_used}")

    # Vérifier si le dataset existe
    if ds_id not in datasets_vues:
        print(f"      ❌ Dataset ID {ds_id} non trouvé dans la liste")
        continue

    ds_info = datasets_vues[ds_id]
    print(f"      Dataset: {ds_info['name']}")

    # Vérifier les métriques
    problems = []
    for metric in metrics_used:
        # Les métriques peuvent être des strings ou des objets
        metric_name = (
            metric
            if isinstance(metric, str)
            else metric.get("label") or metric.get("expression")
        )

        # Si c'est une expression SQL directe, ne pas vérifier
        if isinstance(metric, str) and (
            "(" in metric or "SUM" in metric.upper() or "COUNT" in metric.upper()
        ):
            print(f"         ✅ Métrique '{metric}' (expression SQL directe)")
            continue

        # Vérifier si la métrique existe dans le dataset
        if (
            metric_name not in ds_info["metrics"]
            and metric_name not in ds_info["columns"]
        ):
            print(
                f"         ❌ Métrique/colonne '{metric_name}' N'EXISTE PAS dans le dataset"
            )
            problems.append(f"Metric '{metric_name}' does not exist")
        else:
            print(f"         ✅ Métrique '{metric_name}' existe")

    # Vérifier les groupby
    for col in groupby_used:
        if col not in ds_info["columns"]:
            print(f"         ❌ Colonne groupby '{col}' N'EXISTE PAS dans le dataset")
            problems.append(f"Column '{col}' does not exist")
        else:
            print(f"         ✅ Colonne groupby '{col}' existe")

    if problems:
        charts_to_fix.append(
            {
                "chart_id": chart_id,
                "chart_name": chart_name,
                "ds_id": ds_id,
                "ds_name": ds_info["name"],
                "problems": problems,
                "params": params,
            }
        )

    print("")

print("")

# 3. Afficher les colonnes disponibles pour créer les bonnes métriques
print("3. COLONNES DISPONIBLES DANS LES DATASETS:")
print("-" * 70)

for ds_id, ds_info in datasets_vues.items():
    print(f"\n   {ds_info['name']} (ID: {ds_id}):")
    print("      Colonnes numériques (pour métriques):")
    numeric_cols = [
        name
        for name, col in ds_info["columns"].items()
        if "numeric" in str(col.get("type", "")).lower()
        or "int" in str(col.get("type", "")).lower()
        or "bigint" in str(col.get("type", "")).lower()
    ]
    for col in numeric_cols[:10]:
        print(f"         - {col}")

print("")

# 4. Résumé et solutions
print("=" * 70)
print("RÉSUMÉ DES PROBLÈMES:")
print("=" * 70)

if charts_to_fix:
    print(f"\n   Charts avec problèmes: {len(charts_to_fix)}\n")

    for chart_info in charts_to_fix:
        print(f"   Chart: {chart_info['chart_name']} (ID: {chart_info['chart_id']})")
        print(f"      Dataset: {chart_info['ds_name']} (ID: {chart_info['ds_id']})")
        print("      Problèmes:")
        for prob in chart_info["problems"]:
            print(f"         - {prob}")
        print("")

    print("\n   SOLUTION:")
    print(
        "   Les métriques doivent utiliser les colonnes qui existent dans les datasets."
    )
    print("   Pour les KPI, utiliser directement les colonnes numériques.")
    print(
        "   Pour les graphiques, créer des métriques SUM() ou COUNT() sur les colonnes existantes."
    )
else:
    print("\n   ✅ Aucun problème de métriques détecté")
    print(
        "   L'erreur 'does not exist' peut venir d'un autre problème (droits, vues SQL, etc.)"
    )

print("")

# 5. Créer un fichier avec les corrections à faire
if charts_to_fix:
    corrections = []
    corrections.append("# CORRECTIONS DES MÉTRIQUES DANS LES CHARTS\n")
    corrections.append("# Utiliser les colonnes disponibles dans les datasets\n\n")

    for chart_info in charts_to_fix:
        corrections.append(
            f"## Chart: {chart_info['chart_name']} (ID: {chart_info['chart_id']})\n"
        )
        corrections.append(f"Dataset: {chart_info['ds_name']}\n")
        corrections.append(f"Problèmes: {', '.join(chart_info['problems'])}\n")

        # Suggérer des corrections
        ds_cols = datasets_vues[chart_info["ds_id"]]["columns"]
        numeric_cols = [
            name
            for name, col in ds_cols.items()
            if "numeric" in str(col.get("type", "")).lower()
        ]

        if numeric_cols:
            corrections.append(
                f"Colonnes disponibles pour métriques: {', '.join(numeric_cols[:5])}\n"
            )
            corrections.append(
                f"Suggestion: Utiliser SUM({numeric_cols[0]}) ou les colonnes directement\n"
            )
        corrections.append("\n")

    with open("CORRECTIONS_METRIQUES.md", "w", encoding="utf-8") as f:
        f.write("\n".join(corrections))

    print("   Fichier créé: CORRECTIONS_METRIQUES.md")

print("")
