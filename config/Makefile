# Makefile for FortiGate Nextrade - Cloud Native Version
# Following CNCF best practices for build automation

# ============================================================================
# Configuration
# ============================================================================
APP_NAME := fortinet
VERSION := $(shell cat VERSION 2>/dev/null || echo "development")
REGISTRY := registry.jclee.me
IMAGE_NAME := $(REGISTRY)/$(APP_NAME)/nextrade
BUILD_DATE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Directories
SRC_DIR := src
BUILD_DIR := build
CMD_DIR := cmd
PKG_DIR := pkg
INTERNAL_DIR := internal
TEST_DIR := test

# Docker
DOCKERFILE := $(BUILD_DIR)/docker/Dockerfile
DOCKER_CONTEXT := .

# Kubernetes
K8S_NAMESPACE := fortinet
HELM_CHART := $(BUILD_DIR)/helm

# Python
PYTHON := python3
PIP := pip3
VENV := venv

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# ============================================================================
# Help
# ============================================================================
.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)FortiGate Nextrade - Cloud Native Build System$(NC)"
	@echo "$(BLUE)===============================================$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Examples:$(NC)"
	@echo "  make dev-setup     # Setup development environment"
	@echo "  make build         # Build container image"
	@echo "  make test          # Run all tests"
	@echo "  make deploy        # Deploy to Kubernetes"

# ============================================================================
# Development Environment
# ============================================================================
.PHONY: dev-setup
dev-setup: ## Setup development environment
	@echo "$(GREEN)Setting up development environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	./$(VENV)/bin/pip install --upgrade pip
	./$(VENV)/bin/pip install -r requirements.txt
	./$(VENV)/bin/pip install -e .
	@echo "$(GREEN)✅ Development environment ready$(NC)"
	@echo "$(YELLOW)Activate with: source $(VENV)/bin/activate$(NC)"

.PHONY: dev-run
dev-run: ## Run application in development mode
	@echo "$(GREEN)Starting development server...$(NC)"
	export APP_MODE=development && \
	export LOG_LEVEL=DEBUG && \
	$(PYTHON) $(CMD_DIR)/fortinet/main.py --web

.PHONY: dev-clean
dev-clean: ## Clean development environment
	@echo "$(GREEN)Cleaning development environment...$(NC)"
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

# ============================================================================
# Code Quality
# ============================================================================
.PHONY: format
format: ## Format code using black and isort
	@echo "$(GREEN)Formatting code...$(NC)"
	black $(SRC_DIR)/ $(CMD_DIR)/ $(PKG_DIR)/ $(INTERNAL_DIR)/
	isort $(SRC_DIR)/ $(CMD_DIR)/ $(PKG_DIR)/ $(INTERNAL_DIR)/

.PHONY: lint
lint: ## Lint code using flake8
	@echo "$(GREEN)Linting code...$(NC)"
	flake8 $(SRC_DIR)/ $(CMD_DIR)/ $(PKG_DIR)/ $(INTERNAL_DIR)/ --max-line-length=120 --ignore=E203,W503

.PHONY: security-scan
security-scan: ## Run security scans
	@echo "$(GREEN)Running security scans...$(NC)"
	bandit -r $(SRC_DIR)/ -f json -o security-report.json
	safety check --json --output safety-report.json
	@echo "$(GREEN)✅ Security scan complete. Check security-report.json and safety-report.json$(NC)"

.PHONY: quality
quality: format lint security-scan ## Run all code quality checks

# ============================================================================
# Testing
# ============================================================================
.PHONY: test-unit
test-unit: ## Run unit tests
	@echo "$(GREEN)Running unit tests...$(NC)"
	pytest $(TEST_DIR)/unit/ -v --cov=$(SRC_DIR) --cov-report=html --cov-report=xml

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	pytest $(TEST_DIR)/integration/ -v --timeout=60

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests
	@echo "$(GREEN)Running end-to-end tests...$(NC)"
	pytest $(TEST_DIR)/e2e/ -v --timeout=120

.PHONY: test
test: test-unit test-integration ## Run all tests except e2e

.PHONY: test-all
test-all: test-unit test-integration test-e2e ## Run all tests including e2e

# ============================================================================
# Container Operations
# ============================================================================
.PHONY: build
build: ## Build container image
	@echo "$(GREEN)Building container image...$(NC)"
	docker build \
		-f $(DOCKERFILE) \
		-t $(IMAGE_NAME):$(VERSION) \
		-t $(IMAGE_NAME):latest \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--build-arg VERSION=$(VERSION) \
		--build-arg VCS_REF=$(VCS_REF) \
		$(DOCKER_CONTEXT)
	@echo "$(GREEN)✅ Container image built: $(IMAGE_NAME):$(VERSION)$(NC)"

