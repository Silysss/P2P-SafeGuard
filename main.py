import sys
import os
import json
import time

from vault.vault_core import VaultCore
from sync.network_core import NetworkCore

def run_cli(vault: VaultCore, network: NetworkCore):
    """Interface CLI très basique (PoC)."""
    while True:
        try:
            print("\n--- P2P-SafeGuard ---")
            print("1. Ajouter/Modifier un secret")
            print("2. Lister les secrets")
            print("3. Quitter")
            choix = input("Choix : ")
            
            if choix == "1":
                service = input("Service (ex: Google) : ")
                username = input("Username : ")
                password = input("Password : ")
                notes = input("Notes : ")
                # L'add local triggera automatiquement le trigger_gossip vers les pairs
                vault.add_or_update_secret(service, username, password, notes)
                
            elif choix == "2":
                print("Affichage (si vous êtes sur le bon Wi-Fi) :")
                secrets = vault.get_all_secrets_decrypted()
                if secrets:
                    for s in secrets:
                        print(f"[{s['_uuid']}] {s['service']} | {s['username']} : {s['password']}")
                else:
                    print("(Aucun secret ou accès refusé)")
            elif choix == "3":
                print("Fermeture de l'interface.")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\nArrêt manuel.")
            sys.exit(0)
        except Exception as e:
            print(f"Erreur UI : {e}")

def main():
    # 1. Charger la config
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Fichier config.json introuvable.")
        sys.exit(1)

    node_id = config.get("node_id", "Unknown_Device")
    host = config.get("host", "0.0.0.0")
    port = config.get("port", 5000)
    peers = config.get("peers", [])
    allowed_bssids = config.get("allowed_bssids_hashes", [])
    
    db_path = "vault.json"

    # Vérifier l'état de la base de données
    is_new_vault = not os.path.exists(db_path)

    master_password = os.environ.get("P2P_MASTER_PASSWORD")
    if not master_password:
        try:
            if is_new_vault:
                print("\n=== NOUVEAU VAULT P2P-SAFEGUARD ===")
                print("Il s'agit du premier lancement. Vous devez configurer votre Vault.")
                master_password = input("Choisissez votre Password Master (Fort) : ")
            else:
                master_password = input("Master Password : ")
        except EOFError:
            print("Erreur : Master password requis (EOF). Utilisez l'environnement P2P_MASTER_PASSWORD.")
            sys.exit(1)

    print(f"Démarrage {node_id} sur le port {port}...")

    # 2. Initialisation Vault
    try:
        vault = VaultCore(
            master_password=master_password,
            allowed_bssids_hashes=allowed_bssids,
            db_path=db_path
        )
    except ValueError:
        print("\n[ERREUR FATALE] Impossible de déverrouiller le Vault : Mot de passe incorrect ou base corrompue.")
        sys.exit(1)

    # 3. Initialisation Network (qui injecte dans le Vault les messages entrants)
    network = NetworkCore(
        node_id=node_id,
        host=host,
        port=port,
        peers=peers,
        apply_gossip_callback=vault.apply_remote_gossip,
        get_all_records_callback=vault.get_records_for_sync
    )

    # Lier le Vault au Network (le Vault prévient le réseau quand y'a une maj LOCALE)
    vault.on_sync_trigger = network.trigger_local_update

    # 4. Lancer le serveur TCP asynchrone
    network.start()
    
    # 5. Demander un sync aux pairs (Feature : Récupération du setup depuis un autre noeud)
    network.request_sync()
    
    # 5. Lancer l'UI / CLI ou mode Daemon
    if sys.stdin.isatty():
        run_cli(vault, network)
    else:
        print("Mode Daemon activé (pas de console interactive).")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass
    
    # 6. Extinction propre
    print("Arrêt du daemon...")
    network.stop()

if __name__ == "__main__":
    main()
