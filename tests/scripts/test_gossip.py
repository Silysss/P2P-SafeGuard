import socket
import json
import time
import sys

def send_message(ip, port, message):
    try:
        with socket.create_connection((ip, port), timeout=2.0) as sock:
            data = json.dumps(message).encode('utf-8')
            sock.sendall(data)
            return True
    except Exception as e:
        print(f"Erreur d'envoi vers {ip}:{port} : {e}")
        return False

if __name__ == "__main__":
    is_lww = len(sys.argv) > 1 and sys.argv[1] == "lww"
    timestamp = 1000.0 if is_lww else time.time()
    
    if is_lww:
        print("Test Résolution LWW: on envoie un vieux record...")
        
    gossip_msg = {
        "type": "GOSSIP_UPDATE",
        "sender_id": "TestScript",
        "path_vector": ["TestScript"],
        "payload": {
            "uuid": "dede1111-2222-3333-4444-555566667777",
            "updated_at": timestamp,
            "is_deleted": False,
            "nonce": "test_nonce_base64_for_docker",
            "ciphertext": "test_ciphertext_base64_for_docker"
        }
    }

    # On envoie vers le Node 1 accessible sur localhost:5001 grâce au port mapping Docker
    print("Envoi vers localhost:5001...")
    success = send_message("127.0.0.1", 5001, gossip_msg)
    if success:
        print(f"Message envoyé (timestamp: {timestamp}). Vérifiez si 'vaccin_node2.json' et 'vaccin_node3.json' le contiennent !")
    else:
        print("Échec de l'envoi.")
