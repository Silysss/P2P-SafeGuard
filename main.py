import sys
import os
import json
import time

try:
    import questionary
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("Veuillez installer les dépendances depuis l'environnement venv (questionary, rich).")
    sys.exit(1)

from vault.vault_core import VaultCore
from sync.network_core import NetworkCore

console = Console()

def run_cli(vault: VaultCore, network: NetworkCore):
    """Interface CLI améliorée avec questionary et rich."""
    while True:
        try:
            console.clear()
            console.print("\n[bold cyan]--- P2P-SafeGuard ---[/bold cyan]")
            choix = questionary.select(
                "Que souhaitez-vous faire ?",
                choices=[
                    "1. Ajouter/Modifier un secret",
                    "2. Lister les secrets",
                    "3. Rechercher un secret",
                    "4. Supprimer un secret",
                    "5. Quitter"
                ]
            ).ask()

            if not choix or choix.startswith("5"):
                console.print("[yellow]Fermeture de l'interface.[/yellow]")
                sys.exit(0)
                
            elif choix.startswith("1"):
                service = questionary.text("Service (ex: Google) :").ask()
                if not service: continue
                username = questionary.text("Username :").ask()
                password = questionary.password("Password :").ask()
                notes = questionary.text("Notes (optionnel) :").ask()
                
                if vault.add_or_update_secret(service, username, password, notes):
                    console.print(f"[green]✔ Secret pour '{service}' sauvegardé et propagé.[/green]")
                else:
                    console.print("[red]✖ Échec de la sauvegarde.[/red]")
                input("\nAppuyez sur <Entrée> pour continuer...")
                    
            elif choix.startswith("2"):
                secrets = vault.get_all_secrets_decrypted()
                if not secrets:
                    input("\n(Aucun secret). Appuyez sur <Entrée> pour retourner au menu...")
                    continue
                    
                table = Table(title="Vos Secrets P2P-SafeGuard")
                table.add_column("UUID", style="dim", width=8)
                table.add_column("Service", style="cyan")
                table.add_column("Username", style="magenta")
                table.add_column("Password", style="green")
                table.add_column("Notes", style="white")
                
                for s in secrets:
                    table.add_row(s['_uuid'][:8], s['service'], s['username'], s['password'], s.get('notes', ''))
                console.print(table)
                input("\nAppuyez sur <Entrée> pour continuer...")
                
            elif choix.startswith("3"):
                query = questionary.text("Recherche (service ou username) :").ask()
                if not query: continue
                secrets = vault.get_all_secrets_decrypted()
                found = [s for s in secrets if query.lower() in s['service'].lower() or query.lower() in s['username'].lower()]
                
                if not found:
                    console.print("[yellow]Aucun résultat trouvé.[/yellow]")
                    input("\nAppuyez sur <Entrée> pour continuer...")
                    continue
                    
                table = Table(title=f"Résultats pour '{query}'")
                table.add_column("UUID", style="dim", width=8)
                table.add_column("Service", style="cyan")
                table.add_column("Username", style="magenta")
                table.add_column("Password", style="green")
                
                for s in found:
                    table.add_row(s['_uuid'][:8], s['service'], s['username'], s['password'])
                console.print(table)
                input("\nAppuyez sur <Entrée> pour continuer...")
                
            elif choix.startswith("4"):
                secrets = vault.get_all_secrets_decrypted()
                if not secrets:
                    input("\n(Aucun secret). Appuyez sur <Entrée> pour retourner au menu...")
                    continue
                    
                choices_list = [f"{s['service']} ({s['username']}) - {s['_uuid']}" for s in secrets]
                choices_list.append("Annuler")
                
                to_delete = questionary.select("Sélectionnez le secret à supprimer :", choices=choices_list).ask()
                if to_delete and to_delete != "Annuler":
                    uuid_str = to_delete.split(" - ")[-1]
                    if vault.delete_secret(uuid_str):
                        console.print(f"[green]✔ Secret {uuid_str[:8]} supprimé avec succès (Soft delete propagé).[/green]")
                    else:
                        console.print("[red]✖ Échec de la suppression.[/red]")
                    input("\nAppuyez sur <Entrée> pour continuer...")
                        
        except KeyboardInterrupt:
            console.print("\n[yellow]Arrêt manuel.[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[red]Erreur UI : {e}[/red]")

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
                console.print("\n[bold magenta]=== NOUVEAU VAULT P2P-SAFEGUARD ===[/bold magenta]")
                console.print("[italic]Il s'agit du premier lancement. Vous devez configurer votre Vault.[/italic]")
                master_password = questionary.password("Choisissez votre Password Master (Fort) :").ask()
                if not master_password: sys.exit(0)
            else:
                master_password = questionary.password("Master Password :").ask()
                if not master_password: sys.exit(0)
        except EOFError:
            console.print("[red]Erreur : Master password requis (EOF).[/red]")
            sys.exit(1)

    console.print(f"Démarrage {node_id} sur le port {port}...")

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
