#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/scripts/logs"
LOG_FILE="${LOG_DIR}/update_and_check.log"
VENV_DIR="${REPO_ROOT}/.venv"

mkdir -p "${LOG_DIR}"
: > "${LOG_FILE}"

log() {
    local timestamp
    timestamp="$(date +"%Y-%m-%d %H:%M:%S")"
    echo "[${timestamp}] $*" | tee -a "${LOG_FILE}"
}

run_step() {
    local description="$1"
    shift
    log "==> ${description}"
    if "$@" 2>&1 | tee -a "${LOG_FILE}"; then
        log "<== Succès: ${description}"
        return 0
    else
        local status=$?
        log "<== Échec (${status}): ${description}"
        return "${status}"
    fi
}

log "Démarrage du script update_and_check.sh"
cd "${REPO_ROOT}"

if [ ! -d "${VENV_DIR}" ]; then
    run_step "Création de l'environnement virtuel .venv" python3 -m venv "${VENV_DIR}" || exit $?
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
log "Environnement virtuel activé (${VENV_DIR})"

if [ -f "pyproject.toml" ]; then
    if ! run_step "Installation des dépendances dev via pip install -e '.[dev]'" pip install -e '.[dev]'; then
        if [ -f "requirements-dev.txt" ]; then
            run_step "Installation des dépendances dev via requirements-dev.txt" pip install -r requirements-dev.txt || exit $?
        else
            log "Aucun fallback requirements-dev.txt trouvé"
            exit 1
        fi
    fi
elif [ -f "requirements-dev.txt" ]; then
    run_step "Installation des dépendances dev via requirements-dev.txt" pip install -r requirements-dev.txt || exit $?
else
    log "Impossible de trouver pyproject.toml ou requirements-dev.txt pour installer les dépendances."
    exit 1
fi

run_step "Installation de types-PyYAML" pip install types-PyYAML || exit $?
run_step "Installation de psycopg[binary]" pip install "psycopg[binary]" || exit $?

run_step "Exécution de pre-commit" python -m pre_commit run --all-files || exit $?
run_step "Exécution de Ruff avec --fix" ruff . --fix || exit $?
run_step "Exécution de Black" black . || exit $?
run_step "Exécution de MyPy" mypy . || exit $?
run_step "Exécution de Pytest (mode quiet)" python -m pytest -q || exit $?

log "Script terminé avec succès"
