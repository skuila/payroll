from PyQt6.QtWidgets import (
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
)
from PyQt6.QtGui import QAction


def attach_analysis_menu(main_window):
    try:
        menubar = main_window.menuBar()
        analysis_menu = menubar.addMenu("&Analyse")

        act_quick_audit = QAction("Audit rapide", main_window)
        act_quick_audit.setShortcut("Ctrl+Shift+A")
        act_quick_audit.setToolTip("Nets négatifs, majuscules, codes sensibles")
        act_quick_audit.triggered.connect(lambda: _run_quick_audit(main_window))
        analysis_menu.addAction(act_quick_audit)

        act_compare = QAction("Comparer périodes…", main_window)
        act_compare.setToolTip("Sélectionner deux périodes pour comparaison")
        act_compare.triggered.connect(lambda: _compare_periods_dialog(main_window))
        analysis_menu.addAction(act_compare)

        act_anomalies = QAction("Anomalies détaillées", main_window)
        act_anomalies.setToolTip("Afficher table filtrée des anomalies")
        act_anomalies.triggered.connect(lambda: _show_anomalies_detailed(main_window))
        analysis_menu.addAction(act_anomalies)

        return analysis_menu
    except Exception as e:
        print(f"Erreur attach_analysis_menu: {e}")
        return None


def _run_quick_audit(main_window):
    try:
        from logic.audit import run_basic_audit

        period = None
        if hasattr(main_window, "dashboard") and hasattr(
            main_window.dashboard, "current_period"
        ):
            period = main_window.dashboard.current_period()

        findings = run_basic_audit(period)

        msg_parts = []
        for f in findings.get("findings", [])[:10]:
            msg_parts.append(f"• {f.get('rule', '?')} : {f.get('count', 0)}")

        msg = "\n".join(msg_parts) if msg_parts else "Aucune anomalie détectée."

        QMessageBox.information(main_window, "Audit rapide", f"Résultats :\n\n{msg}")

        if hasattr(main_window, "right_panel") and hasattr(
            main_window.right_panel, "refresh_audit"
        ):
            main_window.right_panel.refresh_audit(findings)
    except ImportError:
        QMessageBox.warning(
            main_window, "Audit rapide", "Module logic.audit non disponible."
        )
    except Exception as e:
        QMessageBox.warning(main_window, "Audit rapide", f"Erreur : {e}")


def _compare_periods_dialog(main_window):
    try:
        from logic.audit import compare_periods

        if not hasattr(main_window, "provider"):
            QMessageBox.information(main_window, "Comparer", "Provider non disponible.")
            return

        periods = main_window.provider.periods()
        if len(periods) < 2:
            QMessageBox.information(
                main_window, "Comparer", "Au moins 2 périodes requises."
            )
            return

        dlg = QDialog(main_window)
        dlg.setWindowTitle("Comparer périodes")
        dlg.resize(400, 200)

        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel("Période 1 (récente) :"))
        combo1 = QComboBox(dlg)
        combo1.addItems(periods)
        combo1.setCurrentIndex(len(periods) - 1)
        layout.addWidget(combo1)

        layout.addWidget(QLabel("Période 2 (ancienne) :"))
        combo2 = QComboBox(dlg)
        combo2.addItems(periods)
        combo2.setCurrentIndex(max(0, len(periods) - 2))
        layout.addWidget(combo2)

        btn_ok = QPushButton("Comparer", dlg)
        btn_ok.clicked.connect(dlg.accept)
        layout.addWidget(btn_ok)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            p1 = combo1.currentText()
            p2 = combo2.currentText()

            result = compare_periods(p1, p2)

            delta_net = result.get("delta_net", 0)
            pct = result.get("pct", 0)

            msg = f"Comparaison {p1} vs {p2} :\n\n"
            msg += f"Delta net : {delta_net:,.2f} $ ({pct:+.1f}%)\n"

            QMessageBox.information(main_window, "Comparaison", msg)
    except ImportError:
        QMessageBox.warning(
            main_window, "Comparer", "Module logic.audit non disponible."
        )
    except Exception as e:
        QMessageBox.warning(main_window, "Comparer", f"Erreur : {e}")


def _show_anomalies_detailed(main_window):
    try:
        from logic.audit import run_basic_audit

        period = None
        if hasattr(main_window, "dashboard") and hasattr(
            main_window.dashboard, "current_period"
        ):
            period = main_window.dashboard.current_period()

        findings = run_basic_audit(period)

        anomalies_count = sum(f.get("count", 0) for f in findings.get("findings", []))

        QMessageBox.information(
            main_window,
            "Anomalies détaillées",
            f"Total anomalies : {anomalies_count}\n\n(Table détaillée : à implémenter dans un panel séparé)",
        )
    except ImportError:
        QMessageBox.warning(
            main_window, "Anomalies", "Module logic.audit non disponible."
        )
    except Exception as e:
        QMessageBox.warning(main_window, "Anomalies", f"Erreur : {e}")
