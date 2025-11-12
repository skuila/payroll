# services/mapping_profiles.py
# ========================================
# GESTIONNAIRE PROFILS MAPPING AVEC SIGNATURES TOLERANTES
# ========================================

import json
from typing import Dict, Optional, List, Any
from app.services.schema_inference import normalize_header


def header_signature(headers: List[str]) -> str:
    """
    Génère une signature normalisée pour une liste d'en-têtes

    Args:
        headers: Liste des en-têtes

    Returns:
        str: Signature normalisée (hdr:xxx|yyy|zzz...)
    """
    base = [normalize_header(h) for h in headers]
    base = [str(h).strip().lower() for h in base]
    return "hdr:" + "|".join(sorted(base))


class MappingProfiles:
    """
    Gestionnaire de profils de mapping avec support de signatures tolérantes
    """

    def __init__(self, repo):
        """
        Args:
            repo: Instance de DataRepository pour accès BDD
        """
        self.repo = repo

    def find_by_signature(
        self, client_key: str, signature: str
    ) -> Optional[Dict[str, Any]]:
        """
        Cherche un profil par signature (avec fallback normalisé)

        Args:
            client_key: Clé client
            signature: Signature des headers

        Returns:
            dict ou None: Profil trouvé avec ses métadonnées
        """
        # Essaie signature telle quelle
        row = self.repo.run_query(
            """
            SELECT profile_id, client_key, profile_name, header_signature, mapping_json, options_json, confidence
            FROM payroll.ingestion_profiles
            WHERE client_key=%s AND header_signature=%s
            ORDER BY updated_at DESC LIMIT 1
        """,
            (client_key, signature),
            fetch_one=True,
        )

        if row:
            return {
                "profile_id": row[0],
                "client_key": row[1],
                "profile_name": row[2],
                "header_signature": row[3],
                "mapping_json": row[4],
                "options_json": row[5],
                "confidence": row[6],
            }

        # Fallback: normaliser la signature passée (gestion alias)
        # Si signature commence par "hdr:", extraire les headers et renormaliser
        if signature.startswith("hdr:"):
            headers_list = signature.replace("hdr:", "").split("|")
            norm_sig = header_signature(headers_list)

            if norm_sig != signature:
                row = self.repo.run_query(
                    """
                    SELECT profile_id, client_key, profile_name, header_signature, mapping_json, options_json, confidence
                    FROM payroll.ingestion_profiles
                    WHERE client_key=%s AND header_signature=%s
                    ORDER BY updated_at DESC LIMIT 1
                """,
                    (client_key, norm_sig),
                    fetch_one=True,
                )

                if row:
                    return {
                        "profile_id": row[0],
                        "client_key": row[1],
                        "profile_name": row[2],
                        "header_signature": row[3],
                        "mapping_json": row[4],
                        "options_json": row[5],
                        "confidence": row[6],
                    }

        return None

    def save_profile(
        self,
        client_key: str,
        profile_name: str,
        headers: List[str],
        mapping: Dict[str, int],
        options: Optional[Dict] = None,
        confidence: float = 1.0,
    ) -> int:
        """
        Sauvegarde un profil de mapping

        Args:
            client_key: Clé client
            profile_name: Nom du profil
            headers: Liste des en-têtes
            mapping: Mapping colonnes
            options: Options additionnelles
            confidence: Score de confiance

        Returns:
            int: ID du profil créé
        """
        sig = header_signature(headers)
        mapping_json = json.dumps(mapping, ensure_ascii=False)
        options_json = json.dumps(options or {}, ensure_ascii=False)

        result = self.repo.run_query(
            """
            INSERT INTO payroll.ingestion_profiles 
            (client_key, profile_name, header_signature, mapping_json, options_json, confidence)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s)
            RETURNING profile_id
        """,
            (client_key, profile_name, sig, mapping_json, options_json, confidence),
            fetch_one=True,
        )

        return result[0] if result else None
