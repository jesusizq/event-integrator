# Fever Event Integrator

## Overview

This project implements a microservice that integrates events from external XML API providers into the Fever marketplace, as detailed in [TASK.md](docs/TASK.md). It's a backend API built with Python and Flask, designed for scalability and maintainability.

For a detailed discussion of architectural choices, design decisions, and scalability considerations, please see [Design, Architecture, and Scalability Report](docs/DESIGN_AND_SCALABILITY.md).

## API Usage

The main event search API endpoint is available at: `http://localhost:8080/v1/events/search` (when using Docker/Nginx) or `http://localhost:5000/v1/events/search` (when running Flask directly).
This endpoint retrieves events based on their plan start date. It accepts two optional query parameters:

- `starts_at`: An ISO 8601 formatted datetime string (e.g., `YYYY-MM-DDTHH:MM:SSZ`) specifying the beginning of the date range for event plans.
- `ends_at`: An ISO 8601 formatted datetime string (e.g., `YYYY-MM-DDTHH:MM:SSZ`) specifying the end of the date range for event plans.

Example usage:

```bash
curl -X GET \
  -H "Accept: application/json" \
  "http://localhost:8080/v1/events/search?starts_at=2024-07-01T00:00:00Z&ends_at=2024-07-31T23:59:59Z"
```

A health check endpoint is available at `/v1/health`:

```bash
curl -X GET http://localhost:8080/v1/health

# Expected response:
{"status": "ok"}
```

## Architectural Summary

The system is a microservice with a layered architecture:

- **API Layer**: Flask & APIFairy for handling HTTP requests and validation.
- **Service Layer**: Core business logic.
- **Provider Client**: Interacts with external XML APIs.
- **XML Parser**: Parses XML data to Pydantic models.
- **Data Access Layer**: SQLAlchemy ORM for PostgreSQL database interactions.
- **Background Worker**: Celery & Redis for asynchronous data synchronization.
- **Nginx**: Acts as a reverse proxy in the Docker setup, handling incoming traffic. It can also be configured for SSL termination, basic load balancing (if scaled), and serving static files if needed.

This modular design supports independent development, testing, and scaling. For more details, refer to the [Design, Architecture, and Scalability Report](docs/DESIGN_AND_SCALABILITY.md).

## Makefile

A `Makefile` is provided in the project root to simplify common development and operational tasks. It serves as a convenient entry point for commands related to dependency management, running the application, executing tests, and managing Docker containers.

Key `make` targets include:

- `make install`: Installs project dependencies using Poetry.
- `make run`: Runs the Flask development server.
- `make test`: Executes the test suite using `pytest`.
- `make lint`: Runs linters to check code style.
- `make build`: Builds the Docker image for the application.
- `make up`: Starts all services (application, database, Redis) using Docker Compose (delegates to `docker/run.sh up`).
- `make down`: Stops all services managed by Docker Compose (delegates to `docker/run.sh down`).

Please refer to the `Makefile` itself for the full list of targets and their specific implementations.

## Environment variables

The application requires the following environment variables, typically managed via a `.env` file in the project root. Take a look at the [.env.example](.env.example) file for reference.

**Important Notes**

- **Localhost Configuration**: When working against localhost, ensure to update the service names in the `.env` file to `localhost`. For example, change `postgresql://user:password@db:5432/event_integrator` to `postgresql://user:password@localhost:5432/event_integrator`.
- **Version Control**: **Do not commit** the `.env` file to version control.

## Database Migrations

This project uses Flask-Migrate (which relies on Alembic) to manage database schema changes. For details on why migrations are used, see the [Design, Architecture, and Scalability Report](docs/DESIGN_AND_SCALABILITY.md).

### Initial Setup (One-Time Only)

Before you can create or apply migrations for the first time, you need to initialize the migration environment. This creates a `migrations` directory in your project root that will store all migration scripts and configurations.

1.  **Ensure the `migrations` directory exists with correct permissions:**
    This step is crucial to avoid permission errors when Docker tries to write to this directory from within the container. From your project root:

    ```bash
    mkdir -p migrations
    sudo chown -R $(id -u):$(id -g) migrations
    ```

2.  **Initialize the Flask-Migrate environment:**
    From the project root again, run this command to initialize the migration environment with:

    ```bash
    make init-migrations
    ```

    This command will populate the `./migrations` directory on your host with essential migration files.

    You should commit the initially generated `migrations` directory and all its contents. For this project, **commit all generated migration scripts in `migrations/versions/`**.

Once these steps are completed and committed, you can use the Makefile targets like `make create-migration` and `make migrate` to manage your database schema changes.

### Creating New Migrations

Whenever you make changes to your SQLAlchemy models (defined in `app/models/*.py`), you must generate a new migration script to reflect these changes.

**Generate the migration script:**

Use the provided Makefile command:

```bash
    make create-migration message="<message>"
```

Replace `<message>` with a short, clear summary of the schema changes you made, and you will see the migration script generated in `migrations/versions/`.

### Applying Migrations

Applying migrations to execute the generated scripts to update your database schema to the desired state.

1.  **Automatically on `docker compose up` (via `make up`):**
    The `migrations` service defined in `docker/docker-compose.yml` is configured to automatically run `flask db upgrade` every time your services are started.

2.  **Manually using Makefile:**
    If you need to apply migrations manually (e.g., after pulling new changes from Git that include new migration scripts, without restarting all services), you can use:

    ```bash
    make migrate
    ```

3.  **Manually for Local Development (without Docker, using Poetry environment):**
    If you are developing locally without relying on Docker and have your database and environment variables configured directly on your host machine: - First, ensure your Poetry virtual environment is active:
    ```bash
    poetry shell
    ```
    - Then apply migrations:
    ```bash
    flask db upgrade
    ```

## Dependencies

Install dependencies (`poetry` >=1.5.0 needs to be [installed](https://python-poetry.org/docs/#installing-with-the-official-installer) on the system)

Depending on your IDE, you may need to configure the python interpreter to use the poetry environment (i.e. [PyCharm](https://www.jetbrains.com/help/pycharm/poetry.html))

Use the Makefile to install dependencies:

```sh
make install
```

Activate `poetry environment` (if not using `make run` or other `make` targets that handle it):

```sh
poetry shell
```

## Running the app

Ensure environment variables are set or available in a `.env` file.

Using Makefile with Docker Compose is recommended. This method uses the [docker/docker-compose.yml](docker/docker-compose.yml) file which runs the Flask app along with an Nginx proxy, PostgreSQL database, and Redis.

Ensure your `.env` file is in the project root, as `docker-compose.yml` depends on it.

Build and start the containers in detached mode with:

```sh
source .env && make build && make up
```

The app will be available via Nginx at `http://localhost:8080`

- Event search endpoint: `http://localhost:8080/v1/events/search`
- Health check: [http://localhost:8080/v1/health/](http://localhost:8080/v1/health/)

- View logs: `cd docker && docker compose logs -f` (or `make logs`)
- Stop containers: `make down`

## Running Tests

Ensure development dependencies are installed (this is handled by `make install` if you haven't run it yet, or it's included if you've run `make up`).

Configure a `TEST_DATABASE_URL` in your environment or `.env` file, so tests automatically run against that database.

To run tests:

```sh
source .env.test && make test
```

**IMPORTANT**: ensure you have sourced your test environment variables first with `source .env.test`. That command relies on `docker/run.sh`, which depends on `--env-file=.env.test` for the test environment to work. That file is hardcoded in the run.sh script.
