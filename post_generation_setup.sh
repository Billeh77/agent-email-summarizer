#!/bin/bash
set -euo pipefail

# Post-generation setup — registers this agent so it resolves locally, i.e.
# creates the row in the db-service `agents` table that get_agent_by_name, the
# dashboard, and the poller all read. (Replaces the old chmod-only stub that
# printed "complete" without registering anything.)
#
# Self-configuring: the agent name / workflow / queue are DERIVED from this repo,
# so this script is identical for every agent and can't drift from the code.
# Override any of them via env vars if derivation can't pick the right one
# (e.g. a multi-workflow agent):
#   AGENT_NAME=... WORKFLOW=... QUEUE=... TENANT_ID=... ./post_generation_setup.sh
#
# Idempotent, and fails LOUDLY: each step works or stops with a clear fix.

ENVIRONMENT="${ARATA_ENV:-dev}"
TENANT_ID="${TENANT_ID:-e9501a25}"   # local dev tenant; override with TENANT_ID=...

# --- Derive agent identity from the repo (override via env) ------------------
# AGENT_NAME: the constant the workflow uses as its registered name.
# WORKFLOW:   the Temporal workflow class (== the registered workflow id).
# QUEUE:      the worker's task queue.
AGENT_NAME="${AGENT_NAME:-$(grep -rhoE 'AGENT_NAME *= *"[^"]+"' workflows/*/src 2>/dev/null | head -1 | sed -E 's/.*"([^"]+)".*/\1/')}"
WORKFLOW="${WORKFLOW:-$(grep -rhoE 'class [A-Za-z0-9_]+Workflow' workflows/*/src 2>/dev/null | head -1 | sed -E 's/^class //')}"
QUEUE="${QUEUE:-$(grep -rhoE 'TASK_QUEUE *= *"[^"]+"' workflows/*/src 2>/dev/null | head -1 | sed -E 's/.*"([^"]+)".*/\1/')}"

# Fail loudly if any couldn't be derived (e.g. multi-workflow repo) — set via env.
for v in AGENT_NAME WORKFLOW QUEUE; do
  if [ -z "${!v}" ]; then
    echo "❌ Could not derive ${v} from the repo. Set it explicitly, e.g.:"
    echo "   ${v}=<value> ./post_generation_setup.sh"
    exit 1
  fi
done

# Original behaviour: make helper scripts executable (setup_pulumi.sh self-deletes
# after a successful run, hence the || true).
chmod +x run_locally.sh setup_env.sh setup_pulumi.sh 2>/dev/null || true

echo "▶ Post-generation setup: ${AGENT_NAME} (env=${ENVIRONMENT}, tenant=${TENANT_ID})"
echo "    workflow=${WORKFLOW}  queue=${QUEUE}"

# --- Preconditions (fail loudly; never fake success) ------------------------
command -v aratactl >/dev/null 2>&1 || { echo "❌ aratactl not found — install the Arata CLI."; exit 1; }
az account show >/dev/null 2>&1 || { echo "❌ Not logged into Azure — run: az login"; exit 1; }

# The agent's Azure identity must exist in Key Vault before `tenant add-agent`
# (it reads agent-<name>-app-id / -app-secret). That identity is created by pulumi.
if ! az keyvault secret show \
        --name "agent-${AGENT_NAME}-app-id" \
        --vault-name "kv-arata-ai-${ENVIRONMENT}" >/dev/null 2>&1; then
  echo "❌ Key Vault secret 'agent-${AGENT_NAME}-app-id' not found."
  echo "   Deploy the Azure identity first:  ./setup_pulumi.sh   (or: cd pulumi && pulumi up)"
  exit 1
fi

# --- 1. Ensure the tenant exists in the registry ----------------------------
echo "▶ Ensuring tenant ${TENANT_ID} exists in the registry ..."
aratactl registry -e "${ENVIRONMENT}" tenant create --id "${TENANT_ID}" --name "Dev Tenant" || true

# --- 2. Register / update the agent catalog definition ----------------------
echo "▶ Registering agent definition ..."
aratactl registry -e "${ENVIRONMENT}" agent create \
  --name "${AGENT_NAME}" --workflow "${WORKFLOW}" --queue "${QUEUE}"

# --- 3. Resolve the auto-generated agent id ---------------------------------
echo "▶ Resolving agent id ..."
AGENT_ID="$(aratactl registry -e "${ENVIRONMENT}" agent list -o json | python3 -c "
import sys, json
text = sys.stdin.read()
i = text.find('[')
data, _ = (json.JSONDecoder().raw_decode(text[i:]) if i >= 0 else ([], 0))
print(next((a['id'] for a in data if a.get('name') == '${AGENT_NAME}'), ''))
")"
[ -n "${AGENT_ID}" ] || { echo "❌ Could not resolve agent id for '${AGENT_NAME}' from the registry."; exit 1; }
echo "  agent id: ${AGENT_ID}"

# --- 4. Provision into the tenant DB (writes the db-service agents row) ------
echo "▶ Provisioning ${AGENT_NAME} into tenant ${TENANT_ID} (writes the db row) ..."
aratactl registry -e "${ENVIRONMENT}" tenant add-agent "${TENANT_ID}" "${AGENT_ID}"

# --- 5. Upload agent artifacts (purpose / config / instructions) ------------
# Flips has_purpose/has_config/has_instructions in the registry; the purpose is
# what enables intent routing. set-* is "upload or replace" (idempotent).
# Each artifact is skipped if it's missing or still the generated template
# default, so this script stays safe to run before the Phase-5 artifacts exist.
echo "▶ Uploading agent artifacts (purpose / config / instructions) ..."

if [ -f agent_skills/AGENT_PURPOSE.md ] \
   && ! grep -qF "This agent can process requests and execute workflows." agent_skills/AGENT_PURPOSE.md; then
  aratactl registry -e "${ENVIRONMENT}" agent set-purpose "${AGENT_ID}" agent_skills/AGENT_PURPOSE.md
else
  echo "  ⏭ purpose: missing or still the template default — skipping"
fi

if [ -f agent_skills/AGENT_INSTRUCTIONS.md ] \
   && ! grep -qF "This guide explains how to use the agent." agent_skills/AGENT_INSTRUCTIONS.md; then
  aratactl registry -e "${ENVIRONMENT}" agent set-instructions "${AGENT_ID}" agent_skills/AGENT_INSTRUCTIONS.md
else
  echo "  ⏭ instructions: missing or still the template default — skipping"
fi

# Config stub = the lone read-only use_emails_v2 property; treat >1 property as real.
if [ -f agent_skills/AGENT_CONFIG.json ] \
   && python3 -c "import json,sys; sys.exit(0 if len(json.load(open('agent_skills/AGENT_CONFIG.json')).get('properties',{})) > 1 else 1)" 2>/dev/null; then
  aratactl registry -e "${ENVIRONMENT}" agent set-config "${AGENT_ID}" agent_skills/AGENT_CONFIG.json
else
  echo "  ⏭ config: missing or still the template default — skipping"
fi

echo
echo "✅ Post-generation setup complete — agent registered."
echo "   Verify the row:  GET http://localhost:8000/v1/agents/name/${AGENT_NAME}?tenant=${TENANT_ID}"
