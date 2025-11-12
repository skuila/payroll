# config/theme_manager.py - Gestionnaire de thèmes pour l'application
"""
Gestionnaire de thèmes pour le Système de Contrôle de la Paie.
Permet de charger, lister et changer de thème dynamiquement.
"""
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings


class ThemeManager:
    """Gestionnaire centralisé des thèmes de l'application"""

    # Thèmes disponibles
    THEMES = {
        "saas_finance": {
            "name": "SaaS Finance Dark",
            "file": "style_saas_finance.qss",
            "description": "Thème sombre moderne avec accent turquoise",
            "preview_color": "#1DD1A1",
        },
        "saas_finance_high_contrast": {
            "name": "SaaS Finance High Contrast",
            "file": "style_saas_finance_high_contrast.qss",
            "description": "Thème sombre à contraste élevé pour meilleure lisibilité",
            "preview_color": "#00D9FF",
        },
        # Ajoutez d'autres thèmes ici
    }

    DEFAULT_THEME = "saas_finance"
    SETTINGS_KEY = "appearance/theme"

    def __init__(self, themes_dir: str):
        """
        Initialise le gestionnaire de thèmes.

        Args:
            themes_dir: Chemin vers le dossier contenant les fichiers QSS
        """
        self.themes_dir = themes_dir
        self.current_theme = None
        self.settings = QSettings()

    def get_available_themes(self) -> dict:
        """
        Retourne la liste des thèmes disponibles.

        Returns:
            dict: Dictionnaire des thèmes {id: {name, file, description, preview_color}}
        """
        available = {}
        for theme_id, theme_info in self.THEMES.items():
            theme_path = os.path.join(self.themes_dir, theme_info["file"])
            if os.path.exists(theme_path):
                available[theme_id] = theme_info
        return available

    def get_current_theme(self) -> str:
        """
        Retourne l'ID du thème actuellement actif.

        Returns:
            str: ID du thème actuel
        """
        if self.current_theme:
            return self.current_theme

        # Lire depuis les settings
        saved_theme = self.settings.value(self.SETTINGS_KEY, self.DEFAULT_THEME)
        return saved_theme if isinstance(saved_theme, str) else self.DEFAULT_THEME

    def set_theme(self, theme_id: str, app: QApplication = None) -> bool:
        """
        Applique un thème à l'application.

        Args:
            theme_id: ID du thème à appliquer
            app: Instance de QApplication (optionnel)

        Returns:
            bool: True si le thème a été appliqué avec succès
        """
        if theme_id not in self.THEMES:
            print(f"WARN:  Thème inconnu : {theme_id}")
            return False

        theme_info = self.THEMES[theme_id]
        theme_path = os.path.join(self.themes_dir, theme_info["file"])

        if not os.path.exists(theme_path):
            print(f"WARN:  Fichier thème introuvable : {theme_path}")
            return False

        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                qss_content = f.read()

            # Appliquer le thème
            if app is None:
                app = QApplication.instance()

            if app:
                app.setStyleSheet(qss_content)
                self.current_theme = theme_id

                # Sauvegarder dans les settings
                self.settings.setValue(self.SETTINGS_KEY, theme_id)

                print(f"OK: Thème chargé : {theme_info['name']}")
                return True
            else:
                print("WARN:  Aucune instance QApplication trouvée")
                return False

        except Exception as e:
            print(f"FAIL: Erreur chargement thème : {e}")
            return False

    def load_saved_theme(self, app: QApplication = None) -> bool:
        """
        Charge le thème sauvegardé dans les settings.

        Args:
            app: Instance de QApplication (optionnel)

        Returns:
            bool: True si le thème a été chargé avec succès
        """
        theme_id = self.get_current_theme()
        return self.set_theme(theme_id, app)

    def reset_theme(self, app: QApplication = None) -> bool:
        """
        Réinitialise au thème par défaut.

        Args:
            app: Instance de QApplication (optionnel)

        Returns:
            bool: True si le thème par défaut a été appliqué
        """
        return self.set_theme(self.DEFAULT_THEME, app)

    def get_theme_info(self, theme_id: str) -> dict | None:
        """
        Retourne les informations d'un thème.

        Args:
            theme_id: ID du thème

        Returns:
            dict | None: Informations du thème ou None si introuvable
        """
        return self.THEMES.get(theme_id)

    def export_theme_list(self) -> list[dict]:
        """
        Exporte la liste des thèmes disponibles pour affichage.

        Returns:
            list[dict]: Liste de dictionnaires avec id, name, description
        """
        themes_list = []
        for theme_id, theme_info in self.get_available_themes().items():
            themes_list.append(
                {
                    "id": theme_id,
                    "name": theme_info["name"],
                    "description": theme_info["description"],
                    "preview_color": theme_info["preview_color"],
                    "is_current": theme_id == self.get_current_theme(),
                }
            )
        return themes_list


# Instance globale du gestionnaire
_theme_manager = None


def get_theme_manager(themes_dir: str = None) -> ThemeManager:
    """
    Retourne l'instance globale du ThemeManager (singleton).

    Args:
        themes_dir: Chemin vers le dossier des thèmes (requis lors du premier appel)

    Returns:
        ThemeManager: Instance du gestionnaire de thèmes
    """
    global _theme_manager

    if _theme_manager is None:
        if themes_dir is None:
            # Chemin par défaut
            themes_dir = os.path.join(os.path.dirname(__file__), "..", "ui", "themes")
            themes_dir = os.path.abspath(themes_dir)

        _theme_manager = ThemeManager(themes_dir)

    return _theme_manager
