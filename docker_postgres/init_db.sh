#!/usr/bin/env bash

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
CREATE TABLE IF NOT EXISTS nbrb_rates_daily_basis
  (
    id text NOT NULL,
    date text NOT NULL,
    numcode text NOT NULL,
    charcode text NOT NULL,
    scale text NOT NULL,
    name text NOT NULL,
    rate text NOT NULL
  );
EOSQL
