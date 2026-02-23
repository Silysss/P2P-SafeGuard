import unittest
import os
import time
import sys

# Ajouter le chemin racine pour l'import des modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vault.crypto_service import CryptoService
from sync.gossip_logic import GossipLogic

class TestP2PSafeGuard(unittest.TestCase):
    def test_crypto_service(self):
        crypto = CryptoService("mon_super_password")
        
        # Test de chiffrement
        secret_data = '{"service": "Google", "username": "user", "password": "123"}'
        ciphertext, nonce = crypto.encrypt(secret_data)
        
        self.assertNotEqual(secret_data, ciphertext)
        self.assertTrue(len(ciphertext) > 0)
        self.assertTrue(len(nonce) > 0)
        
        # Test de déchiffrement
        plaintext = crypto.decrypt(ciphertext, nonce)
        self.assertEqual(plaintext, secret_data)
        
        # Test de corruption
        bad_ciphertext = ciphertext[:-4] + "AAAA" # Corruption du tag GCM ou des données
        failed_plaintext = crypto.decrypt(bad_ciphertext, nonce)
        self.assertIsNone(failed_plaintext)

    def test_gossip_logic_path_vector(self):
        logic = GossipLogic("Node_A")
        
        # Nouveau message
        record = {"uuid": "123", "data": "test"}
        msg = logic.build_gossip_message(record, ["Node_B", "Node_C"])
        
        self.assertEqual(msg["sender_id"], "Node_A")
        self.assertIn("Node_A", msg["path_vector"])
        self.assertEqual(len(msg["path_vector"]), 3)
        
        # Test should_process_message avec boucle
        loop_msg = {
            "type": "GOSSIP_UPDATE",
            "path_vector": ["Node_X", "Node_A", "Node_Y"],
            "payload": record
        }
        should_process, payload = logic.should_process_message(loop_msg)
        self.assertFalse(should_process) # Doit refuser car Node_A est dans le vecteur de chemin
        
        # Test should_process_message sans boucle
        valid_msg = {
            "type": "GOSSIP_UPDATE",
            "path_vector": ["Node_X", "Node_Y"],
            "payload": record
        }
        should_process, payload = logic.should_process_message(valid_msg)
        self.assertTrue(should_process)
        self.assertEqual(payload, record)

    def test_vault_core_crud(self):
        """Test de la logique métier Ajout / Liste / Suppression logicielle du Vault"""
        from vault.vault_core import VaultCore
        import hashlib
        
        # Mock de l'environnement physique
        os.environ['P2P_MOCK_BSSID'] = "TEST_BSSID"
        mock_hash = hashlib.sha256(b"TEST_BSSID").hexdigest()
        
        test_db = "test_crud_vault.json"
        if os.path.exists(test_db): os.remove(test_db)
            
        try:
            vault = VaultCore("test_pwd", allowed_bssids_hashes=[mock_hash], db_path=test_db)
            
            # 1. Ajout de secrets
            vault.add_or_update_secret("Github", "milo", "123", "notes")
            vault.add_or_update_secret("Twitter", "milo", "abc", "")
            
            secrets = vault.get_all_secrets_decrypted()
            self.assertEqual(len(secrets), 2, "Il devrait y avoir 2 secrets.")
            
            # Recherche locale (comportement simulé de la CLI)
            search_res = [s for s in secrets if "twit" in s["service"].lower()]
            self.assertEqual(len(search_res), 1)
            self.assertEqual(search_res[0]["service"], "Twitter")
            
            uuid_twitter = search_res[0]["_uuid"]
            
            # 2. Suppression d'un secret (Soft delete)
            res = vault.delete_secret(uuid_twitter)
            self.assertTrue(res, "La suppression devrait retourner True")
            
            # 3. Vérification de la non-exposition
            secrets_after = vault.get_all_secrets_decrypted()
            self.assertEqual(len(secrets_after), 1, "Le secret supprimé ne doit plus être listé.")
            self.assertEqual(secrets_after[0]["service"], "Github")
            
        finally:
            # Nettoyage
            if os.path.exists(test_db):
                os.remove(test_db)

if __name__ == "__main__":
    unittest.main()
