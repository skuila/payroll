# ui/dashboard_grid.py
# ========================================
# OBSOLÈTE - Module déprécié (Tabler-only policy)
# ========================================
#
# ⚠️ CE MODULE N'EST PLUS UTILISÉ
#
# Raison: Le dashboard utilise maintenant Tabler pur (index.html) comme source de vérité.
#          La grille PyQt personnalisée est remplacée par le layout Tabler responsive.
#          Les composants PyQt personnalisés qui imitent Tabler sont INTERDITS.
#
# Source de vérité: web/tabler/index.html
# Layout utilisé: Tabler grid system (row row-deck row-cards + col-sm-6 col-lg-3)
#
# Si vous avez besoin de modifier la grille, éditer index.html directement.
#
# Date de dépréciation: 2025-10-13
# ========================================

from PyQt6.QtWidgets import QWidget


class DashboardGrid(QWidget):
    """
    OBSOLÈTE - Ne pas utiliser

    Remplacé par: Tabler grid system dans web/tabler/index.html
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        print("⚠️ DEPRECATED: DashboardGrid n'est plus utilisé (Tabler-only policy)")
        print("   Utiliser le grid Tabler dans web/tabler/index.html à la place")
        # No-op: aucune UI créée

    def add_widget(self, *args, **kwargs):
        """No-op - Module obsolète"""
        print("⚠️ DEPRECATED: DashboardGrid.add_widget() ignoré (module obsolète)")
        pass

    def remove_widget(self, *args, **kwargs):
        """No-op - Module obsolète"""
        pass

    def clear_widgets(self):
        """No-op - Module obsolète"""
        pass
