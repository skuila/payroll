# ui/homepage.py - Page d'accueil EXACTEMENT comme Behance (Grid 3x3)
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QCalendarWidget,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QLocale, QSize
from .data_provider import PayrollDataProvider
from .kpi_card import KpiCard
from .kpi_board import KpiBoard
from .dashboard_grid import DashboardGrid

LOC = QLocale(QLocale.Language.French, QLocale.Country.Canada)


def _fmt_money(x: float) -> str:
    """Formate un montant en devise canadienne"""
    try:
        return f"{LOC.toString(float(x), 'f', 2)} $"
    except Exception:
        return f"{x:.2f} $"


class HomePage(QWidget):
    """
    Page d'accueil EXACTEMENT comme Behance :
    - Bande KPI en haut (4 cartes)
    - Grid 3x3 : 8 cartes principales
    - Espacement généreux entre toutes les cartes
    - Design professionnel avec bordures visibles
    """

    payrollDateSelected = pyqtSignal(QDate)

    def __init__(self, provider: PayrollDataProvider, parent=None):
        super().__init__(parent)
        self.setObjectName("HomePage")
        self.provider = provider

        # Layout principal avec QScrollArea pour rendre toutes les cartes visibles
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Créer un QScrollArea pour permettre le scroll vertical
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setObjectName("HomePageScroll")

        # Container interne scrollable
        scroll_container = QWidget()
        scroll_container.setObjectName("HomePage")
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setSpacing(24)  # Espacement généreux comme Behance
        scroll_layout.setContentsMargins(20, 20, 20, 20)

        # ========== BANDE KPI (EN HAUT) ==========
        self.kpi_section = self._create_kpi_section()
        scroll_layout.addWidget(self.kpi_section, 0)

        # ========== GRID 3x3 (8 CARTES COMME BEHANCE) ==========
        self.grid_section = self._create_grid_section()
        scroll_layout.addWidget(self.grid_section, 1)

        # Ajouter le container au scroll area
        scroll_area.setWidget(scroll_container)
        main_layout.addWidget(scroll_area)

    def _create_kpi_section(self):
        """Crée la bande KPI comme Behance"""
        kpi_frame = QFrame()
        kpi_frame.setObjectName("KPISection")
        kpi_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        kpi_layout = QVBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        kpi_layout.setSpacing(0)

        # Container pour les KPI avec drag & drop
        self.kpi_board = KpiBoard(kpi_frame, "HomePageKPI")
        self.kpi_board.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.kpi_board.setFixedHeight(160)  # Hauteur fixe pour la bande

        # Charger et enregistrer les KPI avec possibilité de réorganisation
        self.kpi_cards = []

        try:
            kpi_data = self.provider.get_advanced_kpis()

            if kpi_data:
                for i, kpi in enumerate(kpi_data[:4]):
                    kpi_card = KpiCard(
                        kpi_id=kpi["id"],
                        title=kpi["title"],
                        value_text=kpi["formatted_value"],
                        delta_text=(
                            f"{kpi['delta']:+.1f}%" if kpi["delta"] != 0 else "--"
                        ),
                        trend=kpi["trend"],
                        alert_level=kpi["alert_level"],
                        alert_message=kpi["alert_message"],
                        sparkline_data=kpi["sparkline_data"],
                    )

                    kpi_card.clicked.connect(self._on_kpi_clicked)
                    self.kpi_cards.append(kpi_card)
            else:
                self._create_default_kpis()

        except Exception as e:
            print(f"Erreur chargement KPI: {e}")
            self._create_default_kpis()

        # Enregistrer tous les KPI dans le board avec drag & drop
        kpi_mapping = {card.kpi_id: card for card in self.kpi_cards}
        default_visible = [card.kpi_id for card in self.kpi_cards]
        self.kpi_board.ensure_registered(kpi_mapping, defaults_visible=default_visible)

        kpi_layout.addWidget(self.kpi_board)
        return kpi_frame

    def _create_default_kpis(self):
        """KPI par défaut"""
        default_kpis = [
            {"id": "masse_salariale", "title": "Masse salariale", "value": "6.8M $"},
            {"id": "salaire_net", "title": "Salaire net", "value": "3.7M $"},
            {"id": "deductions", "title": "Déductions", "value": "3.0M $"},
            {"id": "effectifs", "title": "Effectifs", "value": "530"},
        ]

        for kpi in default_kpis:
            kpi_card = KpiCard(
                kpi_id=kpi["id"],
                title=kpi["title"],
                value_text=kpi["value"],
                delta_text="--",
                trend="neutral",
                alert_level="none",
                alert_message="",
                sparkline_data=[],
            )
            kpi_card.clicked.connect(self._on_kpi_clicked)
            self.kpi_cards.append(kpi_card)

    def _create_grid_section(self):
        """Crée le grid avec drag & drop et redimensionnement"""
        # Utiliser DashboardGrid pour gestion avancée
        self.dashboard_grid = DashboardGrid(parent=self, settings_key="homepage/layout")

        # Créer toutes les cartes
        self._create_all_cards()

        # Layout par défaut (3 colonnes)
        default_layout = {
            "transactions": (0, 0, 2, 1),  # Grande carte à gauche (2 lignes)
            "reports": (0, 1, 1, 1),  # Col 1, ligne 0
            "scheduler": (0, 2, 1, 1),  # Col 2, ligne 0
            "credit_card": (1, 1, 1, 1),  # Col 1, ligne 1
            "investment": (1, 2, 1, 1),  # Col 2, ligne 1
            "retirement": (2, 0, 1, 1),  # Ligne 2, col 0
            "business": (2, 1, 1, 1),  # Ligne 2, col 1
            "budget": (2, 2, 1, 1),  # Ligne 2, col 2
        }

        # Ajouter les cartes au grid
        for card_id, (row, col, rowSpan, colSpan) in default_layout.items():
            if card_id in self.cards:
                self.dashboard_grid.add_card(
                    card_id, self.cards[card_id], row, col, rowSpan, colSpan
                )

        # Charger le layout sauvegardé
        self.dashboard_grid.load_layout(default_layout)

        return self.dashboard_grid

    def _create_all_cards(self):
        """Crée toutes les cartes du dashboard et remplit self.cards"""
        cards_data = [
            ("transactions", "All Transaction", self._create_transactions_card),
            ("reports", "Reports", self._create_reports_card),
            ("scheduler", "Scheduler", self._create_scheduler_card),
            ("retirement", "Retirement", self._create_retirement_card),
            ("credit_card", "Credit Card", self._create_credit_card),
            ("investment", "Investment", self._create_investment_card),
            ("business", "Business", self._create_business_card),
            ("budget", "Budget", self._create_budget_card),
        ]

        self.cards = {}
        for card_id, title, create_func in cards_data:
            card = create_func()
            card.setProperty("card_id", card_id)
            card.setProperty("card_title", title)
            self.cards[card_id] = card

    def set_edit_mode(self, enabled: bool):
        """Active/désactive le mode édition du dashboard"""
        if hasattr(self, "dashboard_grid"):
            self.dashboard_grid.set_edit_mode(enabled)

    def _create_card_frame(self, title: str, object_name: str = "HomeCard"):
        """Crée un cadre de carte comme Behance"""
        card = QFrame()
        card.setObjectName(object_name)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card.setMinimumSize(240, 180)  # Taille plus flexible
        # PAS de setMaximumSize pour permettre l'extension selon rowSpan/colSpan

        # Définir les fonctions sizeHint pour l'ajustement automatique
        def sizeHint():
            return QSize(280, 200)

        def minimumSizeHint():
            return QSize(240, 180)

        card.sizeHint = sizeHint
        card.minimumSizeHint = minimumSizeHint

        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Titre avec bouton +
        title_layout = QHBoxLayout()

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        plus_btn = QPushButton("+")
        plus_btn.setObjectName("PlusButton")
        plus_btn.setFixedSize(24, 24)
        title_layout.addWidget(plus_btn)

        layout.addLayout(title_layout)

        return card, layout

    def _create_transactions_card(self):
        """Carte All Transactions - comme Behance"""
        card, layout = self._create_card_frame("All Transaction", "TransactionsCard")

        # Liste des transactions comme dans l'image
        transactions = [
            ("Dropbox", "$3,500"),
            ("Starbucks", "$120"),
            ("McDonald's", "$45"),
            ("Netflix", "$15"),
            ("Spotify", "$10"),
        ]

        for icon, amount in transactions:
            trans_layout = QHBoxLayout()

            # Icône (simulée par emoji)
            icon_label = QLabel(
                "📦" if "Dropbox" in icon else "☕" if "Starbucks" in icon else "🍔"
            )
            icon_label.setFixedSize(24, 24)
            trans_layout.addWidget(icon_label)

            # Nom
            name_label = QLabel(icon)
            name_label.setObjectName("TransactionName")
            trans_layout.addWidget(name_label)

            trans_layout.addStretch()

            # Montant
            amount_label = QLabel(amount)
            amount_label.setObjectName("TransactionAmount")
            trans_layout.addWidget(amount_label)

            layout.addLayout(trans_layout)

        return card

    def _create_reports_card(self):
        """Carte Reports - comme Behance"""
        card, layout = self._create_card_frame("Reports", "ReportsCard")

        # Stats financières comme dans l'image
        stats_layout = QHBoxLayout()

        # Worth
        worth_layout = QVBoxLayout()
        worth_label = QLabel("Worth")
        worth_label.setObjectName("CardSubtitle")
        worth_layout.addWidget(worth_label)

        self.worth_value = QLabel("$14,455")
        self.worth_value.setObjectName("ValueSuccess")
        worth_layout.addWidget(self.worth_value)
        stats_layout.addLayout(worth_layout)

        # Spent
        spent_layout = QVBoxLayout()
        spent_label = QLabel("Spent")
        spent_label.setObjectName("CardSubtitle")
        spent_layout.addWidget(spent_label)

        self.spent_value = QLabel("$10,234")
        self.spent_value.setObjectName("ValueDanger")
        spent_layout.addWidget(self.spent_value)
        stats_layout.addLayout(spent_layout)

        # Earn by Category
        earn_layout = QVBoxLayout()
        earn_label = QLabel("Earn by Category")
        earn_label.setObjectName("CardSubtitle")
        earn_layout.addWidget(earn_label)

        self.earn_value = QLabel("$4,653")
        self.earn_value.setObjectName("ValueInfo")
        earn_layout.addWidget(self.earn_value)
        stats_layout.addLayout(earn_layout)

        layout.addLayout(stats_layout)

        # Graphique simple (simulé par des barres)
        chart_widget = self._create_simple_chart()
        layout.addWidget(chart_widget)

        return card

    def _create_simple_chart(self):
        """Crée un graphique simple comme Behance"""
        chart_widget = QWidget()
        chart_widget.setFixedHeight(60)
        chart_widget.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:1, x2:0, y2:0,
                    stop:0 #1DD1A1, stop:0.3 #1DD1A1, stop:1 transparent);
                border-radius: 8px;
            }
        """
        )
        return chart_widget

    def _create_scheduler_card(self):
        """Carte Scheduler - comme Behance"""
        card, layout = self._create_card_frame("Scheduler", "SchedulerCard")

        # Calendrier simple comme dans l'image
        calendar = QCalendarWidget()
        calendar.setMaximumDate(QDate.currentDate().addDays(365))
        calendar.setMinimumDate(QDate.currentDate().addDays(-365))
        calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        calendar.setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        calendar.setGridVisible(True)
        layout.addWidget(calendar)

        return card

    def _create_retirement_card(self):
        """Carte Retirement - comme Behance"""
        card, layout = self._create_card_frame("Retirement", "RetirementCard")

        # Today Deposit
        deposit_layout = QVBoxLayout()
        deposit_label = QLabel("Today Deposit")
        deposit_label.setObjectName("CardSubtitle")
        deposit_layout.addWidget(deposit_label)

        self.deposit_value = QLabel("$100")
        self.deposit_value.setObjectName("ValueInfo")
        deposit_layout.addWidget(self.deposit_value)
        layout.addLayout(deposit_layout)

        # Project Value
        project_layout = QVBoxLayout()
        project_label = QLabel("Project Value at age is 50")
        project_label.setObjectName("CardSubtitle")
        project_layout.addWidget(project_label)

        self.project_value = QLabel("$75,000")
        self.project_value.setObjectName("ValueSuccess")
        project_layout.addWidget(self.project_value)
        layout.addLayout(project_layout)

        # Progress bar comme dans l'image
        progress = QProgressBar()
        progress.setValue(65)
        progress.setObjectName("RetirementProgress")
        layout.addWidget(progress)

        return card

    def _create_credit_card(self):
        """Carte Credit Card - comme Behance"""
        card, layout = self._create_card_frame("Credit Card", "CreditCard")

        # Design carte de crédit comme l'image
        card_design = QLabel()
        card_design.setStyleSheet(
            """
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF6B6B, stop:1 #FF8E8E);
                border-radius: 12px;
                padding: 20px;
                color: white;
                font-weight: bold;
                font-size: 16px;
            }
        """
        )
        card_design.setText("VISA\nJerome Cain\n**** **** **** 1234\n$3,578")
        card_design.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(card_design)

        return card

    def _create_investment_card(self):
        """Carte Investment - comme Behance"""
        card, layout = self._create_card_frame("Investment", "InvestmentCard")

        # Market Value
        market_layout = QVBoxLayout()
        market_label = QLabel("Market Value")
        market_label.setObjectName("CardSubtitle")
        market_layout.addWidget(market_label)

        self.market_value = QLabel("$30,657")
        self.market_value.setObjectName("ValueSuccess")
        market_layout.addWidget(self.market_value)
        layout.addLayout(market_layout)

        # Cash Balance
        cash_layout = QVBoxLayout()
        cash_label = QLabel("Cash Balance")
        cash_label.setObjectName("CardSubtitle")
        cash_layout.addWidget(cash_label)

        self.cash_balance = QLabel("$506.6")
        self.cash_balance.setObjectName("ValueInfo")
        cash_layout.addWidget(self.cash_balance)
        layout.addLayout(cash_layout)

        # Tabs comme dans l'image
        tabs_layout = QHBoxLayout()

        portfolio_btn = QPushButton("Portfolio")
        portfolio_btn.setObjectName("TabButton")
        tabs_layout.addWidget(portfolio_btn)

        transactions_btn = QPushButton("Transactions")
        transactions_btn.setObjectName("TabButton")
        tabs_layout.addWidget(transactions_btn)

        layout.addLayout(tabs_layout)

        return card

    def _create_business_card(self):
        """Carte Business - comme Behance"""
        card, layout = self._create_card_frame("Business", "BusinessCard")

        # Total au centre
        total_label = QLabel("$4.2k")
        total_label.setObjectName("BusinessTotal")
        total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(total_label)

        # Donut chart simulé (cercles colorés)
        chart_container = QWidget()
        chart_container.setFixedHeight(80)
        chart_container.setStyleSheet(
            """
            QWidget {
                background: qconicalgradient(cx:0.5, cy:0.5, angle:0,
                    stop:0 #FF6B6B, stop:0.25 #4ECDC4, stop:0.5 #45B7D1, stop:0.75 #96CEB4, stop:1 #FFEAA7);
                border-radius: 40px;
            }
        """
        )
        layout.addWidget(chart_container)

        # Légende comme dans l'image
        legend_layout = QHBoxLayout()

        legend_items = [
            ("Shell", "#FF6B6B"),
            ("Starbucks", "#4ECDC4"),
            ("Dropbox", "#45B7D1"),
            ("McDonald's", "#96CEB4"),
        ]

        for name, color in legend_items:
            item_layout = QHBoxLayout()

            # Point coloré
            point = QLabel("●")
            point.setStyleSheet(f"color: {color}; font-size: 12px;")
            item_layout.addWidget(point)

            # Nom
            name_label = QLabel(name)
            name_label.setObjectName("LegendText")
            item_layout.addWidget(name_label)

            legend_layout.addLayout(item_layout)

        layout.addLayout(legend_layout)

        return card

    def _create_budget_card(self):
        """Carte Budget - comme Behance"""
        card, layout = self._create_card_frame("Budget", "BudgetCard")

        # Income et Expense
        budget_layout = QHBoxLayout()

        # Income
        income_layout = QVBoxLayout()
        income_label = QLabel("Income")
        income_label.setObjectName("CardSubtitle")
        income_layout.addWidget(income_label)

        self.income_value = QLabel("$4,567.34")
        self.income_value.setObjectName("ValueSuccess")
        income_layout.addWidget(self.income_value)
        budget_layout.addLayout(income_layout)

        # Expense
        expense_layout = QVBoxLayout()
        expense_label = QLabel("Expense")
        expense_label.setObjectName("CardSubtitle")
        expense_layout.addWidget(expense_label)

        self.expense_value = QLabel("$4,567.34")
        self.expense_value.setObjectName("ValueDanger")
        expense_layout.addWidget(self.expense_value)
        budget_layout.addLayout(expense_layout)

        layout.addLayout(budget_layout)

        # Liste des dépenses comme dans l'image
        expenses = [
            ("Groceries", "$7600.00"),
            ("Healthy Fruits", "$1200.00"),
            ("Internet", "$150.00"),
        ]

        for category, amount in expenses:
            exp_layout = QHBoxLayout()

            category_label = QLabel(category)
            category_label.setObjectName("ExpenseCategory")
            exp_layout.addWidget(category_label)

            exp_layout.addStretch()

            amount_label = QLabel(amount)
            amount_label.setObjectName("ExpenseAmount")
            exp_layout.addWidget(amount_label)

            layout.addLayout(exp_layout)

        # Bar chart simple
        chart_widget = QWidget()
        chart_widget.setFixedHeight(40)
        chart_widget.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1DD1A1, stop:0.5 #4ECDC4, stop:1 #45B7D1);
                border-radius: 8px;
            }
        """
        )
        layout.addWidget(chart_widget)

        return card

    def _on_kpi_clicked(self, kpi_id: str):
        """Gestion du clic sur un KPI"""
        print(f"KPI cliqué : {kpi_id}")

    def _on_payroll_date_clicked(self, date: QDate):
        """Gestion du clic sur une date du calendrier"""
        self.payrollDateSelected.emit(date)
