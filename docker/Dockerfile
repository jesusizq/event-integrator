# ------------------------------------------------------------------------------
# Builder stage
# ------------------------------------------------------------------------------
FROM python:3.11 AS builder

ENV POETRY_VERSION=1.8.2
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_NO_INTERACTION=1

RUN apt-get update && apt-get install --no-install-recommends -y curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get remove -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

# Configure poetry to create the virtual env in the project's root
RUN poetry config virtualenvs.in-project true

COPY poetry.lock pyproject.toml ./

# Install dependencies
RUN poetry install --no-root --no-dev

# Copy the application code AFTER installing dependencies
# to leverage Docker cache more effectively.
COPY ./app /app/source_code
COPY ./config.py /app/config.py
COPY ./run.py /app/run.py

# ------------------------------------------------------------------------------
# Final application image stage
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS app

ENV POETRY_VERSION=1.8.2
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_NO_INTERACTION=1
ENV PATH="$POETRY_HOME/bin:/home/appuser/.venv/bin:$PATH"

# Install curl for health checks
RUN apt-get update && apt-get install --no-install-recommends -y curl postgresql-client && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser

# Copy only essential files and the virtual environment from the builder
COPY --from=builder /app/pyproject.toml /app/poetry.lock /home/appuser/
COPY --from=builder /app/.venv /home/appuser/.venv
COPY --from=builder $POETRY_HOME $POETRY_HOME

# Copy application code from the builder stage
COPY --from=builder /app/source_code /home/appuser/app
COPY --from=builder /app/config.py /home/appuser/config.py
COPY --from=builder /app/run.py /home/appuser/run.py

# Copy the migrations directory from the host into the image
COPY ./migrations /home/appuser/migrations

# Copy migrations entrypoint script
COPY ./docker/entrypoints/migrations_entrypoint.sh /home/appuser/migrations_entrypoint.sh
RUN chmod +x /home/appuser/migrations_entrypoint.sh

# Ensure the appuser owns the necessary files and directories
RUN chown -R appuser:appuser /home/appuser/pyproject.toml /home/appuser/poetry.lock /home/appuser/.venv $POETRY_HOME /home/appuser/app /home/appuser/config.py /home/appuser/run.py /home/appuser/migrations_entrypoint.sh && \
    chown appuser:appuser /home/appuser

# Fix shebang lines in virtual environment scripts to point to the correct Python path
RUN find /home/appuser/.venv/bin/ -type f -exec sed -i 's|#!/app/.venv/bin/python|#!/home/appuser/.venv/bin/python|g' {} \;

EXPOSE 5000

# Switch to the non-root user
USER appuser

CMD ["/home/appuser/.venv/bin/gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:create_app()"]

# ------------------------------------------------------------------------------
# Nginx stage
# ------------------------------------------------------------------------------
FROM nginx:alpine AS nginx

# Create log directory with proper permissions
RUN mkdir -p /var/log/nginx && \
    touch /var/log/nginx/access.log && \
    touch /var/log/nginx/error_file.log && \
    chown -R nginx:nginx /var/log/nginx && \
    chmod -R 755 /var/log/nginx

# Remove default Nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy custom Nginx configuration
COPY ./nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
#EXPOSE 443

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]

# ------------------------------------------------------------------------------
# Redis configured stage
# ------------------------------------------------------------------------------
FROM redis:7-alpine AS redis-configured

# Copy custom Redis configuration
COPY ./redis/redis.conf /usr/local/etc/redis/redis.conf

EXPOSE 6379

# Start Redis
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
