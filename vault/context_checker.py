import os
import subprocess
import hashlib

class ContextChecker:
    """
    Interface modulaire pour vérifier le contexte (Proof of Location).
    Conçu pour s'adapter à différents OS via des stratégies.
    """
    def __init__(self, allowed_bssids_hashes):
        self.allowed_bssids_hashes = allowed_bssids_hashes
        self.os_type = os.environ.get('P2P_OS_TARGET', 'linux').lower()
        
    def get_current_bssid(self):
        """Récupère le BSSID courant selon l'OS configuré."""
        mock_bssid = os.environ.get('P2P_MOCK_BSSID')
        if mock_bssid:
            return mock_bssid.upper()
            
        if self.os_type == 'linux':
            return self._get_bssid_linux()
        elif self.os_type == 'windows':
            return self._get_bssid_windows()
        else:
            raise NotImplementedError(f"OS non supporté pour la récupération du BSSID : {self.os_type}")

    def _get_bssid_linux(self):
        """Stratégie pour Linux (utilise iwgetid pour plus de rapidité)."""
        try:
            # iwgetid -a est quasi-instantané (10ms) contrairement à nmcli (4s)
            result = subprocess.run(
                ["iwgetid", "-a"], 
                capture_output=True, text=True, check=True
            )
            # Sortie typique : wlan0     Access Point/Cell: B6:52:7A:02:72:2C
            for line in result.stdout.splitlines():
                if "Cell:" in line:
                    return line.split("Cell:")[1].strip().replace('\\', '').upper()
            return None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _get_bssid_windows(self):
        """Stratégie pour Windows (utilise netsh)."""
        try:
            # Exemple pour Windows 
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, check=True
            )
            for line in result.stdout.splitlines():
                if "BSSID" in line:
                    bssid = line.split(":", 1)[1].strip().upper()
                    return bssid
            return None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _hash_bssid(self, bssid):
        """Hash le BSSID avec SHA-256 pour le comparer avec config.json."""
        if not bssid:
            return None
        return hashlib.sha256(bssid.encode('utf-8')).hexdigest()

    def is_context_valid(self):
        """
        Vérifie si le BSSID courant correspond à un des BSSID autorisés.
        """
        current_bssid = self.get_current_bssid()
        if not current_bssid:
            print("Erreur : Impossible de récupérer le BSSID courant.")
            return False
            
        hashed_bssid = self._hash_bssid(current_bssid)
        if hashed_bssid not in self.allowed_bssids_hashes:
            print(f"Erreur : BSSID actuel ({current_bssid}) non reconnu.")
            print(f"Son Hash (SHA-256) : {hashed_bssid}")
            print("Veuillez rajouter ce hash dans 'allowed_bssids_hashes' (config.json).")
            return False
            
        return True
