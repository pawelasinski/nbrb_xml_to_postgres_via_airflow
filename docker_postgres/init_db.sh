#!/usr/bin/env bash

set -e  # Exit immediately if a command exits with a non-zero status.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
CREATE TABLE IF NOT EXISTS nbrb_rates_daily_basis
  (
    id TEXT NOT NULL,
    date TEXT NOT NULL,
    numcode TEXT NOT NULL,
    charcode TEXT NOT NULL,
    scale TEXT NOT NULL,
    name TEXT NOT NULL,
    rate TEXT NOT NULL
  );
EOSQL
# -v ON_ERROR_STOP=1 — it is a flag that tells psql to stop execution if an error occurs.
