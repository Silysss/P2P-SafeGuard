import threading
from typing import List, Dict, Callable

from .socket_server import SocketServer
from .socket_client import SocketClient
from .gossip_logic import GossipLogic

class NetworkCore:
    """
    Contrôleur principal du Module B (Réseau & Sync).
    Fait le lien entre le Serveur, le Client, la logique Gossip, et le Vault local.
    """
    def __init__(self, node_id: str, host: str, port: int, peers: List[Dict[str, int]], 
                 apply_gossip_callback: Callable[[dict], bool],
                 get_all_records_callback: Callable[[], List[dict]]):
        self.node_id = node_id
        self.peers = peers # Liste de dictionnaires ex: [{'ip': '127.0.0.1', 'port': 5001}]
        self.apply_gossip_callback = apply_gossip_callback
        self.get_all_records_callback = get_all_records_callback
        
        self.gossip_logic = GossipLogic(node_id)
        self.server = SocketServer(host, port, self._on_message_received)
        self.client = SocketClient()

    def start(self):
        """Démarre le serveur réseau."""
        self.server.start()

    def stop(self):
        """Arrête le serveur réseau."""
        self.server.stop()

    def _on_message_received(self, message: dict):
        """
        Appelé quand le serveur TCP reçoit un message.
        Logique de réception et vérification Gossip.
        """
        if message.get("type") == "SYNC_REQUEST":
            sender_id = message.get("sender_id")
            # Un pair nous demande tout notre catalogue, on lui broadcast toutes nos entrées en individuel
            if sender_id and sender_id != self.node_id:
                for record in self.get_all_records_callback():
                    self.trigger_local_update(record)
            return

        should_process, record_payload = self.gossip_logic.should_process_message(message)
        
        if not should_process:
            return # Boucle P2P empêchée ou format invalide

        # Transmettre le record au Vault pour appliquer le LWW (Time check)
        # Si le record est plus récent que le local (ou nouveau), on l'applique et on le propage aux autres pairs
        is_applied = self.apply_gossip_callback(record_payload)
        
        if is_applied:
            # Si le Vault l'a accepté (plus récent), on doit le propager avec notre ID ajouté au path_vector
            path_vector = message.get("path_vector", [])
            new_message = self.gossip_logic.build_gossip_message(record_payload, path_vector)
            self._propagate_to_peers(new_message)

    def trigger_local_update(self, new_record: dict):
        """
        Appelé depuis le Vault (Interface A -> B).
        L'utilisateur local a fait une mise à jour, on l'envoie en broadcast à tous les pairs.
        """
        message = self.gossip_logic.build_gossip_message(new_record)
        self._propagate_to_peers(message)

    def request_sync(self):
        """
        Appelé au démarrage : broadcast un SYNC_REQUEST pour récupérer l'historique des pairs.
        """
        message = self.gossip_logic.build_sync_request()
        self._propagate_to_peers(message)

    def _propagate_to_peers(self, message: dict):
        """Envoie le message P2P à tous les pairs de la configuration."""
        for peer in self.peers:
            # Lancement asynchrone pour ne pas bloquer si un pair est lent
            threading.Thread(
                target=self._send_to_peer,
                args=(peer["ip"], peer["port"], message),
                daemon=True
            ).start()

    def _send_to_peer(self, ip: str, port: int, message: dict):
        success = self.client.send_message(ip, port, message)
        if not success:
            pass # Logs optionnels: print(f"Impossible de joindre le pair {ip}:{port}")
