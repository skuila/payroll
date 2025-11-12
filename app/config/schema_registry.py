"""
Schema Registry pour la détection automatique des types de colonnes
Configuration YAML pour le moteur de détection
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_registry() -> Dict[str, Any]:
    """
    Charge la configuration du registre de schéma depuis le fichier YAML

    Returns:
        Dict: Configuration du registre avec types et paramètres UI
    """
    try:
        # Chemin vers le fichier de configuration
        registry_path = Path(__file__).parent / "schema_registry.yaml"

        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            # Configuration par défaut si le fichier n'existe pas
            return get_default_registry()

    except Exception as e:
        print(f"WARN: Erreur chargement registre: {e}")
        return get_default_registry()


def get_default_registry() -> Dict[str, Any]:
    """
    Retourne une configuration par défaut pour la détection de types

    Returns:
        Dict: Configuration par défaut
    """
    return {
        "types": {
            "matricule": {
                "visible": True,
                "priority": 90,
                "description": "Numéro d'identification employé",
                "detectors": [
                    {
                        "kind": "mask_dominance",
                        "weight": 1.0,
                        "allow": ["9", "A", "-"],
                        "min_len": 3,
                        "max_len": 20,
                        "coverage_min": 0.70,
                        "noise_max": 0.20,
                    },
                    {"kind": "all_numeric_ratio", "weight": 0.8, "min_ratio": 0.60},
                ],
                "validators": [{"kind": "uniqueness_hint", "min_uniques_ratio": 0.30}],
            },
            "nom": {
                "visible": True,
                "priority": 80,
                "description": "Nom de l'employé",
                "detectors": [
                    {"kind": "alpha_token_ratio", "weight": 1.0, "min_ratio": 0.80},
                    {
                        "kind": "high_entropy_alpha",
                        "weight": 0.8,
                        "min_entropy": 2.0,
                        "max_const_ratio": 0.30,
                    },
                    {
                        "kind": "avg_length_range",
                        "weight": 0.6,
                        "min_len": 2,
                        "max_len": 50,
                    },
                ],
                "validators": [{"kind": "high_entropy", "min_entropy": 1.5}],
            },
            "prenom": {
                "visible": True,
                "priority": 70,
                "description": "Prénom de l'employé",
                "detectors": [
                    {"kind": "alpha_token_ratio", "weight": 1.0, "min_ratio": 0.80},
                    {
                        "kind": "high_entropy_alpha",
                        "weight": 0.8,
                        "min_entropy": 1.8,
                        "max_const_ratio": 0.40,
                    },
                    {
                        "kind": "avg_length_range",
                        "weight": 0.6,
                        "min_len": 2,
                        "max_len": 30,
                    },
                ],
                "validators": [{"kind": "high_entropy", "min_entropy": 1.2}],
            },
            "pay_code": {
                "visible": True,
                "priority": 85,
                "description": "Code de paie",
                "detectors": [
                    {
                        "kind": "mask_dominance",
                        "weight": 1.0,
                        "allow": ["9", "A", "-"],
                        "min_len": 1,
                        "max_len": 10,
                        "coverage_min": 0.60,
                        "noise_max": 0.30,
                    },
                    {
                        "kind": "low_cardinality_hint",
                        "weight": 0.7,
                        "max_uniques_ratio": 0.20,
                    },
                ],
                "validators": [{"kind": "reject_constant", "max_const_ratio": 0.50}],
            },
            "amount_employee": {
                "visible": True,
                "priority": 95,
                "description": "Montant employé",
                "detectors": [
                    {"kind": "number_parse_ratio", "weight": 1.0, "min_ratio": 0.80},
                    {"kind": "contains_comma_ratio", "weight": 0.3, "min_ratio": 0.30},
                ],
                "validators": [],
            },
            "montant": {
                "visible": True,
                "priority": 95,
                "description": "Montant (alias)",
                "detectors": [
                    {"kind": "number_parse_ratio", "weight": 1.0, "min_ratio": 0.80},
                    {"kind": "contains_comma_ratio", "weight": 0.3, "min_ratio": 0.30},
                ],
                "validators": [],
            },
            "amount_employer": {
                "visible": True,
                "priority": 90,
                "description": "Montant employeur",
                "detectors": [
                    {"kind": "number_parse_ratio", "weight": 1.0, "min_ratio": 0.80},
                    {"kind": "contains_comma_ratio", "weight": 0.3, "min_ratio": 0.30},
                ],
                "validators": [],
            },
            "pay_date": {
                "visible": True,
                "priority": 100,
                "description": "Date de paie",
                "detectors": [
                    {"kind": "date_parse_ratio", "weight": 1.0, "min_ratio": 0.70}
                ],
                "validators": [],
            },
        },
        "ui": {
            "sample_rows": 200,
            "min_confidence_accept": 0.70,
            "min_confidence_warn": 0.50,
        },
    }


if __name__ == "__main__":
    # Test du module
    registry = load_registry()
    print(f"✅ Registre chargé: {len(registry['types'])} types définis")
    for type_name, type_config in registry["types"].items():
        print(f"  - {type_name}: {type_config['description']}")
