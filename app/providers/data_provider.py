# providers/data_provider.py
"""Interface abstraite pour les providers de données de paie"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AbstractDataProvider(ABC):
    """
    Interface pour l'accès aux données de paie.

    Implémentations:
    - PostgresProvider: Accès PostgreSQL avec pool de connexions
    - SqliteProvider: Accès SQLite (fallback lecture seule)
    """

    @abstractmethod
    def get_kpis(self, pay_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Retourne les KPI pour une date de paie donnée.

        Args:
            pay_date: Date de paie exacte au format YYYY-MM-DD (ex: "2025-08-28"), None = dernière date de paie

        Returns:
            Dict avec clés:
            - masse_salariale (float): Total des salaires bruts
            - nb_employes (int): Nombre d'employés distincts
            - deductions (float): Total des déductions (négatif)
            - net_moyen (float): Salaire net moyen
            - pay_date (str): Date de paie effective (YYYY-MM-DD)
            - period (str): Alias pour pay_date (compatibilité)
        """
        pass

    @abstractmethod
    def get_table(
        self, offset: int = 0, limit: int = 50, filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Retourne les données de paie paginées.

        Args:
            offset: Décalage pour pagination (0-based)
            limit: Nombre maximum de lignes à retourner (défaut: 50, max: 100)
            filters: Filtres optionnels (dict avec clés: period, matricule, categorie)

        Returns:
            Dict avec clés:
            - rows (List[Dict]): Liste des lignes avec colonnes:
              * matricule (str)
              * nom (str)
              * date_paie (str) format YYYY-MM-DD
              * categorie (str)
              * montant (float)
            - total (int): Nombre total de lignes (pour pagination)
            - offset (int): Offset effectif
            - limit (int): Limit effectif
        """
        pass

    @abstractmethod
    def close(self):
        """Ferme les connexions et libère les ressources"""
        pass
