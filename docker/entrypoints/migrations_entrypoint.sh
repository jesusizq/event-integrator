#!/bin/sh
set -e

echo "Migration script started."

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
PG_USER="${POSTGRES_USER:-user}"
PG_DBNAME="${POSTGRES_DB:-eventsdb}"

echo "Waiting for database at ${DB_HOST}:${DB_PORT} with user ${PG_USER} on db ${PG_DBNAME} to be healthy..."

# Loop until pg_isready returns 0 (success)
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${PG_USER}" -d "${PG_DBNAME}" -q; do
  echo "Postgres is unavailable - sleeping"
  sleep 2
done

echo "Database is healthy."
echo "Running migrations..."

# Run flask db upgrade and capture its output and exit code
output=$(flask db upgrade 2>&1)
exit_code=$?

echo "Flask db upgrade command output:"
echo "${output}"

if [ ${exit_code} -ne 0 ]; then
  echo "Error: flask db upgrade failed with exit code ${exit_code}."
  exit ${exit_code}
fi

echo "Migrations complete. Migration script finished." 