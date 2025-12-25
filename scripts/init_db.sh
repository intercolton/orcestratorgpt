#!/usr/bin/env bash
set -euo pipefail
psql "$DATABASE_URL" -f migrations/001_init.sql
