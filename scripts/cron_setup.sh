#!/bin/bash
# Install LeadOS cron jobs
# Run once: bash scripts/cron_setup.sh

LEADOS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$LEADOS_DIR/.venv/bin/python"
LOG="$LEADOS_DIR/logs"

mkdir -p "$LOG"

(crontab -l 2>/dev/null; cat <<CRON
# LeadOS — Lead Scorer (daily 6 AM)
0 6 * * * $PYTHON $LEADOS_DIR/scripts/lead_scorer.py >> $LOG/scorer.log 2>&1

# LeadOS — Full Pipeline (daily 7 AM)
0 7 * * 1-5 $PYTHON $LEADOS_DIR/agents/orchestrator.py >> $LOG/pipeline.log 2>&1

# LeadOS — Deliverer check every 30 min during business hours
*/30 8-17 * * 1-5 $PYTHON $LEADOS_DIR/agents/deliverer.py >> $LOG/deliverer.log 2>&1

# LeadOS — Reply optimizer every hour
0 * * * 1-5 $PYTHON $LEADOS_DIR/agents/optimizer.py >> $LOG/optimizer.log 2>&1

# LeadOS — Friday KPI report (9 AM Friday)
0 9 * * 5 $PYTHON $LEADOS_DIR/agents/orchestrator.py --report >> $LOG/report.log 2>&1
CRON
) | crontab -

echo "LeadOS cron jobs installed:"
crontab -l | grep LeadOS
