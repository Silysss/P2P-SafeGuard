.PHONY: help cli test-unit test-func test-all docker-up docker-down clean

# Définition de l'image Docker de test (le Noeud 1 utilisé par défaut par le docker-compose)
TEST_IMAGE=p2p-safeguard-node1:latest
DOCKER_CMD=docker run --rm -v $(shell pwd):/app -w /app $(TEST_IMAGE)

help:
	@echo "--- P2P-SafeGuard : Available Commands ---"
	@echo "Usage : make <target>"
	@echo ""
	@echo "1. Local Execution :"
	@echo "  make cli          Launch the interactive CLI script (main.py)"
	@echo ""
	@echo "2. Automated Tests (Dockerized) :"
	@echo "  make test-unit    Run unit tests (Crypto, Gossip logic)"
	@echo "  make test-func    Run functional tests (Vault initialization/reset/login)"
	@echo "  make test-all     Run all validation tests sequentially"
	@echo ""
	@echo "3. Integration Cluster (3-Node P2P) :"
	@echo "  make docker-up    Build and launch the background simulation cluster"
	@echo "  make docker-down  Gracefully stop and remove simulation containers"
	@echo "  make docker-exec n=X  Attach to the CLI Interface of Node <X> (X=1, 2 or 3)"
	@echo ""
	@echo "4. Utilities :"
	@echo "  make clean        Delete local vault*.json databases"

## ====== Local Execution ======
cli:
	@echo "Launching P2P-SafeGuard locally..."
	./venv/bin/python main.py

## ====== Tests (Dockerized) ======
test-unit:
	@echo "Running unit tests inside a sandbox container..."
	docker compose build node1
	$(DOCKER_CMD) python -m unittest tests/test_unit.py -v

test-func:
	@echo "Running functional tests inside a sandbox container..."
	docker compose build node1
	$(DOCKER_CMD) python -m unittest tests/test_functional_vault.py -v

test-all: test-unit test-func
	@echo "\n=== All tests passed successfully ! ==="

## ====== Cluster (Docker Compose) ======
docker-up:
	@echo "Starting P2P-SafeGuard cluster..."
	docker compose up -d --build

docker-down:
	@echo "Stopping P2P-SafeGuard cluster..."
	docker compose down

docker-exec:
	@if [ -z "$(n)" ]; then \
		echo "Error: Please specify a node number with n=... (Ex: make docker-exec n=1)"; \
	else \
		echo "Connecting to the interface of Node $(n)..."; \
		docker compose exec -it node$(n) python main.py --cli; \
	fi

## ====== Cleanup ======
clean:
	@echo "Cleaning local database files..."
	rm -f vault*.json
