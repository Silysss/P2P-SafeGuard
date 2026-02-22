import json
import os
import uuid
import time
from typing import Dict, List, Optional

class DBManager:
    """Gestionnaire de la base de données locale (vault.json)."""

    def __init__(self, db_path: str = "vault.json"):
        self.db_path = db_path
        self.data = self._load_or_create_db()

    def _load_or_create_db(self) -> dict:
        """Charge le fichier JSON ou le crée s'il n'existe pas avec un ID de vault unique."""
        if not os.path.exists(self.db_path):
            initial_data = {
                "vault_id": str(uuid.uuid4()),
                "records": []
            }
            self._save_db(initial_data)
            return initial_data

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # En cas de corruption, on pourrait lever une erreur, mais ici on recrée (ou backup)
            print(f"Erreur: {self.db_path} est corrompu. Création d'une nouvelle base de données.")
            return {"vault_id": str(uuid.uuid4()), "records": []}

    def _save_db(self, data: Optional[dict] = None):
        """Sauvegarde les données dans le fichier JSON."""
        if data is None:
            data = self.data
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_all_records(self) -> List[dict]:
        """Retourne tous les records non supprimés (soft delete exclu)."""
        return [r for r in self.data.get("records", []) if not r.get("is_deleted", False)]
        
    def get_raw_records(self) -> List[dict]:
         """Retourne TOUS les records (inclus deleted) pour la synchronisation."""
         return self.data.get("records", [])

    def get_record(self, record_uuid: str) -> Optional[dict]:
        """Récupère un record spécifique par son UUID (qu'il soit deleted ou non)."""
        for record in self.data.get("records", []):
            if record["uuid"] == record_uuid:
                return record
        return None

    def upsert_record_local(self, record_uuid: str, ciphertext: str, nonce: str, is_deleted: bool = False) -> dict:
        """
        Action LOCALE : L'utilisateur ajoute ou modifie un enregistrement depuis ce device.
        On met à jour le temps actuel et on sauvegarde.
        Retourne le record complet pour diffusion Gossip.
        """
        new_record = {
            "uuid": record_uuid,
            "updated_at": time.time(),
            "is_deleted": is_deleted,
            "nonce": nonce,
            "ciphertext": ciphertext
        }
        
        self._upsert(new_record)
        return new_record
        
    def _upsert(self, new_record: dict):
        """Remplace ou ajoute le record en mémoire et sauvegarde (Interne)."""
        records = self.data.setdefault("records", [])
        for i, record in enumerate(records):
            if record["uuid"] == new_record["uuid"]:
                records[i] = new_record
                self._save_db()
                return
                
        records.append(new_record)
        self._save_db()

    def process_gossip_update(self, gossip_record: dict) -> bool:
        """
        Action DISTANTE : Résolution de conflit LWW (Feature B.2 - Module Sync).
        Vérifie si le record distant est plus récent que le record local.
        Retourne True si appliqué (donc à propager), False si ignoré (trop vieux).
        """
        local_record = self.get_record(gossip_record["uuid"])
        
        if local_record:
            # LWW Check: Si le timestamp reçu n'est pas strictement supérieur, on ignore.
            if gossip_record["updated_at"] <= local_record["updated_at"]:
                return False
                
        # Le record n'existe pas ou est plus récent, on l'applique
        self._upsert(gossip_record)
        return True
