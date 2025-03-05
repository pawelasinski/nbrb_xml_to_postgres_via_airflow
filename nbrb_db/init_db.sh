#!/usr/bin/env bash

set -e

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" <<-EOSQL
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
