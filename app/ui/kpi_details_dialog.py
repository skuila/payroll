# ui/kpi_details_dialog.py
# ========================================
# OBSOLÈTE - Module déprécié (Tabler-only policy)
# ========================================
#
# ⚠️ CE MODULE N'EST PLUS UTILISÉ
#
# Raison: Le dashboard utilise maintenant Tabler pur (index.html) comme source de vérité.
#          Les dialogues de détails PyQt sont remplacés par des modals Tabler ou des pages dédiées.
#          Les composants PyQt personnalisés qui imitent Tabler sont INTERDITS.
#
# Source de vérité: web/tabler/index.html + period-report.html (pour rapports détaillés)
# Modals utilisés: Tabler modal component (data-bs-toggle="modal")
#
# Si vous avez besoin d'une modale de détails, utiliser les modals Tabler dans le HTML.
#
# Date de dépréciation: 2025-10-13
# ========================================

from PyQt6.QtWidgets import QDialog


class KpiDetailsDialog(QDialog):
    """
    OBSOLÈTE - Ne pas utiliser

    Remplacé par: Modals Tabler ou pages dédiées (ex: period-report.html)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        print("⚠️ DEPRECATED: KpiDetailsDialog n'est plus utilisé (Tabler-only policy)")
        print("   Utiliser les modals Tabler ou period-report.html à la place")
        # No-op: aucune UI créée

    def set_data(self, *args, **kwargs):
        """No-op - Module obsolète"""
        print("⚠️ DEPRECATED: KpiDetailsDialog.set_data() ignoré (module obsolète)")
        pass

    def show_details(self, *args, **kwargs):
        """No-op - Module obsolète"""
        pass
