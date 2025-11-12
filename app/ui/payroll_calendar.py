# ui/payroll_calendar.py - Calendrier personnalisé pour la paie (PyQt6)
from __future__ import annotations
from PyQt6.QtWidgets import QCalendarWidget, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QDate


class PayrollCalendar(QWidget):
    """
    Calendrier personnalisé pour la paie.
    - Grille visible
    - Pas de numéros de semaine
    - Signal clicked(QDate) pour ouvrir l'analyse de paie
    """

    # Signal émis quand une date est cliquée
    dateClicked = pyqtSignal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PayrollCalendar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Titre (stylé par QSS)
        self.title_label = QLabel("📅 Calendrier de paie")
        self.title_label.setObjectName("CalendarTitle")
        layout.addWidget(self.title_label)

        # Widget calendrier
        self.calendar = QCalendarWidget(self)
        self.calendar.setObjectName("CalendarWidget")

        # Configuration selon les spécifications
        self.calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.setGridVisible(True)

        # Personnalisation visuelle
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setNavigationBarVisible(True)

        # Connecter le signal
        self.calendar.clicked.connect(self._on_date_clicked)

        layout.addWidget(self.calendar)

        # Le style est appliqué par le QSS global (ui/themes/style_saas_finance.qss)

    def _on_date_clicked(self, date: QDate):
        """Gère le clic sur une date"""
        # Émettre le signal
        self.dateClicked.emit(date)

        # Feedback visuel (optionnel)
        self.title_label.setText(
            f"📅 Calendrier de paie - {date.toString('dd/MM/yyyy')}"
        )

    def set_highlighted_dates(self, dates: list[QDate]):
        """
        Met en évidence des dates spécifiques (ex: dates de paie).

        Args:
            dates: Liste de QDate à mettre en évidence
        """
        from PyQt6.QtGui import QTextCharFormat, QColor

        # Format pour les dates de paie
        payroll_format = QTextCharFormat()
        payroll_format.setBackground(
            QColor(29, 209, 161, 80)
        )  # Turquoise semi-transparent
        payroll_format.setForeground(QColor(255, 255, 255))
        payroll_format.setFontWeight(700)

        # Appliquer le format à chaque date
        for date in dates:
            self.calendar.setDateTextFormat(date, payroll_format)

    def clear_highlighted_dates(self):
        """Efface toutes les mises en évidence"""
        from PyQt6.QtGui import QTextCharFormat

        default_format = QTextCharFormat()

        # Parcourir toutes les dates de l'année courante
        current_date = QDate.currentDate()
        year = current_date.year()

        for month in range(1, 13):
            days_in_month = QDate(year, month, 1).daysInMonth()
            for day in range(1, days_in_month + 1):
                date = QDate(year, month, day)
                self.calendar.setDateTextFormat(date, default_format)

    def get_selected_date(self) -> QDate:
        """Retourne la date actuellement sélectionnée"""
        return self.calendar.selectedDate()

    def set_selected_date(self, date: QDate):
        """Définit la date sélectionnée"""
        self.calendar.setSelectedDate(date)