.PHONY: push
push: build ## Push container image to registry
	@echo "$(GREEN)Pushing container image...$(NC)"
	docker push $(IMAGE_NAME):$(VERSION)
	docker push $(IMAGE_NAME):latest
	@echo "$(GREEN)✅ Container image pushed to registry$(NC)"

.PHONY: run-container
run-container: ## Run container locally
	@echo "$(GREEN)Running container locally...$(NC)"
	docker run -it --rm \
		-p 7777:7777 \
		-e APP_MODE=development \
		-e LOG_LEVEL=DEBUG \
		$(IMAGE_NAME):latest

.PHONY: container-scan
container-scan: build ## Scan container for vulnerabilities
	@echo "$(GREEN)Scanning container for vulnerabilities...$(NC)"
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy image $(IMAGE_NAME):$(VERSION)

# ============================================================================
# Helm Operations
# ============================================================================
.PHONY: helm-lint
helm-lint: ## Lint Helm chart
	@echo "$(GREEN)Linting Helm chart...$(NC)"
	helm lint $(HELM_CHART)

.PHONY: helm-package
helm-package: helm-lint ## Package Helm chart
	@echo "$(GREEN)Packaging Helm chart...$(NC)"
	helm package $(HELM_CHART) --version $(VERSION) --app-version $(VCS_REF)
	@echo "$(GREEN)✅ Helm chart packaged$(NC)"

.PHONY: helm-install
helm-install: helm-package ## Install Helm chart locally
	@echo "$(GREEN)Installing Helm chart...$(NC)"
	helm upgrade --install $(APP_NAME) \
		./$(APP_NAME)-$(VERSION).tgz \
		--namespace $(K8S_NAMESPACE) \
		--create-namespace \
		--wait
	@echo "$(GREEN)✅ Helm chart installed$(NC)"

.PHONY: helm-uninstall
helm-uninstall: ## Uninstall Helm chart
	@echo "$(GREEN)Uninstalling Helm chart...$(NC)"
	helm uninstall $(APP_NAME) --namespace $(K8S_NAMESPACE)

# ============================================================================
# Kubernetes Operations
# ============================================================================
.PHONY: k8s-apply
k8s-apply: ## Apply Kubernetes manifests
	@echo "$(GREEN)Applying Kubernetes manifests...$(NC)"
	kubectl apply -f deployments/k8s/manifests/ --namespace $(K8S_NAMESPACE)

.PHONY: k8s-delete
k8s-delete: ## Delete Kubernetes resources
	@echo "$(GREEN)Deleting Kubernetes resources...$(NC)"
	kubectl delete -f deployments/k8s/manifests/ --namespace $(K8S_NAMESPACE) --ignore-not-found

.PHONY: k8s-status
k8s-status: ## Check Kubernetes deployment status
	@echo "$(GREEN)Checking deployment status...$(NC)"
	kubectl get pods,svc,ingress -n $(K8S_NAMESPACE)

.PHONY: k8s-logs
k8s-logs: ## Show application logs
	@echo "$(GREEN)Showing application logs...$(NC)"
	kubectl logs -l app=$(APP_NAME) -n $(K8S_NAMESPACE) --tail=100 -f

# ============================================================================
# Health Checks
# ============================================================================
.PHONY: health-check
health-check: ## Run health check
	@echo "$(GREEN)Running health check...$(NC)"
	$(PYTHON) $(CMD_DIR)/fortinet/main.py --health

.PHONY: version
version: ## Show version information
	@echo "$(GREEN)Version information:$(NC)"
	@echo "App Version: $(VERSION)"
	@echo "Git Commit: $(VCS_REF)"
	@echo "Build Date: $(BUILD_DATE)"
	@echo "Image: $(IMAGE_NAME):$(VERSION)"

# ============================================================================
# CI/CD Operations
# ============================================================================
.PHONY: ci-pipeline
ci-pipeline: quality test build container-scan helm-package ## Run full CI pipeline
	@echo "$(GREEN)✅ CI Pipeline completed successfully$(NC)"

.PHONY: deploy
deploy: push helm-install ## Deploy to Kubernetes cluster
	@echo "$(GREEN)✅ Deployment completed$(NC)"
	@echo "$(YELLOW)Check status with: make k8s-status$(NC)"

# ============================================================================
# Cleanup
# ============================================================================
.PHONY: clean
clean: dev-clean ## Clean all build artifacts
	@echo "$(GREEN)Cleaning build artifacts...$(NC)"
	docker rmi $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest 2>/dev/null || true
	rm -rf build/docker/.buildx-cache
	rm -f *.tgz
	rm -f security-report.json safety-report.json
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

# ============================================================================
# Documentation
# ============================================================================
.PHONY: docs
docs: ## Generate documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	@echo "$(YELLOW)Documentation generation not implemented yet$(NC)"

# Make help the default target
.DEFAULT_GOAL := help