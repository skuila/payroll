# config/config_manager.py — ajoute stratégie de calcul du Net (par colonne / par catégorie)
import json, os
from typing import Dict, Any

DEFAULT_SETTINGS = {
    "input_format": "no_header",  # "no_header" | "has_header"
    "locale": "FR",  # "FR" | "CA" | "US"
    "column_mapping_by_index": {
        "4": "Titre d’emploi",
        "6": "Matricule",
        "7": "Nom et prénom",
        "5": "Date de paie",
        "8": "Catégorie de paie",
        "9": "Code Paie",
        "10": "Description",
        "11": "Poste budgétaire",
        "12": "Description budgétaire",
        "13": "Montant",
        "14": "Montant Employeur",
        "13.1": "Montant Employé",
    },
    "column_mapping_by_name": {},
    # Nouveau bloc 'net' : paramétrage du calcul
    "net": {
        "strategy": "as_is",  # "as_is" | "by_category"
        "amount_column": "Montant",  # "Montant" | "Montant Employé" | "Montant Employeur"
        "default_effect": -1,  # effet si catégorie inconnue
        "effects": {  # catégorie canonique -> effet (+1/0/-1)
            "gains": 1,
            "assurance": -1,
            "déductions légales": -1,
            "avantages imposables": 0,
        },
        "aliases": {  # alias (source) -> catégorie canonique
            "syndicats": "déductions légales",
            "impôts": "déductions légales",
            "cotisations": "déductions légales",
            "assurance": "assurance",
        },
    },
}

SETTINGS_PATH = os.path.join("config", "settings.json")


def ensure_dirs():
    os.makedirs("config", exist_ok=True)


def load_settings() -> Dict[str, Any]:
    ensure_dirs()
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return DEFAULT_SETTINGS.copy()
    # shallow merge defaults
    merged = DEFAULT_SETTINGS.copy()
    for k, v in data.items():
        merged[k] = v
    # ensure 'net' defaults merged too
    if "net" not in merged:
        merged["net"] = DEFAULT_SETTINGS["net"]
    else:
        net = DEFAULT_SETTINGS["net"].copy()
        net.update(merged["net"] or {})
        merged["net"] = net
    return merged


def save_settings(data: Dict[str, Any]) -> None:
    ensure_dirs()
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Configuration centralisée des credentials DB -----------------
def get_db_password() -> str:
    """Retourne le mot de passe DB centralisé.

    Ordre de priorité :
      1. variable d'environnement PAYROLL_DB_PASSWORD
      2. valeur par défaut demandée par l'équipe (ici: 'aq456*456')
    """
    return os.getenv("PAYROLL_DB_PASSWORD", "aq456*456")


def get_dsn() -> str:
    """Construit et retourne un DSN PostgreSQL utilisable par psycopg/SQLAlchemy.

    - Si PAYROLL_DSN est défini, il est retourné sans modification.
    - Sinon on construit le DSN à partir des variables :
        PAYROLL_DB_USER, PAYROLL_DB_HOST, PAYROLL_DB_PORT, PAYROLL_DB_NAME
      Le mot de passe utilisé vient de `get_db_password()`.
    """
    dsn = os.getenv("PAYROLL_DSN") or os.getenv("DATABASE_URL")
    if dsn:
        return dsn

    user = os.getenv("PAYROLL_DB_USER", "payroll_app")
    host = os.getenv("PAYROLL_DB_HOST", "localhost")
    port = os.getenv("PAYROLL_DB_PORT", "5432")
    name = os.getenv("PAYROLL_DB_NAME", "payroll_db")
    pwd = get_db_password()
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


def get_db_conn_params() -> dict:
    """Retourne un dict minimal utilisable pour se connecter via psycopg.
    Exemple : psycopg.connect(**get_db_conn_params())
    """
    dsn = get_dsn()
    # si l'app utilise psycopg connect with a DSN string, retourne le param 'dsn'
    return {"dsn": dsn}
