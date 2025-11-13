# services/profile_manager.py
# ========================================
# GESTIONNAIRE PROFILS MAPPING
# ========================================
# Mémorisation et réutilisation mappings par fichier/organisme

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime


class ProfileManager:
    """
    Gestionnaire de profils de mapping

    Un profil contient:
    - Mapping colonnes (type → col_idx)
    - Fingerprint fichier (hash colonnes + masques)
    - Métadonnées (organisme, nom fichier type, etc.)
    - Historique utilisations
    """

    def __init__(self, profiles_dir: str = None):
        """
        Args:
            profiles_dir: Dossier stockage profils (défaut: config/profiles/)
        """
        if profiles_dir:
            self.profiles_dir = Path(profiles_dir)
        else:
            self.profiles_dir = Path(__file__).parent.parent / "config" / "profiles"

        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def generate_fingerprint(self, headers: List[str], sample_rows: List[List]) -> str:
        """
        Génère un fingerprint du fichier (hash colonnes + patterns valeurs)

        Args:
            headers: Liste en-têtes colonnes
            sample_rows: Échantillon lignes (10-20)

        Returns:
            str: Hash MD5 du fingerprint
        """
        # Normaliser headers (lowercase, sans espaces)
        norm_headers = [h.lower().strip().replace(" ", "_") for h in headers]

        # Extraire patterns valeurs (premiers caractères, longueurs)
        patterns = []
        for col_idx in range(len(headers)):
            col_values = [
                row[col_idx] if col_idx < len(row) else None for row in sample_rows[:10]
            ]

            # Pattern: type + longueur moyenne
            types = [type(v).__name__ for v in col_values if v is not None]
            lengths = [len(str(v)) for v in col_values if v is not None]

            avg_len = sum(lengths) / len(lengths) if lengths else 0
            dominant_type = max(set(types), key=types.count) if types else "None"

            patterns.append(f"{dominant_type}:{int(avg_len)}")

        # Créer fingerprint texte
        fingerprint_text = "|".join(norm_headers) + "||" + "|".join(patterns)

        # Hash MD5
        return hashlib.md5(fingerprint_text.encode("utf-8")).hexdigest()

    def save_profile(
        self,
        name: str,
        mapping: Dict[str, int],
        headers: List[str],
        sample_rows: List[List],
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Sauvegarde un profil de mapping

        Args:
            name: Nom du profil (ex: "paie_standard_2025")
            mapping: Mapping détecté {type_name: col_idx}
            headers: En-têtes colonnes
            sample_rows: Échantillon pour fingerprint
            metadata: Métadonnées additionnelles

        Returns:
            str: Chemin fichier profil créé
        """
        fingerprint = self.generate_fingerprint(headers, sample_rows)

        profile_data = {
            "version": "1.0",
            "name": name,
            "fingerprint": fingerprint,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "usage_count": 1,
            "mapping": mapping,
            "headers": headers,
            "metadata": metadata or {},
        }

        # Nom fichier: <fingerprint>.profile.json
        profile_path = self.profiles_dir / f"{fingerprint}.profile.json"

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Profil sauvegardé: {profile_path}")

        return str(profile_path)

    def find_profile(
        self, headers: List[str], sample_rows: List[List]
    ) -> Optional[Dict]:
        """
        Cherche un profil existant correspondant au fichier

        Args:
            headers: En-têtes fichier actuel
            sample_rows: Échantillon lignes

        Returns:
            dict ou None: Profil trouvé
        """
        fingerprint = self.generate_fingerprint(headers, sample_rows)
        profile_path = self.profiles_dir / f"{fingerprint}.profile.json"

        if profile_path.exists():
            with open(profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)

            # Mettre à jour last_used et usage_count
            profile["last_used"] = datetime.now().isoformat()
            profile["usage_count"] = profile.get("usage_count", 0) + 1

            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)

            print(
                f"✓ Profil trouvé: {profile['name']} (utilisé {profile['usage_count']} fois)"
            )

            return profile

        return None

    def list_profiles(self) -> List[Dict]:
        """
        Liste tous les profils disponibles

        Returns:
            List[dict]: Profils triés par last_used DESC
        """
        profiles = []

        for profile_file in self.profiles_dir.glob("*.profile.json"):
            try:
                with open(profile_file, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                profiles.append(profile)
            except Exception as e:
                print(f"⚠️ Erreur lecture profil {profile_file}: {e}")

        # Trier par dernière utilisation
        profiles.sort(key=lambda p: p.get("last_used", ""), reverse=True)

        return profiles

    def delete_profile(self, fingerprint: str) -> bool:
        """
        Supprime un profil

        Args:
            fingerprint: Hash du profil

        Returns:
            bool: True si supprimé
        """
        profile_path = self.profiles_dir / f"{fingerprint}.profile.json"

        if profile_path.exists():
            profile_path.unlink()
            print(f"✓ Profil supprimé: {fingerprint}")
            return True

        return False


# ========== TESTS ==========

if __name__ == "__main__":
    print("=" * 70)
    print("TEST PROFILE MANAGER")
    print("=" * 70)

    manager = ProfileManager()

    # Test données
    headers = ["Type", "Nom, Prénom", "Matricule", "Date", "Montant"]
    sample_rows = [
        ["Gains", "Dupont, Jean", "1001", "2023-01-15", "1234.56"],
        ["Gains", "Martin, Claire", "1002", "2023-01-15", "2500.00"],
    ]

    mapping = {
        "type_paie": 0,
        "fullname": 1,
        "matricule": 2,
        "date_paie": 3,
        "montant": 4,
    }

    # Test 1: Créer profil
    print("\n1️⃣ Création profil:")
    profile_path = manager.save_profile(
        name="Test Paie Standard",
        mapping=mapping,
        headers=headers,
        sample_rows=sample_rows,
        metadata={"organisme": "SCP Test"},
    )

    # Test 2: Retrouver profil
    print("\n2️⃣ Recherche profil:")
    found = manager.find_profile(headers, sample_rows)
    if found:
        print(f"  ✓ Profil retrouvé: {found['name']}")
        print(f"  Mapping: {found['mapping']}")

    # Test 3: Lister profils
    print("\n3️⃣ Liste profils:")
    all_profiles = manager.list_profiles()
    for p in all_profiles:
        print(f"  - {p['name']} (utilisé {p.get('usage_count', 0)} fois)")

    print("\n✅ Tests terminés")
