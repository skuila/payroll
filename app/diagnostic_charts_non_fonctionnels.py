#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostic complet des charts/KPI non fonctionnels"""
import sys
import io
import json
import os
import requests

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

session = requests.Session()

print("=" * 70)
print("DIAGNOSTIC - CHARTS/KPI NON FONCTIONNELS")
print("=" * 70)
print("")

# Authentification HTTP
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

# 1. Tester les datasets (vues SQL)
print("1. TEST DES DATASETS (VUES SQL):")
print("-" * 70)

response = session.get(
    "http://localhost:8088/api/v1/dataset/?q=(page:0,page_size:100)", timeout=10
)
datasets: list = response.json().get("result", [])

datasets_vues = [
    d for d in datasets if d.get("table_name", "").startswith("v_payroll_")
]

print(f"   Datasets avec vues: {len(datasets_vues)}\n")

for ds in datasets_vues:
    ds_id = ds.get("id")
    ds_name = ds.get("table_name")
    ds_schema = ds.get("schema", "")

    print(f"   Dataset: {ds_name} (ID: {ds_id})")

    # Récupérer le détail
    try:
        detail_response = session.get(
            f"http://localhost:8088/api/v1/dataset/{ds_id}/", timeout=10
        )
        if detail_response.status_code == 200:
            ds_detail = detail_response.json().get("result", {})

            # Colonnes
            columns = ds_detail.get("columns", [])
            print(f"      Colonnes: {len(columns)}")

            # Métriques
            metrics = ds_detail.get("metrics", [])
            print(f"      Métriques: {len(metrics)}")

            if metrics:
                for m in metrics:
                    m_name = m.get("metric_name", "N/A")
                    m_expr = m.get("expression", "N/A")
                    print(f"         - {m_name}: {m_expr[:60]}")

            # Tester une requête simple
            try:
                query_response = session.post(
                    "http://localhost:8088/api/v1/chart/data/",
                    json={
                        "datasource": {"id": ds_id, "type": "table"},
                        "query_context": {
                            "datasource": {"id": ds_id, "type": "table"},
                            "force": True,
                        },
                        "queries": [{"row_limit": 5}],
                    },
                    timeout=15,
                )

                if query_response.status_code == 200:
                    query_data = query_response.json()
                    result = (
                        query_data.get("result", [{}])[0]
                        if query_data.get("result")
                        else {}
                    )
                    data = result.get("data", [])
                    print(f"      ✅ Requête test: OK ({len(data)} lignes)")
                else:
                    error_data = (
                        query_response.json()
                        if query_response.headers.get("content-type", "").startswith(
                            "application/json"
                        )
                        else {}
                    )
                    error_msg = (
                        error_data.get("message", "")
                        or error_data.get("error", "")
                        or query_response.text[:200]
                    )
                    print(f"      ❌ Requête test échouée: {error_msg[:150]}")
            except Exception as e:
                print(f"      ❌ Erreur test requête: {str(e)[:100]}")
        else:
            print(
                f"      ❌ Impossible de récupérer les détails: {detail_response.status_code}"
            )
    except Exception as e:
        print(f"      ❌ Erreur: {str(e)[:100]}")

    print("")

print("")

# 2. Tester les charts/KPI
print("2. TEST DES CHARTS/KPI:")
print("-" * 70)

response = session.get(
    "http://localhost:8088/api/v1/chart/?q=(page:0,page_size:100)", timeout=10
)
all_charts = response.json().get("result", [])

# Charts payroll (IDs 112-120)
payroll_charts = [
    c
    for c in all_charts
    if c.get("id") in [112, 113, 114, 115, 116, 117, 118, 119, 120]
]

print(f"   Charts payroll à tester: {len(payroll_charts)}\n")

