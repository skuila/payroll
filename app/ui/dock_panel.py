# ui/dock_panel.py — DockWidget PyQt6 : signal correct + policies souples
from PyQt6.QtWidgets import QDockWidget, QSizePolicy, QWidget
from PyQt6.QtCore import Qt, pyqtSignal


class DockPanel(QDockWidget):
    """Dock standardisé, sans tailles figées et avec un signal public stable."""

    floatingChanged2 = pyqtSignal(bool)  # relai public (True = flottant)

    def __init__(self, title: str, inner: QWidget, parent=None):
        super().__init__(title, parent)
        self.setObjectName(title.replace(" ", "_"))

        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        self.setWidget(inner)
        # Policies souples : éviter l'écrasement sans fixer des tailles rigides
        inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        # PyQt6 : utiliser topLevelChanged
        self.topLevelChanged.connect(self.floatingChanged2.emit)
