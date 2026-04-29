#!/usr/bin/env bash
set -euo pipefail
alembic downgrade base
alembic upgrade head
python app/seed/demo_seed.py
