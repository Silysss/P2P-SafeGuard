.PHONY: help cli test-unit test-func test-all docker-up docker-down clean

# Définition de l'image Docker de test (le Noeud 1 utilisé par défaut par le docker-compose)
TEST_IMAGE=p2p-safeguard-node1:latest
DOCKER_CMD=docker run --rm -v $(shell pwd):/app -w /app $(TEST_IMAGE)

help:
	@echo "--- P2P-SafeGuard : Commandes Disponibles ---"
	@echo "Utilisation : make <cible>"
	@echo ""
	@echo "1. Exécution Locale :"
	@echo "  make cli          Lancer le script principal interactif (main.py)"
	@echo ""
	@echo "2. Tests Automatisés (sous Docker) :"
	@echo "  make test-unit    Lancer les tests unitaires (Crypto, Gossip logic)"
	@echo "  make test-func    Lancer les tests fonctionnels (Création/Reset/Login de Vault.json)"
	@echo "  make test-all     Enchainer tous les tests de validation"
	@echo ""
	@echo "3. Cluster d'Intégration (3 noeuds P2P) :"
	@echo "  make docker-up    Bâtir et lancer le cluster de test asynchrone en arrière-plan"
	@echo "  make docker-down  Arrêter et supprimer proprement les conteneurs de test"
	@echo ""
	@echo "4. Utilitaires :"
	@echo "  make clean        Supprimer les bases de données vault*.json locales"

## ====== Exécution Locale ======
cli:
	@echo "Lancement de P2P-SafeGuard en local..."
	python main.py

## ====== Tests (Dockerisés) ======
test-unit:
	@echo "Exécution des tests unitaires dans un conteneur vierge..."
	docker compose build node1
	$(DOCKER_CMD) python -m unittest tests/test_unit.py -v

test-func:
	@echo "Exécution des tests fonctionnels dans un conteneur vierge..."
	docker compose build node1
	$(DOCKER_CMD) python -m unittest tests/test_functional_vault.py -v

test-all: test-unit test-func
	@echo "\n=== Tous les tests ont été validés avec succès ! ==="

## ====== Cluster (Docker Compose) ======
docker-up:
	@echo "Démarrage du cluster P2P-SafeGuard..."
	docker compose up -d --build

docker-down:
	@echo "Arrêt du cluster P2P-SafeGuard..."
	docker compose down

## ====== Nettoyage ======
clean:
	@echo "Nettoyage des fichiers locaux de base de données..."
	rm -f vault*.json
