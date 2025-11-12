from PyQt6.QtWidgets import QMenu, QFileDialog, QMessageBox, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt


def attach_reports_menu(main_window):
    try:
        menubar = main_window.menuBar()
        reports_menu = menubar.addMenu("&Rapports")

        excel_menu = QMenu("Export Excel", main_window)
        reports_menu.addMenu(excel_menu)

        _add_excel_action(excel_menu, main_window, "Résumé par période", "resume")
        _add_excel_action(
            excel_menu, main_window, "Détail par employé", "detail_employe"
        )
        _add_excel_action(
            excel_menu, main_window, "Répartition par code de paie", "rep_code_paie"
        )
        _add_excel_action(
            excel_menu, main_window, "Répartition par poste budgétaire", "rep_poste"
        )
        _add_excel_action(
            excel_menu, main_window, "Évolution 12 dernières périodes", "evolution"
        )
        _add_excel_action(excel_menu, main_window, "Anomalies", "anomalies")
        _add_excel_action(
            excel_menu, main_window, "Comparaison période N vs N-1", "comparaison"
        )

        pdf_menu = QMenu("Export PDF", main_window)
        reports_menu.addMenu(pdf_menu)

        _add_pdf_action(pdf_menu, main_window, "Résumé par période", "resume")
        _add_pdf_action(pdf_menu, main_window, "Détail par employé", "detail_employe")
        _add_pdf_action(
            pdf_menu, main_window, "Répartition par code de paie", "rep_code_paie"
        )
        _add_pdf_action(
            pdf_menu, main_window, "Répartition par poste budgétaire", "rep_poste"
        )
        _add_pdf_action(
            pdf_menu, main_window, "Évolution 12 dernières périodes", "evolution"
        )
        _add_pdf_action(pdf_menu, main_window, "Anomalies", "anomalies")
        _add_pdf_action(
            pdf_menu, main_window, "Comparaison période N vs N-1", "comparaison"
        )

        return reports_menu
    except Exception as e:
        print(f"Erreur attach_reports_menu: {e}")
        return None


def _add_excel_action(menu, main_window, label, report_type):
    action = QAction(label, main_window)
    action.triggered.connect(lambda: _export_excel(main_window, report_type, label))
    menu.addAction(action)


def _add_pdf_action(menu, main_window, label, report_type):
    action = QAction(label, main_window)
    action.triggered.connect(lambda: _export_pdf(main_window, report_type, label))
    menu.addAction(action)


def _export_excel(main_window, report_type, label):
    try:
        from logic.reports import (
            export_excel_resume,
            export_excel_detail_employe,
            export_excel_rep_code_paie,
            export_excel_rep_poste,
            export_excel_evolution,
            export_excel_anomalies,
            export_excel_comparaison,
        )

        period = _get_current_period(main_window)
        if not period:
            QMessageBox.warning(
                main_window, "Export Excel", "Aucune période sélectionnée."
            )
            return

        filepath, _ = QFileDialog.getSaveFileName(
            main_window,
            f"Exporter {label} (Excel)",
            f"{label.replace(' ', '_')}_{period}.xlsx",
            "Fichiers Excel (*.xlsx)",
        )

        if not filepath:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if report_type == "resume":
                export_excel_resume(period, filepath)
            elif report_type == "detail_employe":
                export_excel_detail_employe(period, filepath)
            elif report_type == "rep_code_paie":
                export_excel_rep_code_paie(period, filepath)
            elif report_type == "rep_poste":
                export_excel_rep_poste(period, filepath)
            elif report_type == "evolution":
                export_excel_evolution(period, filepath)
            elif report_type == "anomalies":
                export_excel_anomalies(period, filepath)
            elif report_type == "comparaison":
                periods = (
                    main_window.provider.periods()
                    if hasattr(main_window, "provider")
                    else []
                )
                if len(periods) < 2:
                    QMessageBox.warning(
                        main_window, "Export", "Au moins 2 périodes requises."
                    )
                    return
                p1 = periods[-1]
                p2 = periods[-2]
                export_excel_comparaison(p1, p2, filepath)

            QMessageBox.information(
                main_window, "Export Excel", f"Fichier créé :\n{filepath}"
            )
        finally:
            QApplication.restoreOverrideCursor()
    except ImportError:
        QApplication.restoreOverrideCursor()
        QMessageBox.warning(
            main_window, "Export Excel", "Module logic.reports non disponible."
        )
    except Exception as e:
        QApplication.restoreOverrideCursor()
        QMessageBox.warning(main_window, "Export Excel", f"Erreur : {e}")


def _export_pdf(main_window, report_type, label):
    try:
        from logic.reports import (
            export_pdf_resume,
            export_pdf_detail_employe,
            export_pdf_rep_code_paie,
            export_pdf_rep_poste,
            export_pdf_evolution,
            export_pdf_anomalies,
            export_pdf_comparaison,
        )

        period = _get_current_period(main_window)
        if not period:
            QMessageBox.warning(
                main_window, "Export PDF", "Aucune période sélectionnée."
            )
            return

        filepath, _ = QFileDialog.getSaveFileName(
            main_window,
            f"Exporter {label} (PDF)",
            f"{label.replace(' ', '_')}_{period}.pdf",
            "Fichiers PDF (*.pdf)",
        )

        if not filepath:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if report_type == "resume":
                export_pdf_resume(period, filepath)
            elif report_type == "detail_employe":
                export_pdf_detail_employe(period, filepath)
            elif report_type == "rep_code_paie":
                export_pdf_rep_code_paie(period, filepath)
            elif report_type == "rep_poste":
                export_pdf_rep_poste(period, filepath)
            elif report_type == "evolution":
                export_pdf_evolution(period, filepath)
            elif report_type == "anomalies":
                export_pdf_anomalies(period, filepath)
            elif report_type == "comparaison":
                periods = (
                    main_window.provider.periods()
                    if hasattr(main_window, "provider")
                    else []
                )
                if len(periods) < 2:
                    QMessageBox.warning(
                        main_window, "Export", "Au moins 2 périodes requises."
                    )
                    return
                p1 = periods[-1]
                p2 = periods[-2]
                export_pdf_comparaison(p1, p2, filepath)

            QMessageBox.information(
                main_window, "Export PDF", f"Fichier créé :\n{filepath}"
            )
        finally:
            QApplication.restoreOverrideCursor()
    except ImportError:
        QApplication.restoreOverrideCursor()
        QMessageBox.warning(
            main_window, "Export PDF", "Module logic.reports non disponible."
        )
    except Exception as e:
        QApplication.restoreOverrideCursor()
        QMessageBox.warning(main_window, "Export PDF", f"Erreur : {e}")


def _get_current_period(main_window):
    if hasattr(main_window, "dashboard") and hasattr(
        main_window.dashboard, "current_period"
    ):
        return main_window.dashboard.current_period()
    if hasattr(main_window, "provider"):
        periods = main_window.provider.periods()
        return periods[-1] if periods else None
    return None
