#!/usr/bin/env bash
# -------------------------------------------------------------------
#  setup_env.sh — Populate .env.{env} for Email Summarizer app from Azure KV
#
#  Environments: dev, staging, prod (inferred from vault name)
#  Auth0 secrets always come from staging vault
#
#  Prerequisites:
#    • Azure CLI installed and logged in (az login)
#    • Access to the Key Vault (kv-arata-ai-{env})
#
#  Usage:
#    ./setup_env.sh                          # dev vault, .env.development
#    ./setup_env.sh --vault kv-arata-ai-staging
#    ./setup_env.sh --remote                 # use staging cloud service URLs
#    ./setup_env.sh --vectordb               # include VECTORDB_URL
#    ./setup_env.sh --file-service           # include FILE_SERVICE_URL
# -------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Defaults ──────────────────────────────────────────────────────
VAULT_NAME="kv-arata-ai-dev"
USE_REMOTE=false
INCLUDE_VECTORDB=false
INCLUDE_FILE_SERVICE=false

# ── Parse arguments ───────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --vault)        VAULT_NAME="$2"; shift 2 ;;
        --remote)       USE_REMOTE=true; shift ;;
        --vectordb)     INCLUDE_VECTORDB=true; shift ;;
        --file-service) INCLUDE_FILE_SERVICE=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--vault VAULT_NAME] [--remote] [--vectordb] [--file-service]"
            echo ""
            echo "Options:"
            echo "  --vault NAME     Azure Key Vault name (default: kv-arata-ai-dev)"
            echo "  --remote         Use staging cloud service URLs instead of localhost"
            echo "  --vectordb       Include VECTORDB_URL in .env"
            echo "  --file-service   Include FILE_SERVICE_URL in .env"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Extract environment from vault name (kv-arata-ai-{env})
if [[ $VAULT_NAME =~ kv-arata-ai-([a-z]+)$ ]]; then
    ENV="${BASH_REMATCH[1]}"
else
    echo "❌ Invalid vault name. Expected format: kv-arata-ai-{env}"
    exit 1
fi

# Auth0 secrets always come from the staging vault
STAGING_VAULT_NAME="kv-arata-ai-staging"

# ── Helpers ───────────────────────────────────────────────────────
fetch_secret() {
    local secret_name="$1"
    local vault="${2:-$VAULT_NAME}"
    local value
    value=$(az keyvault secret show \
        --name "$secret_name" \
        --vault-name "$vault" \
        --query "value" -o tsv 2>/dev/null) || true

    if [[ -z "$value" ]]; then
        echo "⚠️  Could not fetch secret: $secret_name" >&2
        return 1
    fi
    echo "$value"
}

echo "============================================================"
echo "🔑 Email Summarizer App — Environment Setup"
echo "============================================================"
echo "📦 Key Vault : $VAULT_NAME"
echo ""

# ── Verify Azure CLI login ────────────────────────────────────────
if ! az account show &>/dev/null; then
    echo "❌ Not logged in to Azure CLI. Run 'az login' first."
    exit 1
fi
echo "✅ Azure CLI authenticated"
echo ""

# ── Fetch secrets ─────────────────────────────────────────────────
echo "🔑 Fetching secrets from $VAULT_NAME ..."

SECRET_AZURE_TENANT_ID=""
SECRET_AZURE_CLIENT_ID=""
SECRET_AZURE_CLIENT_SECRET=""
SECRET_AUTH0_DOMAIN=""
SECRET_AUTH0_CLIENT_ID=""
SECRET_AUTH0_CLIENT_SECRET=""
SECRET_AUTH0_SESSION_SECRET=""
SECRET_SERVER_URL=""

fetch_and_set() {
    local var_name="SECRET_$1"
    local secret_name="$2"
    local vault="${3:-}"
    local value
    if value=$(fetch_secret "$secret_name" "$vault"); then
        echo "  ✓ $1"
        eval "$var_name=\$value"
    else
        echo "  ✗ $1 (secret: $secret_name)"
    fi
}

# Shared secrets
fetch_and_set "AZURE_TENANT_ID" "entra-tenant-id"

# Auth0 secrets always come from staging vault
echo "  (Auth0 secrets fetched from $STAGING_VAULT_NAME)"
fetch_and_set "AUTH0_DOMAIN"         "auth0-domain"        "$STAGING_VAULT_NAME"
fetch_and_set "AUTH0_CLIENT_ID"      "auth0-client-id"     "$STAGING_VAULT_NAME"
fetch_and_set "AUTH0_SESSION_SECRET" "ui-cookie-secret"    "$STAGING_VAULT_NAME"

IS_DEV_VAULT=false
if [[ "$VAULT_NAME" == *"-dev"* ]]; then
    IS_DEV_VAULT=true
fi

