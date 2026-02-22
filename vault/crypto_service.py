import os
import base64
from typing import Tuple, Optional
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256

class CryptoService:
    """Service gérant la cryptographie AES-GCM et la dérivation de clé."""
    
    def __init__(self, master_password: str, salt: bytes = b'p2p-safeguard-salt'):
        # On utilise un sel fixe (ou on pourrait le stocker dans config)
        self.salt = salt
        self.key = self._derive_key(master_password)
        
    def _derive_key(self, password: str) -> bytes:
        """Dérive une clé de 32 octets (256 bits) avec PBKDF2-HMAC-SHA256 (100k itérations)."""
        return PBKDF2(password, self.salt, dkLen=32, count=100000, hmac_hash_module=SHA256)
        
    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        """
        Chiffre une chaîne en AES-GCM.
        Retourne (ciphertext_b64, nonce_b64).
        """
        # Générer un nouveau nonce de 16 bytes pour AES GCM
        cipher = AES.new(self.key, AES.MODE_GCM)
        
        data = plaintext.encode('utf-8')
        ciphertext, tag = cipher.encrypt_and_digest(data)
        
        # Le résultat stocké est le tag concaténé au ciphertext
        # afin de s'assurer de l'intégrité lors du déchiffrement.
        encrypted_data = tag + ciphertext
        
        return (
            base64.b64encode(encrypted_data).decode('utf-8'),
            base64.b64encode(cipher.nonce).decode('utf-8')
        )
        
    def decrypt(self, ciphertext_b64: str, nonce_b64: str) -> Optional[str]:
        """
        Déchiffre une donnée AES-GCM.
        Vérifie l'intégrité (Authentication Tag).
        Retourne la chaîne en clair, ou None si échec.
        """
        try:
            encrypted_data = base64.b64decode(ciphertext_b64)
            nonce = base64.b64decode(nonce_b64)
            
            # Extraire le tag (16 octets) et le reste (ciphertext)
            tag = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            
            return plaintext.decode('utf-8')
        except (ValueError, KeyError) as e:
            # Échec du déchiffrement (mauvaise clé, données corrompues, tag invalide)
            print(f"Erreur de déchiffrement (potentiellement contexte invalide ou corruption) : {e}")
            return None
