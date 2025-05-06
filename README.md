# Fever Event Integrator

## Overview

This project implements a solution for the task defined in the [TASK.md](docs/TASK.md) file.

It's a simple backend API built with Flask and Python.

The main API runs at: `http://localhost:8080/v1/<endpoint>` (when using Docker/Nginx) or `http://localhost:5000/v1/<endpoint>` (when running Flask directly).

A health check endpoint is available at `/v1/health`.

## Architectural Overview

TODO: add architectural overview

## Environment variables

The application requires the following environment variables, typically managed via a `.env` file in the project root:

```sh
# Flask Configuration
FLASK_APP=run.py
FLASK_CONFIG=development # Config to use (development, testing, production)
SECRET_KEY=your_strong_secret_key
FLASK_DEBUG=1 # Set to 1 for development

# Database Configuration
DATABASE_URL=postgresql://user:password@db:5432/event_integrator
DB_NAME=event_integrator
DB_USER=user
DB_PASSWORD=password
TEST_DATABASE_URL=postgresql://test_user:test_password@host:port/test_event_integrator
TEST_DB_NAME=test_event_integrator
TEST_DB_USER=test_user
TEST_DB_PASSWORD=test_password

# External Provider API
PROVIDER_API_URL=https://provider.code-challenge.feverup.com/api/events
PROVIDER_API_TIMEOUT=10 # seconds
```

- Set `FLASK_CONFIG` to `production` for production deployments.
- Ensure `SECRET_KEY` is set to a strong, unique value in production.
- Create a `.env` file (copied from `.env.example`) in the project root to manage these variables locally. **Do not commit `.env` to version control.**

## Dependencies

Install dependencies (`poetry` >=1.5.0 needs to be [installed](https://python-poetry.org/docs/#installing-with-the-official-installer) on the system)

Depending on your IDE, you may need to configure the python interpreter to use the poetry environment (i.e. [PyCharm](https://www.jetbrains.com/help/pycharm/poetry.html))

If the previous step has not done it automatically, now you have to install dependencies:

```sh
poetry install
```

Activate `poetry environment`:

```sh
poetry shell
```

## Running the app

### 1. Using Poetry

Ensure environment variables are set or available in a `.env` file.

```sh
# Run the development server
poetry run flask run

# The app will be available at http://localhost:5000
```

### 2. Using Docker Compose (Recommended)

This method uses the [docker/docker-compose.yml](docker/docker-compose.yml) file which runs the Flask app along with an Nginx proxy.

Ensure your `.env` file is in the project root, as `docker-compose.yml` is depends on it.

Build and start the containers in detached mode via the helper script:

```sh
sh docker/run.sh -d up
```

The app will be available via Nginx at `http://localhost:8080`

- View logs: `cd docker && docker compose logs -f`
- Stop containers: `sh docker/run.sh down`

## Running Tests

Ensure development dependencies are installed (`poetry install --with dev`).

Configure a `TEST_DATABASE_URL` in your environment or `.env` file, so tests automatically run against that database.

```sh
poetry run pytest
```

Alternatively, run tests inside the Docker container (after `make up` or `./docker/run.sh up`):

```sh
make test
# or
docker compose exec app poetry run pytest
```
