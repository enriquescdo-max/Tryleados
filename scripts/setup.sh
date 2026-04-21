#!/bin/bash
# LeadOS one-time setup
set -e

LEADOS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$LEADOS_DIR"

echo "=== LeadOS Setup ==="

# 1. Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Python dependencies installed"

# 2. Env file
if [ ! -f config/.env ]; then
    cp config/.env.example config/.env
    echo "✓ Created config/.env — EDIT THIS FILE with your API keys before running"
else
    echo "✓ config/.env already exists"
fi

# 3. Database schema
if [ -n "$LEADOS_DB_URL" ]; then
    psql "$LEADOS_DB_URL" -f scripts/db_schema.sql
    echo "✓ Database schema applied"
else
    echo "⚠ LEADOS_DB_URL not set — skipping schema. Run manually:"
    echo "  psql \$LEADOS_DB_URL -f scripts/db_schema.sql"
fi

# 4. Cron jobs
bash scripts/cron_setup.sh
echo "✓ Cron jobs installed"

echo ""
echo "=== Next Steps ==="
echo "1. Edit config/.env with your API keys"
echo "2. Run the schema: psql \$LEADOS_DB_URL -f scripts/db_schema.sql"
echo "3. Import leads: INSERT into leads table or sync from HubSpot"
echo "4. Run your first pipeline: python agents/orchestrator.py"
echo "5. Start webhook server: uvicorn agents.webhook_server:app --port 8080"
