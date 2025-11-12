# ui/chart_bar.py
# ========================================
# OBSOLÈTE - Module déprécié (Tabler-only policy)
# ========================================
#
# ⚠️ CE MODULE N'EST PLUS UTILISÉ
#
# Raison: Le dashboard utilise maintenant Tabler pur (index.html) comme source de vérité.
#          Tous les charts/graphiques sont désormais rendus côté HTML via ApexCharts local.
#          Les composants PyQt personnalisés qui imitent Tabler sont INTERDITS.
#
# Source de vérité: web/tabler/index.html
# Charts utilisés: ApexCharts (dist/libs/apexcharts/dist/apexcharts.min.js)
#
# Si vous avez besoin d'un graphique, l'ajouter dans index.html uniquement.
#
# Date de dépréciation: 2025-10-13
# ========================================

from PyQt6.QtWidgets import QWidget


class ChartBar(QWidget):
    """
    OBSOLÈTE - Ne pas utiliser

    Remplacé par: Charts ApexCharts dans web/tabler/index.html
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        print("⚠️ DEPRECATED: ChartBar n'est plus utilisé (Tabler-only policy)")
        print("   Utiliser ApexCharts dans web/tabler/index.html à la place")
        # No-op: aucune UI créée

    def update_data(self, *args, **kwargs):
        """No-op - Module obsolète"""
        print("⚠️ DEPRECATED: ChartBar.update_data() ignoré (module obsolète)")
        pass

    def clear(self):
        """No-op - Module obsolète"""
        pass
