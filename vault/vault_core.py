import json
import uuid
from typing import List, Dict, Optional, Callable

from .crypto_service import CryptoService
from .context_checker import ContextChecker
from .db_manager import DBManager

class VaultCore:
    """
    Contrôleur principal du Module A (Vault).
    Vérifie le contexte avant toute opération et interagit avec le DBManager et CryptoService.
    """
    def __init__(self, master_password: str, allowed_bssids_hashes: List[str], db_path: str = "vault.json", on_sync_trigger: Optional[Callable[[dict], None]] = None):
        self.context_checker = ContextChecker(allowed_bssids_hashes)
        self.crypto_service = CryptoService(master_password)
        self.db_manager = DBManager(db_path)
        self.on_sync_trigger = on_sync_trigger # Callback pour appeler Module B quand une action locale arrive
        
    def _check_access(self) -> bool:
        """Vérifie si le contexte BSSID est valide."""
        return self.context_checker.is_context_valid()

    def add_or_update_secret(self, service: str, username: str, password: str, notes: str, record_uuid: Optional[str] = None) -> bool:
        """
        Action locale de l'UI : Ajoute ou modifie un secret.
        """
        if not self._check_access():
            print("Access Denied: BSSID de l'environnement physique non autorisé.")
            return False
            
        if record_uuid is None:
            record_uuid = str(uuid.uuid4())
            
        # Structure de données en clair du secret
        secret_data = json.dumps({
            "service": service,
            "username": username,
            "password": password,
            "notes": notes
        })
        
        # Chiffrement
        ciphertext, nonce = self.crypto_service.encrypt(secret_data)
        
        # Sauvegarde DB avec mise à jour du timestamp LWW
        record = self.db_manager.upsert_record_local(record_uuid, ciphertext, nonce)
        
        # Trigger Interface avec Module B
        if self.on_sync_trigger:
            self.on_sync_trigger(record)
            
        print(f"Secret pour '{service}' sauvegardé localement (UUID: {record_uuid}).")
        return True
        
    def get_all_secrets_decrypted(self) -> List[Dict]:
        """
        Action locale de l'UI : Affiche tous les secrets (si BSSID ok).
        """
        if not self._check_access():
            print("Access Denied: BSSID de l'environnement physique non autorisé.")
            return []
            
        records = self.db_manager.get_all_records()
        decrypted_secrets = []
        
        for record in records:
            plaintext = self.crypto_service.decrypt(record["ciphertext"], record["nonce"])
            if plaintext:
                try:
                    data = json.loads(plaintext)
                    data["_uuid"] = record["uuid"] # Pour référence dans l'UI
                    data["_updated_at"] = record["updated_at"]
                    decrypted_secrets.append(data)
                except json.JSONDecodeError:
                    print(f"Erreur de parsage JSON pour le record {record['uuid']}")
                    
        return decrypted_secrets
        
    def delete_secret(self, record_uuid: str) -> bool:
        """
        Action locale : Soft delete un secret.
        """
        if not self._check_access():
           print("Access Denied: BSSID interdit.")
           return False
           
        record = self.db_manager.get_record(record_uuid)
        if not record:
            return False
            
        # On ne change pas le ciphertext/nonce, on change juste l'état
        updated_record = self.db_manager.upsert_record_local(
            record_uuid=record_uuid,
            ciphertext=record["ciphertext"],
            nonce=record["nonce"],
            is_deleted=True
        )
        
        if self.on_sync_trigger:
            self.on_sync_trigger(updated_record)
            
        return True

    # ---- INTERFACE AVEC MODULE B (Réseau) ----

    def apply_remote_gossip(self, gossip_record: dict) -> bool:
        """
        Reçoit un record depuis le Module B (Network).
        On ne vérifie PAS le BSSID ici (le Vault peut recevoir des sync même verrouillé, 
        l'attaquant ne peut tout de même pas les lire sans Master Password et BSSID).
        Retourne True si appliqué.
        """
        return self.db_manager.process_gossip_update(gossip_record)
        
    def get_records_for_sync(self) -> List[dict]:
        """Retourne tous les records locaux pour la synchronisation initiale."""
        return self.db_manager.get_raw_records()