if $IS_DEV_VAULT; then
    echo "  ⏭  Skipping AUTH0_CLIENT_SECRET (not in dev vault — fetching from staging)"
    fetch_and_set "AUTH0_CLIENT_SECRET" "auth0-client-secret" "$STAGING_VAULT_NAME"
else
    fetch_and_set "AUTH0_CLIENT_SECRET" "auth0-client-secret"
    fetch_and_set "AZURE_CLIENT_ID"     "applications-email-summarizer-app-id"
    fetch_and_set "AZURE_CLIENT_SECRET" "applications-email-summarizer-app-secret"
fi

# Server URL (only non-dev envs have this in the vault)
if [[ "$ENV" != "dev" ]]; then
    fetch_and_set "SERVER_URL" "applications-email-summarizer-server-url"
fi

echo ""

# ── Derived values ────────────────────────────────────────────────
AZURE_KEYVAULT_URI="https://${VAULT_NAME}.vault.azure.net"

AUTH0_SCOPE="openid profile email offline_access"
AUTH0_AUDIENCE="https://${SECRET_AUTH0_DOMAIN}/api/v2/"

if $USE_REMOTE; then
    ARATA_DB_URL="https://app-db-staging.azurewebsites.net"
    VECTORDB_URL="https://app-vectordb-staging.azurewebsites.net"
    FILE_SERVICE_URL="https://app-file-staging.azurewebsites.net"
    echo "🌐 Using remote (staging) service URLs"
else
    ARATA_DB_URL="http://localhost:8000"
    VECTORDB_URL="http://localhost:8003"
    FILE_SERVICE_URL="http://localhost:8002"
    echo "🏠 Using localhost service URLs"
fi

# ── Determine env file path ────────────────────────────────────────
if [[ "$ENV" == "dev" ]]; then
    ENV_FILE="$SCRIPT_DIR/.env.development"
    SERVER_URL="http://localhost:3000"
else
    ENV_FILE="$SCRIPT_DIR/.env.$ENV"
    SERVER_URL="$SECRET_SERVER_URL"
fi

# Create backup if file already exists
if [[ -f "$ENV_FILE" ]]; then
    BACKUP="$ENV_FILE.bak.$(date +%Y%m%dT%H%M%S)"
    cp "$ENV_FILE" "$BACKUP"
    echo "📋 Backed up existing env file to $(basename "$BACKUP")"
fi

# ── Write .env file ────────────────────────────────────────────────
echo "📝 Writing $ENV_FILE ..."

{
    cat <<EOF
# ---------------------------------------------------------------
#  Auto-generated by setup_env.sh — $(date -Iseconds)
#  Env: $ENV | Vault: $VAULT_NAME
# ---------------------------------------------------------------

# Server
SERVER_URL=$SERVER_URL

# Service URLs
ARATA_DB_URL=$ARATA_DB_URL
EOF

    if $INCLUDE_VECTORDB; then
        echo "VECTORDB_URL=$VECTORDB_URL"
    fi

    if $INCLUDE_FILE_SERVICE; then
        echo "FILE_SERVICE_URL=$FILE_SERVICE_URL"
    fi

    cat <<EOF

# Azure Key Vault
AZURE_KEYVAULT_URI=$AZURE_KEYVAULT_URI
AZURE_TENANT_ID=$SECRET_AZURE_TENANT_ID
AZURE_CALLER_SERVICE=applications-email-summarizer
AZURE_DB_SERVICE=db-service
EOF

    if $INCLUDE_VECTORDB; then
        echo "AZURE_VECTORDB_SERVICE=vectordb-service"
    fi

    if $INCLUDE_FILE_SERVICE; then
        echo "AZURE_FILE_SERVICE=file-service"
    fi

    cat <<EOF

# Azure Service Principal
AZURE_CLIENT_ID=$SECRET_AZURE_CLIENT_ID
AZURE_CLIENT_SECRET=$SECRET_AZURE_CLIENT_SECRET

# Auth0
AUTH0_DOMAIN=$SECRET_AUTH0_DOMAIN
AUTH0_CLIENT_ID=$SECRET_AUTH0_CLIENT_ID
AUTH0_CLIENT_SECRET=$SECRET_AUTH0_CLIENT_SECRET
AUTH0_SESSION_SECRET=$SECRET_AUTH0_SESSION_SECRET
AUTH0_SCOPE=$AUTH0_SCOPE
AUTH0_AUDIENCE=$AUTH0_AUDIENCE

# App URLs
HOME_APP_URL=http://localhost:5173
EOF
} > "$ENV_FILE"

echo "  ✅ $(basename "$ENV_FILE")"
echo ""
echo "============================================================"
echo "✅ Done! Environment file written: $(basename "$ENV_FILE")"
echo "============================================================"
echo ""
echo "You can now run:  pnpm dev"
