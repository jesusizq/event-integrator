# Makefile for event-integrator

# Default shell
SHELL := /bin/bash

# Service name in docker-compose
APP_SERVICE_NAME := app

# Get the directory of the run.sh script
RUN_SH_DIR := $(shell dirname $(realpath ./docker/run.sh))
RUN_SH := ./docker/run.sh

# Variable for log target, defaults to APP_SERVICE_NAME, can be overridden
# Example: make logs service=worker
service ?= $(APP_SERVICE_NAME)

COMPOSE_COMMAND := docker compose -f $(RUN_SH_DIR)/docker-compose.yml
# Use default .env from project root if not test_env
# $(RUN_SH_DIR) is the .../docker directory. We need to go one level up for the .env file.
ENV_FILE_ARG := --env-file $(RUN_SH_DIR)/../.env
ifeq ($(test_env),true)
    ENV_FILE_ARG := --env-file $(RUN_SH_DIR)/../.env.test
endif

.PHONY: help install lint test run-local run-worker-local build up down clean logs exec-app create-migration migrate up-debug init-migrations

help:
	@echo "Available Commands:"
	@echo "  install            : Install dependencies using poetry."
	@echo "  lint               : Run linters (flake8, black --check)."
	@echo "  black              : Run black formatter."
	@echo "  test               : Run pytest tests against app container (requires test env setup)."
	@echo "  run-local          : Run Flask development server locally (requires local env setup)."
	@echo "  run-worker-local   : Run Celery worker locally (requires local env setup)."
	@echo "  build [test_env=true] : Build docker images using run.sh."
	@echo "  up [test_env=true] : Start docker services in detached mode (default dev env). Use test_env=true for test env."
	@echo "  up-debug [test_env=true] : Start docker services in detached mode (default dev env) without app container (for debugging)."
	@echo "  down               : Stop docker services using run.sh."
	@echo "  clean              : Stop and remove docker containers/volumes/images using run.sh."
	@echo "  logs service=<name> : Follow logs for a specific service (default: app)."
	@echo "  exec-app cmd=\"...\" : Execute a command inside the app container."
	@echo "  create-migration message=\"...\" : Create a new database migration script (uses default .env unless test_env=true)."
	@echo "  migrate [test_env=true] : Apply database migrations (uses default .env unless test_env=true)."
	@echo "  init-migrations    : Initialize the database migration environment (one-time setup)."

install:
	poetry install

lint:
	poetry run flake8 app tests
	poetry run black --check app tests

black:
	poetry run black app tests

# Test target: brings up services in 'test' environment and runs pytest
test:
	@echo "INFO: Preparing 'test' environment and running tests... (ensure you have made: source .env.test)"
	@echo "INFO: Cleaning up existing test environment (if any) using $(RUN_SH)..."
	sh $(RUN_SH) -e test down-and-remove
	@echo "INFO: Starting 'test' environment using $(RUN_SH)... This might take a moment."
	sh $(RUN_SH) -e test -d up
	@echo "INFO: 'test' environment started. Executing tests..."
	poetry run pytest
	@echo "---------------------------------------------------------------------"
	@echo "INFO: Pytest execution finished."
	@echo "INFO: Docker services started for testing are still running in 'test' environment."
	@echo "INFO: To stop all services: make down"
	@echo "INFO: To stop services specifically for 'test' env: sh $(RUN_SH) -e test down"
	@echo "---------------------------------------------------------------------"

# Assumes services are running (use 'make up')
run-local:
	poetry run flask run

run-worker-local:
	poetry run celery -A run.celery worker --loglevel=info

build:
ifeq ($(test_env),true)
	sh $(RUN_SH) -e test build
else
	sh $(RUN_SH) build
endif
	@echo "Build completed via run.sh"

up:
ifeq ($(test_env),true)
	@echo "INFO: Starting services in 'test' environment..."
	sh $(RUN_SH) -e test up
else
	@echo "INFO: Starting services in default (dev) environment..."
	sh $(RUN_SH) up
endif

up-debug:
ifeq ($(test_env),true)
	@echo "INFO: Starting 'test' environment dependencies for debugging app..."
	$(COMPOSE_COMMAND) ${ENV_FILE_ARG} up -d --build --scale app=0 --remove-orphans
else
	@echo "INFO: Starting default (dev) environment dependencies for debugging app..."
	$(COMPOSE_COMMAND) $(ENV_FILE_ARG) up -d --build --scale app=0 --remove-orphans
endif
	@echo "---------------------------------------------------------------------"
	@echo "INFO: Dependencies started."
	@echo "INFO: 'app' service is NOT running (scaled to 0)."
	@echo "INFO: You can debug now running the Flask app by yourself with the appropriate environment variables."
	@echo "---------------------------------------------------------------------"

down:
	sh $(RUN_SH) down

clean:
	sh $(RUN_SH) down-and-remove

logs:
	$(COMPOSE_COMMAND) logs -f $(service)

exec-app:
	@if [ -z "$(cmd)" ]; then echo "Command missing. Use: make exec-app cmd=\"your command\""; exit 1; fi
	$(COMPOSE_COMMAND) $(ENV_FILE_ARG) exec $(APP_SERVICE_NAME) $(cmd)

create-migration:
	@if [ -z "$(message)" ]; then echo "Migration message missing. Use: make create-migration message=\"your message\""; exit 1; fi
	$(COMPOSE_COMMAND) $(ENV_FILE_ARG) run --rm $(APP_SERVICE_NAME) flask db migrate -m "$(message)"

migrate:
	$(COMPOSE_COMMAND) $(ENV_FILE_ARG) run --rm $(APP_SERVICE_NAME) flask db upgrade

init-migrations:
	@echo "INFO: Initializing Flask-Migrate environment..."
	@echo "INFO: This command will create the 'migrations' directory if it doesn't exist and populate it."
	@echo "INFO: Ensure 'migrations' directory has correct permissions if it was manually created: sudo chown -R $(id -u):$(id -g) migrations"
	docker compose -f $(RUN_SH_DIR)/docker-compose.yml --env-file $(RUN_SH_DIR)/../.env run --rm migrations flask db init
	@echo "INFO: Migration environment initialization attempted. Check for a 'migrations' directory with 'alembic.ini' and other files." 
