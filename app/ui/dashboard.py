# ui/dashboard.py
# ========================================
# OBSOLÈTE - Module déprécié (Tabler-only policy)
# ========================================
#
# ⚠️ CE MODULE N'EST PLUS UTILISÉ
#
# Raison: Le dashboard utilise maintenant Tabler pur (index.html) comme source de vérité.
#          Le centre PyQt avec KPI cards personnalisées est remplacé par le dashboard Tabler complet.
#          Les composants PyQt personnalisés qui imitent Tabler sont INTERDITS.
#
# Source de vérité: web/tabler/index.html
# Viewer à utiliser: ui/tabler_viewer.py (charge index.html par défaut)
#
# Migration:
#   Ancien: from ui.dashboard import Dashboard
#   Nouveau: from ui.tabler_viewer import TablerViewer
#
# Si vous avez besoin d'ajouter des KPI, les ajouter dans index.html uniquement.
#
# Date de dépréciation: 2025-10-13
# ========================================

from PyQt6.QtWidgets import QWidget


class Dashboard(QWidget):
    """
    OBSOLÈTE - Ne pas utiliser

    Remplacé par: TablerViewer qui charge web/tabler/index.html

    Migration:
        # Ancien code
        dashboard = Dashboard()

        # Nouveau code
        from ui.tabler_viewer import TablerViewer
        dashboard = TablerViewer(bridge=app_bridge)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        print("⚠️ DEPRECATED: Dashboard n'est plus utilisé (Tabler-only policy)")
        print("   Utiliser TablerViewer qui charge web/tabler/index.html à la place")
        print("   Migration: from ui.tabler_viewer import TablerViewer")
        # No-op: aucune UI créée

    def update_kpis(self, *args, **kwargs):
        """No-op - Module obsolète"""
        print("⚠️ DEPRECATED: Dashboard.update_kpis() ignoré (module obsolète)")
        print("   Utiliser window.AppBridge.updateKPI() dans le WebChannel à la place")
        pass

    def add_kpi_card(self, *args, **kwargs):
        """No-op - Module obsolète"""
        pass

    def clear_dashboard(self):
        """No-op - Module obsolète"""
        pass
