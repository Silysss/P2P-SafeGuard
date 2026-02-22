import socket
import json
import logging

class SocketClient:
    """Client TCP P2P pour envoyer les mises à jour de Gossip aux pairs distants."""
    def __init__(self, timeout: float = 2.0):
        # Timeout court pour ne pas bloquer si un pair est hors ligne
        self.timeout = timeout

    def send_message(self, target_ip: str, target_port: int, message: dict) -> bool:
        """
        Envoie un message JSON (GOSSIP_UPDATE) à un pair cible de manière synchrone.
        Retourne True si l'envoi a réussi, False sinon.
        """
        try:
            with socket.create_connection((target_ip, target_port), timeout=self.timeout) as sock:
                # Conversion du dict en JSON puis en bytes UTF-8
                data = json.dumps(message).encode('utf-8')
                sock.sendall(data)
                return True
        except (socket.timeout, socket.error):
            # C'est normal dans un système P2P qu'un pair soit off, on l'ignore silencieusement.
            return False
