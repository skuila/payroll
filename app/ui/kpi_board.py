# ui/kpi_board.py
# ========================================
# OBSOLÈTE - Module déprécié (Tabler-only policy)
# ========================================
#
# ⚠️ CE MODULE N'EST PLUS UTILISÉ
#
# Raison: Le dashboard utilise maintenant Tabler pur (index.html) comme source de vérité.
#          Le board KPI drag & drop PyQt est remplacé par la grille de cards Tabler.
#          Les composants PyQt personnalisés qui imitent Tabler sont INTERDITS.
#
# Source de vérité: web/tabler/index.html
# Layout utilisé: Tabler responsive grid (row row-deck row-cards)
#
# Si vous avez besoin de réorganiser les KPI, modifier la structure HTML dans index.html.
#
# Date de dépréciation: 2025-10-13
# ========================================

from PyQt6.QtWidgets import QListWidget


class KpiBoard(QListWidget):
    """
    OBSOLÈTE - Ne pas utiliser

    Remplacé par: Grille de cards Tabler dans web/tabler/index.html
    """

    def __init__(self, parent=None, settings_group="KPIBoard"):
        super().__init__(parent)
        print("⚠️ DEPRECATED: KpiBoard n'est plus utilisé (Tabler-only policy)")
        print("   Utiliser la grille Tabler dans web/tabler/index.html à la place")
        # No-op: aucune UI créée

    def register_kpi(self, *args, **kwargs):
        """No-op - Module obsolète"""
        print("⚠️ DEPRECATED: KpiBoard.register_kpi() ignoré (module obsolète)")
        pass

    def ensure_registered(self, *args, **kwargs):
        """No-op - Module obsolète"""
        pass

    def set_compact(self, *args, **kwargs):
        """No-op - Module obsolète"""
        pass
