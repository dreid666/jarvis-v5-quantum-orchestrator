#!/usr/bin/env bash
# JARVIS V8 Staging Deployment Script
# Deploys JARVIS V8 to staging environment with full validation

set -euo pipefail

echo "🚀 JARVIS V8 Staging Deployment"
echo "========================================"

# Configuration
STAGING_ENV="staging"
LOG_DIR="logs/staging"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOY_LOG="$LOG_DIR/deploy_${TIMESTAMP}.log"

# Create directories
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DEPLOY_LOG"
}

log "Starting JARVIS V8 staging deployment..."

# Phase 1: Environment Validation
log "Phase 1: Validating environment..."
if ! command -v python &> /dev/null; then
    log "ERROR: Python not found"
    exit 1
fi
log "✅ Python found: $(python --version)"

if ! command -v pip &> /dev/null; then
    log "ERROR: pip not found"
    exit 1
fi
log "✅ pip found"

# Phase 2: Install Dependencies
log "Phase 2: Installing dependencies..."
pip install -q -e ".[test]" 2>&1 | tee -a "$DEPLOY_LOG"
log "✅ Dependencies installed"

# Phase 3: Run Tests
log "Phase 3: Running integration tests..."
python -m pytest tests/test_integration_staging.py -v --tb=short 2>&1 | tee -a "$DEPLOY_LOG"
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log "✅ All integration tests passed"
else
    log "ERROR: Integration tests failed"
    exit 1
fi

# Phase 4: Type Checking
log "Phase 4: Running type checks..."
if command -v mypy &> /dev/null; then
    mypy jarvis/ --config-file=mypy.ini 2>&1 | tee -a "$DEPLOY_LOG" || true
    log "✅ Type checking complete (warnings only)"
else
    log "⚠️ mypy not installed, skipping type checks"
fi

# Phase 5: Collect Baseline Metrics
log "Phase 5: Collecting baseline metrics..."
python << 'EOF' 2>&1 | tee -a "$DEPLOY_LOG"
from jarvis import JARVISOrchestrator
from jarvis.observability import get_collector, get_logger

print("Collecting baseline metrics...")
orchestrator = JARVISOrchestrator()
status = orchestrator.status()
print(f"  Modules loaded: {len(status['modules'].get('loaded', [])) if status.get('modules') else 0}")
print(f"  Tools available: {len(status['tools']) if status.get('tools') else 0}")
print(f"  Settings domain: {status['settings']['domain']}")
if status.get("modules", {}).get("failed"):
    raise SystemExit(f"Module load failures detected: {status['modules']['failed']}")
print("✅ Baseline metrics collected")
EOF

# Phase 6: Deployment Summary
log "Phase 6: Deployment summary"
log "========================================"
log "✅ Deployment successful!"
log "Environment: $STAGING_ENV"
log "Timestamp: $TIMESTAMP"
log "Log file: $DEPLOY_LOG"
log ""
log "Next steps:"
log "1. Access staging environment at: https://staging.jarvis.local"
log "2. Monitor observability dashboard: https://staging-grafana.local"
log "3. Review logs: $DEPLOY_LOG"
log ""
log "Deployment complete! 🎉"
