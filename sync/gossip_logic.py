from typing import List, Dict, Tuple

class GossipLogic:
    """Implémente la logique métier du protocole Gossip (Path Vector)."""
    
    def __init__(self, my_node_id: str):
        self.my_node_id = my_node_id

    def build_gossip_message(self, record: dict, current_path_vector: List[str] = None) -> dict:
        """
        Construit un paquet réseau pour propager un record.
        Ajoute cet appareil (node_id) au vecteur de chemin pour éviter les boucles.
        """
        if current_path_vector is None:
            path_vector = [self.my_node_id]
        else:
            path_vector = list(current_path_vector)
            if self.my_node_id not in path_vector:
                path_vector.append(self.my_node_id)
                
        return {
            "type": "GOSSIP_UPDATE",
            "sender_id": self.my_node_id,
            "path_vector": path_vector,
            "payload": record
        }

    def build_sync_request(self) -> dict:
        """
        Construit un message pour demander à tous les pairs de nous pousser leur base de données.
        """
        return {
            "type": "SYNC_REQUEST",
            "sender_id": self.my_node_id
        }

    def should_process_message(self, message: dict) -> Tuple[bool, dict]:
        """
        Vérifie si le message doit être traité (pour éviter les boucles infinies).
        Retourne (is_valid, record_payload)
        """
        if not isinstance(message, dict) or message.get("type") != "GOSSIP_UPDATE":
            return False, {}
            
        path_vector = message.get("path_vector", [])
        
        # Feature B.1: Si je suis déjà dans le path vector, on droppe le message pour éviter les boucles circulaires.
        if self.my_node_id in path_vector:
            # print(f"GossipLogic : Message droppé, je suis déjà dans la boucle {path_vector}")
            return False, {}
            
        return True, message.get("payload", {})
