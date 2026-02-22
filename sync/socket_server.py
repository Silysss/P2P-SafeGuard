import socket
import threading
import json
from typing import Callable

class SocketServer:
    """Serveur TCP P2P écoutant les mises à jour Gossip entrantes dans des threads."""
    def __init__(self, host: str, port: int, on_message_received: Callable[[dict], None]):
        self.host = host
        self.port = port
        self.on_message_received = on_message_received
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.is_running = False

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.is_running = True
        print(f"Serveur TCP en écoute sur {self.host}:{self.port}")

        # Lancer le listener dans un thread dédié pour ne pas bloquer l'application
        listener_thread = threading.Thread(target=self._accept_loop, daemon=True)
        listener_thread.start()

    def _accept_loop(self):
        while self.is_running:
            try:
                client_sock, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
            except Exception as e:
                # Éviter d'afficher l'erreur si on a forcé l'arrêt du serveur
                if self.is_running:
                    print(f"Erreur d'acceptation connexion : {e}")

    def _handle_client(self, client_sock: socket.socket):
        try:
            # Réception du payload JSON
            data = client_sock.recv(65535)
            if data:
                message = json.loads(data.decode('utf-8'))
                # Transmission au callback du protocole Gossip
                self.on_message_received(message)
        except json.JSONDecodeError:
            print("Erreur : Message reçu invalide (pas au format JSON)")
        except Exception as e:
            print(f"Erreur de gestion client : {e}")
        finally:
            client_sock.close()

    def stop(self):
        self.is_running = False
        try:
            self.server_socket.close()
        except:
            pass
