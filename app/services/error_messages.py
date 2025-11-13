#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de traduction des erreurs techniques en messages utilisateur simples
"""
import re
from typing import Optional, Tuple


def translate_error(
    error: Exception, error_message: Optional[str] = None
) -> Tuple[str, str]:
    """
    Traduit une erreur technique en message utilisateur simple.

    Args:
        error: Exception levée
        error_message: Message d'erreur (optionnel, sinon utilise str(error))

    Returns:
        Tuple (message_utilisateur, solution)
    """
    if error_message is None:
        error_message = str(error)

    error_type = type(error).__name__
    error_lower = error_message.lower()

    # ========== ERREURS FICHIER ==========

    if (
        error_type == "FileNotFoundError"
        or "fichier introuvable" in error_lower
        or "file not found" in error_lower
    ):
        return (
            "Le fichier sélectionné n'existe plus. Vérifiez que le fichier n'a pas été déplacé ou supprimé.",
            "Vérifier le chemin du fichier et réessayer.",
        )

    if (
        "format non supporté" in error_lower
        or "format not supported" in error_lower
        or "unsupported format" in error_lower
    ):
        return (
            "Ce type de fichier n'est pas supporté. Utilisez un fichier Excel (.xlsx) ou CSV.",
            "Convertir le fichier au format Excel (.xlsx) ou CSV et réessayer.",
        )

    # ========== ERREURS COLONNES ==========

    if (
        "colonne obligatoire" in error_lower
        or "colonne manquante" in error_lower
        or "column" in error_lower
        and "missing" in error_lower
    ):
        # Extraire le nom de la colonne si possible
        colonne_match = re.search(r"['\"]([^'\"]+)['\"]", error_message)
        colonne = colonne_match.group(1) if colonne_match else "requise"

        if "matricule" in error_lower or "employee" in error_lower:
            return (
                "Le fichier ne contient pas la colonne 'Matricule' qui est obligatoire. Vérifiez que les colonnes suivantes sont présentes : Matricule, Nom, Date de paie, Montant.",
                "Vérifier les en-têtes du fichier et ajouter la colonne manquante.",
            )
        elif "date" in error_lower or "date de paie" in error_lower:
            return (
                "Le fichier ne contient pas la colonne 'Date de paie' qui est obligatoire.",
                "Vérifier les en-têtes du fichier et ajouter la colonne 'Date de paie'.",
            )
        elif "montant" in error_lower or "amount" in error_lower:
            return (
                "Le fichier ne contient pas la colonne 'Montant' qui est obligatoire.",
                "Vérifier les en-têtes du fichier et ajouter la colonne 'Montant'.",
            )
        else:
            return (
                f"Le fichier ne contient pas toutes les colonnes nécessaires. La colonne '{colonne}' est manquante. Vérifiez que les colonnes suivantes sont présentes : Matricule, Nom, Date de paie, Montant.",
                "Vérifier les en-têtes du fichier et ajouter les colonnes manquantes.",
            )

    # ========== ERREURS DONNÉES ==========

    if (
        "date invalide" in error_lower
        or "invalid date" in error_lower
        or "date" in error_lower
        and "invalid" in error_lower
    ):
        return (
            "Certaines dates dans le fichier sont incorrectes. Vérifiez que les dates sont au format JJ/MM/AAAA ou AAAA-MM-JJ.",
            "Corriger les dates dans le fichier Excel et réessayer.",
        )

    if (
        "matricule manquant" in error_lower
        or "matricule" in error_lower
        and ("missing" in error_lower or "vide" in error_lower)
    ):
        return (
            "Certaines lignes n'ont pas de matricule. Tous les employés doivent avoir un matricule.",
            "Ajouter les matricules manquants dans le fichier Excel.",
        )

    if (
        "montant invalide" in error_lower
        or "invalid amount" in error_lower
        or "montant" in error_lower
        and "invalid" in error_lower
    ):
        return (
            "Certains montants ne sont pas des nombres valides. Vérifiez que les montants sont bien des nombres (ex: 1500.50).",
            "Corriger les montants dans le fichier Excel. Utilisez des nombres avec un point comme séparateur décimal (ex: 1500.50).",
        )

    # ========== ERREURS PÉRIODE ==========

    if (
        "période fermée" in error_lower
        or "period closed" in error_lower
        or "période" in error_lower
        and "fermée" in error_lower
    ):
        return (
            "Cette période de paie est déjà fermée. Vous ne pouvez pas importer de nouvelles données pour cette période.",
            "Contacter l'administrateur pour ouvrir la période ou utiliser une autre date.",
        )

    if (
        "fichier déjà importé" in error_lower
        or "already imported" in error_lower
        or "duplicate" in error_lower
    ):
        return (
            "Ce fichier a déjà été importé. Si vous voulez le réimporter, supprimez d'abord l'import précédent.",
            "Vérifier l'historique des imports et supprimer l'import précédent si nécessaire.",
        )

    # ========== ERREURS BASE DE DONNÉES ==========

    if (
        "connexion" in error_lower
        and ("échouée" in error_lower or "failed" in error_lower)
    ) or ("connection" in error_lower and "failed" in error_lower):
        return (
            "Impossible de se connecter à la base de données. Vérifiez votre connexion internet ou contactez le support technique.",
            "Vérifier la connexion internet et réessayer. Si le problème persiste, contacter le support.",
        )

    if (
        "aucune donnée" in error_lower
        or "no data" in error_lower
        or "données" in error_lower
        and "trouvée" in error_lower
    ):
        return (
            "Aucune donnée n'a été trouvée pour cette période. Vérifiez que vous avez bien importé un fichier pour cette date.",
            "Importer un fichier pour cette période avant de consulter les données.",
        )

    if "période invalide" in error_lower or "invalid period" in error_lower:
        return (
            "La date sélectionnée n'est pas valide. Utilisez le format JJ/MM/AAAA.",
            "Corriger le format de la date et réessayer.",
        )

    # ========== ERREURS GÉNÉRIQUES ==========

    if error_type == "ValueError":
        if "empty" in error_lower or "vide" in error_lower:
            return (
                "Le fichier est vide ou ne contient pas de données valides.",
                "Vérifier que le fichier contient des données et réessayer.",
            )
        return (
            "Les données du fichier ne sont pas valides. Vérifiez le format des colonnes et des valeurs.",
            "Vérifier le fichier Excel et corriger les erreurs avant de réessayer.",
        )

    if (
        error_type == "ImportError"
        or "import échoué" in error_lower
        or "import failed" in error_lower
    ):
        return (
            "L'import a échoué. Vérifiez que le fichier est au bon format et que toutes les colonnes requises sont présentes.",
            "Vérifier le fichier et réessayer. Consultez les messages d'erreur ci-dessus pour plus de détails.",
        )

    if (
        error_type == "PermissionError"
        or "permission" in error_lower
        or "droit" in error_lower
    ):
        return (
            "Vous n'avez pas les permissions nécessaires pour effectuer cette action.",
            "Contacter l'administrateur pour obtenir les permissions nécessaires.",
        )

    # ========== MESSAGE PAR DÉFAUT ==========

    # Message générique si aucune correspondance
    return (
        f"Une erreur s'est produite : {error_message[:100]}",
        "Vérifier les données et réessayer. Si le problème persiste, contacter le support technique.",
    )


def translate_warning(warning_message: str) -> Tuple[str, str]:
    """
    Traduit un avertissement technique en message utilisateur simple.

    Args:
        warning_message: Message d'avertissement

    Returns:
        Tuple (message_utilisateur, action)
    """
    warning_lower = warning_message.lower()

    if "colonne optionnelle" in warning_lower or "optional column" in warning_lower:
        return (
            "Certaines colonnes optionnelles sont manquantes, mais l'import peut continuer.",
            "Aucune action requise.",
        )

    if (
        "lignes rejetées" in warning_lower
        or "lignes ignorées" in warning_lower
        or "rows rejected" in warning_lower
    ):
        # Extraire le nombre si possible
        nb_match = re.search(r"(\d+)", warning_message)
        nb = nb_match.group(1) if nb_match else "certaines"
        return (
            f"{nb} lignes ont été ignorées car elles contenaient des erreurs. Les autres lignes ont été importées avec succès.",
            "Vérifier les lignes rejetées dans le rapport d'import.",
        )

    if (
        "tests qualité" in warning_lower
        or "anomalies" in warning_lower
        or "quality tests" in warning_lower
    ):
        return (
            "L'import est terminé, mais certaines vérifications ont détecté des anomalies. Consultez le rapport pour plus de détails.",
            "Consulter le rapport d'anomalies pour identifier les problèmes.",
        )

    # Message par défaut
    return (warning_message, "Aucune action requise.")


def format_error_for_user(
    error: Exception, error_message: Optional[str] = None
) -> dict:
    """
    Formate une erreur pour l'affichage à l'utilisateur.

    Returns:
        dict avec 'message', 'solution', 'type' (error/warning)
    """
    user_msg, solution = translate_error(error, error_message)

    return {
        "message": user_msg,
        "solution": solution,
        "type": "error",
        "technical": str(error),  # Garder l'erreur technique pour les logs
    }


def format_warning_for_user(warning_message: str) -> dict:
    """
    Formate un avertissement pour l'affichage à l'utilisateur.

    Returns:
        dict avec 'message', 'action', 'type' (warning)
    """
    user_msg, action = translate_warning(warning_message)

    return {"message": user_msg, "action": action, "type": "warning"}
