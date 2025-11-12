# ui/sidebar.py — Barre latérale PyQt6 (LEGACY - Tabler sidebar est maintenant la source de vérité)
# ========================================
# ⚠️ NOTE IMPORTANTE - Tabler-only policy
# ========================================
#
# Cette sidebar PyQt est maintenant LEGACY.
#
# Source de vérité pour la navigation: web/tabler/index.html (sidebar Tabler native)
#
# Ce module reste disponible pour compatibilité avec d'anciens wrappers PyQt,
# mais toute navigation dans l'app doit se faire via le sidebar Tabler HTML.
#
# Si vous ajoutez un nouveau lien de navigation:
#   1. L'ajouter dans web/tabler/index.html (sidebar Tabler)
#   2. Ne PAS créer de nouveau bouton ici
#
# Date de dépréciation partielle: 2025-10-13
# ========================================

from __future__ import annotations
from PyQt6.QtCore import Qt, QSize, QSettings, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QLabel,
)
from PyQt6.QtGui import QCursor


class Sidebar(QWidget):
    """
    LEGACY - Barre latérale PyQt6

    ⚠️ Cette sidebar est maintenant LEGACY. Utiliser le sidebar Tabler (index.html) à la place.

    Conservé pour compatibilité avec anciens wrappers PyQt uniquement.
    Toute nouvelle navigation doit être ajoutée dans web/tabler/index.html.

    Fonctionnalités (legacy):
    - États: ouvert, réduit (icônes seules), épinglé
    - Ouverture auto au survol
    - Réduction auto après inactivité (si non épinglé)
    - Infobulles au survol en mode réduit
    - Persistance de l'état dans QSettings
    """

    toggled = pyqtSignal(bool)  # True si étendu, False si réduit

    SETTINGS_KEY_EXPANDED = "Sidebar/expanded"
    SETTINGS_KEY_PINNED = "Sidebar/pinned"

    WIDTH_EXPANDED = 220
    WIDTH_COLLAPSED = 64
    AUTO_COLLAPSE_DELAY = 3000  # ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = True
        self._pinned = False
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._on_leave_timeout)

        self.setObjectName("Sidebar")
        self.setAutoFillBackground(True)
        self.setMinimumWidth(self.WIDTH_COLLAPSED)
        self.setMaximumWidth(self.WIDTH_EXPANDED)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Bouton toggle (réduire/étendre)
        self.btn_toggle = QToolButton(self)
        self.btn_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_toggle.setText("☰")
        self.btn_toggle.setToolTip("Réduire/étendre la barre (Ctrl+B)")
        self.btn_toggle.setShortcut("Ctrl+B")
        self.btn_toggle.clicked.connect(self._toggle)
        self.btn_toggle.setMinimumSize(QSize(40, 40))
        self.btn_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        root.addWidget(self.btn_toggle, 0, Qt.AlignmentFlag.AlignLeft)

        # Bouton épingler
        self.btn_pin = QToolButton(self)
        self.btn_pin.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_pin.setCheckable(True)
        self.btn_pin.setText("📌")
        self.btn_pin.setToolTip("Épingler/Détacher la barre")
        self.btn_pin.toggled.connect(self._on_pin_toggled)
        self.btn_pin.setMinimumSize(QSize(40, 40))
        self.btn_pin.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        root.addWidget(self.btn_pin, 0, Qt.AlignmentFlag.AlignLeft)

        root.addSpacing(10)

        # Titre (stylé par QSS)
        self.lbl_title = QLabel("Navigation", self)
        self.lbl_title.setObjectName("SidebarTitle")
        root.addWidget(self.lbl_title, 0)

        root.addSpacing(10)

        # Boutons de navigation (LEGACY - voir web/tabler/index.html pour navigation actuelle)
        # Note: Ces boutons sont génériques et doivent être connectés par le parent
        # La navigation réelle se fait maintenant via le sidebar Tabler dans index.html

        self.btn_home = self._create_nav_button(
            "🏠", "Accueil", "Aller au dashboard Tabler"
        )
        root.addWidget(self.btn_home, 0)

        # OBSOLÈTE: btn_analysis (KPI dashboard PyQt custom)
        # Utiliser index.html (dashboard Tabler) à la place
        # self.btn_analysis = self._create_nav_button("📊", "Analyse", "Outils d'analyse")
        # root.addWidget(self.btn_analysis, 0)

        self.btn_import = self._create_nav_button(
            "📥", "Importer", "Importer des données"
        )
        root.addWidget(self.btn_import, 0)

        self.btn_employees = self._create_nav_button(
            "👥", "Employés", "Liste des employés"
        )
        root.addWidget(self.btn_employees, 0)

        # OBSOLÈTE: btn_audit (panel PyQt custom)
        # Utiliser une page Tabler dédiée si nécessaire
        # self.btn_audit = self._create_nav_button("🔍", "Audit", "Audit de paie")
        # root.addWidget(self.btn_audit, 0)

        # OBSOLÈTE: btn_reports (générateur PyQt custom)
        # Utiliser une page Tabler dédiée si nécessaire
        # self.btn_reports = self._create_nav_button("📄", "Rapports", "Générer des rapports")
        # root.addWidget(self.btn_reports, 0)

        # OBSOLÈTE: btn_table (table PyQt custom)
        # La table est maintenant intégrée dans index.html (via WebChannel)
        # self.btn_table = self._create_nav_button("📋", "Table", "Afficher/masquer la table")
        # root.addWidget(self.btn_table, 0)

        root.addStretch(1)

        # Bouton paramètres (en bas)
        self.btn_settings = self._create_nav_button(
            "⚙️", "Paramètres", "Paramètres de l'application"
        )
        root.addWidget(self.btn_settings, 0)

        # Restaurer l'état sauvegardé
        self._restore_state()
        self._apply_mode()

    def _create_nav_button(
        self, icon_text: str, label: str, tooltip: str
    ) -> QPushButton:
        """Crée un bouton de navigation avec icône et label."""
        btn = QPushButton(f"{icon_text}  {label}", self)
        btn.setToolTip(tooltip)
        btn.setMinimumHeight(40)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setProperty("nav_icon", icon_text)
        btn.setProperty("nav_label", label)
        return btn

    def _toggle(self):
        """Bascule entre modes étendu/réduit."""
        self._expanded = not self._expanded
        self._apply_mode()
        self._save_state()
        self.toggled.emit(self._expanded)

    def _on_pin_toggled(self, checked: bool):
        """Gère l'épinglage/détachement de la barre."""
        self._pinned = checked
        self._save_state()

        if checked:
            self.btn_pin.setToolTip("Détacher la barre (auto-masquage désactivé)")
            # Si épinglé, forcer l'expansion
            if not self._expanded:
                self._expanded = True
                self._apply_mode()
                self.toggled.emit(True)
        else:
            self.btn_pin.setToolTip("Épingler la barre")

    def _apply_mode(self):
        """Applique le mode visuel (étendu ou réduit)."""
        if self._expanded:
            self.setFixedWidth(self.WIDTH_EXPANDED)
            self.lbl_title.setVisible(True)
            self.btn_pin.setVisible(True)

            # Afficher les labels des boutons
            for btn in self.findChildren(QPushButton):
                if btn not in (self.btn_toggle, self.btn_pin):
                    icon = btn.property("nav_icon")
                    label = btn.property("nav_label")
                    if icon and label:
                        btn.setText(f"{icon}  {label}")

            self.btn_toggle.setToolTip("Réduire la barre (Ctrl+B)")
        else:
            self.setFixedWidth(self.WIDTH_COLLAPSED)
            self.lbl_title.setVisible(False)
            self.btn_pin.setVisible(False)

            # Afficher seulement les icônes
            for btn in self.findChildren(QPushButton):
                if btn not in (self.btn_toggle, self.btn_pin):
                    icon = btn.property("nav_icon")
                    if icon:
                        btn.setText(icon)

            self.btn_toggle.setToolTip("Étendre la barre (Ctrl+B)")

    def _save_state(self):
        """Sauvegarde l'état dans QSettings."""
        s = QSettings()
        s.setValue(self.SETTINGS_KEY_EXPANDED, self._expanded)
        s.setValue(self.SETTINGS_KEY_PINNED, self._pinned)

    def _restore_state(self):
        """Restaure l'état depuis QSettings."""
        s = QSettings()

        expanded_val = s.value(self.SETTINGS_KEY_EXPANDED, True)
        self._expanded = (
            bool(expanded_val)
            if isinstance(expanded_val, bool)
            else str(expanded_val).lower() != "false"
        )

        pinned_val = s.value(self.SETTINGS_KEY_PINNED, False)
        self._pinned = (
            bool(pinned_val)
            if isinstance(pinned_val, bool)
            else str(pinned_val).lower() == "true"
        )

        self.btn_pin.setChecked(self._pinned)

    def enterEvent(self, event):
        """Ouverture auto au survol (si non épinglé et réduit)."""
        super().enterEvent(event)
        self._hover_timer.stop()

        if not self._pinned and not self._expanded:
            self._expanded = True
            self._apply_mode()
            self.toggled.emit(True)

    def leaveEvent(self, event):
        """Démarre le timer de réduction auto (si non épinglé)."""
        super().leaveEvent(event)

        if not self._pinned and self._expanded:
            self._hover_timer.start(self.AUTO_COLLAPSE_DELAY)

    def _on_leave_timeout(self):
        """Réduit la barre après inactivité (si non épinglé)."""
        if not self._pinned and self._expanded:
            # Vérifier que la souris n'est plus au-dessus
            if not self.underMouse():
                self._expanded = False
                self._apply_mode()
                self.toggled.emit(False)

    def sizeHint(self) -> QSize:
        """Taille suggérée."""
        width = self.WIDTH_EXPANDED if self._expanded else self.WIDTH_COLLAPSED
        return QSize(width, 600)
