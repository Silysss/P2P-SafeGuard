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

if __name__ == "__main__":
    unittest.main()
