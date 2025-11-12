# ui/kpi_card.py
# ========================================
# OBSOLÈTE - Module déprécié (Tabler-only policy)
# ========================================
#
# ⚠️ CE MODULE N'EST PLUS UTILISÉ
#
# Raison: Le dashboard utilise maintenant Tabler pur (index.html) comme source de vérité.
#          Tous les KPI cards sont désormais rendus côté HTML avec composants Tabler officiels.
#          Les composants PyQt personnalisés qui imitent Tabler sont INTERDITS.
#
# Source de vérité: web/tabler/index.html
# KPI Cards utilisées: Tabler cards natives (lignes 476-581 de index.html)
#
# IDs KPI disponibles:
#   - kpi-masse : Masse salariale
#   - kpi-net : Net moyen
#   - kpi-deductions : Déductions
#   - kpi-employes : Employés actifs
#
# Mise à jour via: window.AppBridge.updateKPI({...}) dans app_bridge.js
#
# Si vous avez besoin d'une nouvelle carte KPI, l'ajouter dans index.html uniquement.
#
# Date de dépréciation: 2025-10-13
# ========================================

from PyQt6.QtWidgets import QWidget


class KpiCard(QWidget):
    """
    OBSOLÈTE - Ne pas utiliser

    Remplacé par: Tabler cards natives dans web/tabler/index.html
    Mise à jour via: window.AppBridge.updateKPI() (app_bridge.js)
    """

    def __init__(self, parent=None, title="", value="", **kwargs):
        super().__init__(parent)
        print("⚠️ DEPRECATED: KpiCard n'est plus utilisé (Tabler-only policy)")
        print("   Utiliser les cards Tabler dans web/tabler/index.html à la place")
        print("   Mise à jour via: window.AppBridge.updateKPI({...})")
        # No-op: aucune UI créée

    def update_value(self, *args, **kwargs):
        """No-op - Module obsolète"""
        print("⚠️ DEPRECATED: KpiCard.update_value() ignoré (module obsolète)")
        pass

    def set_title(self, *args, **kwargs):
        """No-op - Module obsolète"""
        pass

    def set_value(self, *args, **kwargs):
        """No-op - Module obsolète"""
        pass
