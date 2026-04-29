#!/usr/bin/env bash
set -euo pipefail
PROFILE_RAW=${1:-dev}
PROFILE=$(printf '%s' "${PROFILE_RAW}" | tr -d '[:space:]')

case "${PROFILE}" in
  dev|demo|prod) ;;
  *)
    echo "Unknown profile ${PROFILE_RAW}. Expected one of: dev demo prod" >&2
    exit 1
    ;;
esac

ENV_FILE=".env.${PROFILE}"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
elif [[ "${PROFILE}" != "prod" ]]; then
  echo "Missing ${ENV_FILE}. Expected one of: .env.dev .env.demo .env.prod" >&2
  exit 1
fi

export APP_ENV="${APP_ENV:-${PROFILE}}"

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" $([[ "${DEBUG:-0}" == "1" ]] && echo "--reload")
