#!/usr/bin/env bash
# Setup script for armada on CentOS Stream 9
# Usage:
#   sudo bash setup_server.sh all     # run all steps
#   sudo bash setup_server.sh 1       # install PostgreSQL 17
#   sudo bash setup_server.sh 2       # install uv
#   sudo bash setup_server.sh 3       # clone/pull repo
#   sudo bash setup_server.sh 4       # install deps + migrate
#   sudo bash setup_server.sh 5       # create .env
#   sudo bash setup_server.sh 6       # create systemd service
set -euo pipefail

APP_DIR="/opt/armada"
APP_USER="mike"
DB_NAME="armada"
DB_USER="armada"
DB_PASS="armada"
DB_PORT="5432"

usage() {
    echo "Usage: sudo bash $0 {all|1|2|3|4|5|6}"
    echo ""
    echo "Steps:"
    echo "  1  Install PostgreSQL 17"
    echo "  2  Install uv"
    echo "  3  Clone/pull repo"
    echo "  4  Install deps + run migrations"
    echo "  5  Create .env file"
    echo "  6  Create systemd service"
    echo "  all  Run all steps"
    exit 1
}

step_1() {
    echo "[1/6] Installing PostgreSQL 17..."
    if ! command -v /usr/pgsql-17/bin/postgres &>/dev/null; then
        dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm || true
        dnf -qy module disable postgresql || true
        dnf install -y postgresql17-server postgresql17
        /usr/pgsql-17/bin/postgresql-17-setup initdb
        systemctl enable postgresql-17
        systemctl start postgresql-17
    else
        echo "PostgreSQL 17 already installed."
        systemctl start postgresql-17 || true
    fi

    PG_HBA="/var/lib/pgsql/17/data/pg_hba.conf"
    if ! grep -q "armada" "$PG_HBA" 2>/dev/null; then
        sed -i '/^# TYPE/a host    armada          armada          127.0.0.1/32            scram-sha-256' "$PG_HBA"
        sed -i '/^# TYPE/a local   armada          armada                                  scram-sha-256' "$PG_HBA"
        systemctl restart postgresql-17
    fi

    echo "Creating database and user..."
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'\" | grep -q 1 || psql -c \"CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';\""
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\" | grep -q 1 || psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};\""
    echo "Done."
}

step_2() {
    echo "[2/6] Installing uv..."
    if ! command -v uv &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
    else
        echo "uv already installed."
    fi
    echo "Done."
}

step_3() {
    echo "[3/6] Setting up application..."
    if [ ! -d "${APP_DIR}/.git" ]; then
        mkdir -p "${APP_DIR}"
        cd "${APP_DIR}"
        git init
        git remote add origin git@github.com:miketery/armada.git
        git fetch origin
        git checkout -f main
    else
        echo "Repo already cloned, pulling latest..."
        cd "${APP_DIR}" && git pull
    fi
    chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
    echo "Done."
}

step_4() {
    echo "[4/6] Installing dependencies and running migrations..."
    cd "${APP_DIR}"
    su - "${APP_USER}" -c "cd ${APP_DIR} && uv sync"
    su - "${APP_USER}" -c "cd ${APP_DIR} && ARMADA_DATABASE_URL='postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:${DB_PORT}/${DB_NAME}' uv run alembic upgrade head"
    echo "Done."
}

step_5() {
    echo "[5/6] Creating .env file..."
    cat > "${APP_DIR}/.env" <<EOF
ARMADA_DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:${DB_PORT}/${DB_NAME}
ARMADA_USERNAME=michael@tmisha.com
PASSWORD=password123
EOF
    chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
    echo "Done."
}

step_6() {
    echo "[6/6] Creating systemd service..."
    cat > /etc/systemd/system/armada.service <<EOF
[Unit]
Description=Armada API Service
After=network.target postgresql-17.service
Requires=postgresql-17.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=/usr/local/bin/uv run uvicorn armada.main:app --host 127.0.0.1 --port 9001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable armada
    systemctl start armada
    echo "Done."
}

run_all() {
    step_1
    step_2
    step_3
    step_4
    step_5
    step_6
    echo ""
    echo "=== Setup Complete ==="
    echo "PostgreSQL 17 : localhost:${DB_PORT}"
    echo "Armada API    : http://127.0.0.1:8000"
    echo "Service       : systemctl status armada"
    echo "Logs          : journalctl -u armada -f"
}

case "${1:-}" in
    1) step_1 ;;
    2) step_2 ;;
    3) step_3 ;;
    4) step_4 ;;
    5) step_5 ;;
    6) step_6 ;;
    all) run_all ;;
    *) usage ;;
esac
