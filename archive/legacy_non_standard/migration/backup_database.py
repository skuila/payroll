#!/usr/bin/env python3
"""
Script de backup PostgreSQL (alternatif à pg_dump)
Utilise Python pour créer un backup de la base
"""

import sys
import os
import subprocess
from datetime import datetime

# Configuration
DSN = os.getenv("PAYROLL_DSN") or "postgresql://payroll_app@localhost:5432/payroll_db"
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")


def parse_dsn(dsn):
    """Parse DSN PostgreSQL"""
    # Format: postgresql://user:password@host:port/database
    parts = dsn.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")

    return {
        "user": user_pass[0],
        "password": user_pass[1] if len(user_pass) > 1 else "",
        "host": host_port[0],
        "port": host_port[1] if len(host_port) > 1 else "5432",
        "database": host_db[1] if len(host_db) > 1 else "payroll_db",
    }


def find_pg_dump():
    """Chercher pg_dump dans les emplacements standards Windows"""
    possible_paths = [
        r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        r"C:\Program Files (x86)\PostgreSQL\17\bin\pg_dump.exe",
        r"C:\Program Files (x86)\PostgreSQL\16\bin\pg_dump.exe",
    ]

    # Chercher dans PATH
    try:
        result = subprocess.run(["where", "pg_dump"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except:
        pass

    # Chercher dans emplacements standards
    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def backup_with_pg_dump():
    """Backup avec pg_dump"""
    pg_dump_path = find_pg_dump()

    if not pg_dump_path:
        print("❌ pg_dump non trouvé")
        print("\nEmplacements cherchés:")
        for path in [
            r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
            r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        ]:
            print(f"  - {path}")
        print("\nSolutions:")
        print("  1. Installer PostgreSQL tools")
        print("  2. Ajouter PostgreSQL bin au PATH")
        print("  3. Utiliser backup SQL (option ci-dessous)")
        return False

    print(f"OK: pg_dump trouvé: {pg_dump_path}")

    # Créer répertoire backup
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Nom fichier backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"backup_pre_migration_{timestamp}.dump")

    # Parse DSN
    db_info = parse_dsn(DSN)

    # Commande pg_dump
    cmd = [
        pg_dump_path,
        "-h",
        db_info["host"],
        "-p",
        db_info["port"],
        "-U",
        db_info["user"],
        "-d",
        db_info["database"],
        "-F",
        "custom",
        "-f",
        backup_file,
    ]

    # Définir mot de passe - prefer PAYROLL_DB_PASSWORD env if present
    env = os.environ.copy()
    env["PGPASSWORD"] = os.getenv("PAYROLL_DB_PASSWORD") or db_info.get("password", "")

    print(f"\nCréation backup: {backup_file}")
    print("Ceci peut prendre quelques minutes...")

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
            size = os.path.getsize(backup_file) / (1024 * 1024)
            print(f"✅ Backup créé avec succès ({size:.2f} MB)")
            print(f"   Fichier: {backup_file}")
            return True
        else:
            print(f"❌ Erreur pg_dump:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def backup_with_sql():
    """Backup SQL alternatif (moins bon mais fonctionne)"""
    print("\n=== BACKUP SQL ALTERNATIF ===")
    print("Note: Moins complet que pg_dump, mais suffisant pour rollback migration")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.services.data_repo import DataRepository

    # Créer répertoire backup
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Nom fichier backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"backup_pre_migration_{timestamp}.sql")

    print(f"\nCréation backup SQL: {backup_file}")

    repo = DataRepository(DSN, min_size=1, max_size=2)

    with open(backup_file, "w", encoding="utf-8") as f:
        # Header
        f.write(
            "-- ============================================================================\n"
        )
        f.write(f"-- BACKUP PRE-MIGRATION - {timestamp}\n")
        f.write(
            "-- ============================================================================\n\n"
        )

        # Backup imported_payroll_master (table source)
        print("  Sauvegarde imported_payroll_master...")

        sql = "SELECT * FROM payroll.imported_payroll_master"
        result = repo.run_query(sql, {})

        f.write("-- TABLE: payroll.imported_payroll_master\n")
        f.write(f"-- Lignes: {len(result)}\n\n")

        # Générer INSERT statements (par batch de 100)
        if result:
            batch_size = 100
            for i in range(0, len(result), batch_size):
                batch = result[i : i + batch_size]

                f.write("INSERT INTO payroll.imported_payroll_master ")
                f.write(
                    '("matricule ", "employé ", "date de paie ", "categorie de paie ", "montant ") VALUES\n'
                )

                for idx, row in enumerate(batch):
                    matricule = str(row[0]).replace("'", "''") if row[0] else ""
                    employe = str(row[1]).replace("'", "''") if row[1] else ""
                    date_paie = str(row[2]) if row[2] else "NULL"
                    categorie = str(row[3]).replace("'", "''") if row[3] else ""
                    montant = str(row[4]) if row[4] else "0"

                    f.write(
                        f"  ('{matricule}', '{employe}', '{date_paie}', '{categorie}', {montant})"
                    )

                    if idx < len(batch) - 1:
                        f.write(",\n")
                    else:
                        f.write(";\n\n")

        f.write("-- FIN BACKUP\n")

    size = os.path.getsize(backup_file) / (1024 * 1024)
    print(f"✅ Backup SQL créé ({size:.2f} MB)")
    print(f"   Fichier: {backup_file}")

    repo.close()
    return True


def main():
    print("=" * 80)
    print("BACKUP BASE DE DONNÉES - PRÉ-MIGRATION")
    print("=" * 80)
    print()

    # Tentative 1: pg_dump (préféré)
    print("Option 1: Backup avec pg_dump (recommandé)...")
    success = backup_with_pg_dump()

    if not success:
        # Tentative 2: SQL alternatif
        print("\n" + "=" * 80)
        response = input("Voulez-vous créer un backup SQL alternatif ? (o/n): ")

        if response.lower() in ["o", "oui", "y", "yes"]:
            backup_with_sql()
        else:
            print("\nWARN:  ATTENTION: Aucun backup créé!")
            print("   Migration annulée par sécurité")
            return 1

    print("\n" + "=" * 80)
    print("✅ Backup terminé - Vous pouvez continuer la migration")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