for chart in payroll_charts:
    chart_id = chart.get("id")
    chart_name = chart.get("slice_name", "N/A")
    ds_id = chart.get("datasource_id")
    viz_type = chart.get("viz_type", "N/A")

    print(f"   Chart: {chart_name} (ID: {chart_id}, Type: {viz_type})")

    # Récupérer le détail complet
    try:
        chart_response = session.get(
            f"http://localhost:8088/api/v1/chart/{chart_id}/", timeout=10
        )
        if chart_response.status_code == 200:
            chart_detail = chart_response.json().get("result", {})

            # Vérifier les params
            params = chart_detail.get("params", {})
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except Exception as _exc:
                    params = {}

            # Métriques utilisées
            metrics = params.get("metrics", [])
            print(f"      Métriques dans chart: {metrics}")

            # Colonnes
            groupby = params.get("groupby", [])
            print(f"      Groupby: {groupby}")

            # Tester le chart
            try:
                # Construire la requête pour le chart
                chart_query = {
                    "datasource": {"id": ds_id, "type": "table"},
                    "query_context": {
                        "datasource": {"id": ds_id, "type": "table"},
                        "force": True,
                    },
                    "queries": [
                        {
                            "metrics": metrics if metrics else [],
                            "groupby": groupby if groupby else [],
                            "row_limit": 10,
                        }
                    ],
                }

                query_response = session.post(
                    "http://localhost:8088/api/v1/chart/data/",
                    json=chart_query,
                    timeout=15,
                )

                if query_response.status_code == 200:
                    query_data = query_response.json()
                    result = (
                        query_data.get("result", [{}])[0]
                        if query_data.get("result")
                        else {}
                    )
                    data = result.get("data", [])
                    error = result.get("error")

                    if error:
                        print(f"      ❌ Erreur dans les données: {error[:150]}")
                    else:
                        print(
                            f"      ✅ Chart fonctionnel: {len(data)} lignes de données"
                        )
                else:
                    error_data = (
                        query_response.json()
                        if query_response.headers.get("content-type", "").startswith(
                            "application/json"
                        )
                        else {}
                    )
                    error_msg = (
                        error_data.get("message", "")
                        or error_data.get("error", "")
                        or query_response.text[:200]
                    )
                    print(f"      ❌ Erreur requête chart: {error_msg[:150]}")
            except Exception as e:
                print(f"      ❌ Erreur test chart: {str(e)[:150]}")
        else:
            print(
                f"      ❌ Impossible de récupérer le chart: {chart_response.status_code}"
            )
    except Exception as e:
        print(f"      ❌ Erreur: {str(e)[:100]}")

    print("")

print("")

# 3. Vérifier les vues SQL directement dans la base
print("3. VÉRIFICATION DES VUES SQL DANS LA BASE:")
print("-" * 70)

sys.path.insert(0, ".")
from app.services.data_repo import DataRepository


try:
    # Build DSN from environment to avoid hard-coded credentials in the repo.
    # Environment variables used (optional): DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME, DATABASE_DSN
    dsn = os.environ.get("DATABASE_DSN") or (
        f"postgresql://{os.environ.get('DB_USER','payroll_app')}:"
        f"{os.environ.get('DB_PASS','__SET_AT_DEPLOY__')}@"
        f"{os.environ.get('DB_HOST','localhost')}:{os.environ.get('DB_PORT','5432')}/"
        f"{os.environ.get('DB_NAME','payroll_db')}"
    )

    if "__SET_AT_DEPLOY__" in dsn:
        print(
            "WARNING: Using placeholder DB password; set DB_PASS or DATABASE_DSN in environment for real connections"
        )

    repo = DataRepository(dsn)
    conn = repo.get_connection().__enter__()
    cur = conn.cursor()

    # Tester chaque vue
    vues = [
        "v_payroll_detail",
        "v_payroll_par_periode",
        "v_payroll_par_budget",
        "v_payroll_par_code",
        "v_payroll_kpi",
    ]

    for vue_name in vues:
        print(f"   Vue: {vue_name}")
        try:
            # Test simple: COUNT(*)
            cur.execute(f"SELECT COUNT(*) FROM payroll.{vue_name}")
            count = cur.fetchone()[0]
            print(f"      ✅ Vue accessible: {count} lignes")

            # Tester avec quelques colonnes
            if vue_name == "v_payroll_kpi":
                cur.execute(f"SELECT * FROM payroll.{vue_name} LIMIT 1")
            else:
                cur.execute(
                    f"SELECT date_paie, COUNT(*) FROM payroll.{vue_name} GROUP BY date_paie LIMIT 3"
                )

            rows = cur.fetchall()
            print(f"      ✅ Requête test: OK ({len(rows)} lignes)")
        except Exception as e:
            print(f"      ❌ Erreur: {str(e)[:150]}")
        print("")

    conn.__exit__(None, None, None)
    repo.close()
except Exception as e:
    print(f"   ❌ Erreur connexion base: {e}")

print("")

# 4. Résumé des problèmes
print("=" * 70)
print("RÉSUMÉ DES PROBLÈMES:")
print("=" * 70)

print(
    """
Vérifiez les erreurs ci-dessus pour identifier:
1. ❌ Datasets non accessibles → Problème de connexion ou vues SQL
2. ❌ Métriques invalides → Noms de métriques incorrects dans les charts
3. ❌ Colonnes manquantes → Colonnes référencées n'existent pas dans les datasets
4. ❌ Erreurs SQL → Les vues SQL ont des erreurs

Solutions possibles:
- Corriger les métriques dans les charts
- Vérifier que les vues SQL sont accessibles
- Vérifier les colonnes des datasets
- Corriger les requêtes SQL des vues
"""
)

print("")
