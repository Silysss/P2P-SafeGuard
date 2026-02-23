import os
import subprocess
import time
import json
import unittest

class TestVaultFunctional(unittest.TestCase):
    """
    Test fonctionnel du Vault via l'exécution complète du système (main.py).
    Conçu pour tourner dans un container Docker éphémère.
    """
    DB_PATH = "vault.json"

    def setUp(self):
        # On s'assure d'avoir un espace de travail vierge pour chaque test
        if os.path.exists(self.DB_PATH):
            os.remove(self.DB_PATH)

    def tearDown(self):
        # Nettoyage
        if os.path.exists(self.DB_PATH):
            os.remove(self.DB_PATH)

    def _run_main_background(self, password: str, timeout: int = 2):
        """Lance l'app en arrière-plan et la tue après `timeout` secondes."""
        env = os.environ.copy()
        env["P2P_MASTER_PASSWORD"] = password
        env["P2P_MOCK_BSSID"] = "MOCK_TEST_BSSID"
        
        process = subprocess.Popen(
            ["python", "main.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(timeout) # Laisser le temps à network.start() et VaultCore de run
        process.terminate()
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr

    def _run_main_foreground(self, password: str):
        """Lance l'app et attend qu'elle finisse toute seule (pratique pour tester les crashs)."""
        env = os.environ.copy()
        env["P2P_MASTER_PASSWORD"] = password
        env["P2P_MOCK_BSSID"] = "MOCK_TEST_BSSID"
        
        return subprocess.run(
            ["python", "main.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )

    def test_1_create_new_vault(self):
        """1. Création d'un nouveau vault"""
        # Le lancement s'effectue et se termine après 2 sec
        self._run_main_background("mon_super_mdp")
        
        # Vérification 1 : Le fichier json a été produit sur le disque
        self.assertTrue(os.path.exists(self.DB_PATH), "Le fichier vault.json n'a pas été créé lors de l'initialisation.")
        
        # Vérification 2 : Le système cryptographique a bien inséré le jeton de vérification
        with open(self.DB_PATH, "r") as f:
            data = json.load(f)
        self.assertIn("password_check", data, "Le Vault a été créé mais le jeton de mot de passe est manquant.")

    def test_2_detect_deleted_vault(self):
        """2. Détection d'un vault supprimé et création d'un nouveau profil"""
        # --- Etape A : On crée un vault initial ---
        self._run_main_background("mdp_init")
        with open(self.DB_PATH, "r") as f:
            data_init = json.load(f)
            id_init = data_init["vault_id"]
        
        # --- Etape B : On simule la perte ou suppression du fichier db ---
        os.remove(self.DB_PATH)
        self.assertFalse(os.path.exists(self.DB_PATH))
        
        # --- Etape C : On redémarre l'application ---
        self._run_main_background("nouveau_mdp")
        self.assertTrue(os.path.exists(self.DB_PATH), "Le système n'a pas réagi à la suppression de la BDD et n'en a pas recréé.")
        
        with open(self.DB_PATH, "r") as f:
            data_rebuild = json.load(f)
            id_rebuild = data_rebuild["vault_id"]
            
        # L'identifiant interne du Vault ("vault_id" UUIDv4) doit obligatoirement avoir changé
        self.assertNotEqual(id_init, id_rebuild, "Le système a repris un ancien ID au lieu de générer un vault complètement neuf.")

    def test_3_bad_password(self):
        """3. Refus d'accès avec un mauvais mot de passe"""
        # On initialise une base légitime
        self._run_main_background("le_vrai_mdp")
        
        # On relance l'application avec un mot de passe frauduleux
        res = self._run_main_foreground("le_mauvais_mdp")
        
        # Le programme DOIT avoir quitté avec une erreur (Exit code 1) et renvoyé le message fatal
        self.assertEqual(res.returncode, 1, "Le programme devrait interdire l'accès et quitter avec le code 1.")
        self.assertIn("[ERREUR FATALE]", res.stdout, "Le lancement n'a pas affiché le traceback utilisateur formaté.")

if __name__ == '__main__':
    unittest.main()
