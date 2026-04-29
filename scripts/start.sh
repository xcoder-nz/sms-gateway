#!/usr/bin/env bash
set -euo pipefail
PROFILE=${1:-dev}
ENV_FILE=".env.${PROFILE}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Unknown profile ${PROFILE}. Expected one of: dev demo prod" >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" $([[ "${DEBUG:-0}" == "1" ]] && echo "--reload")
