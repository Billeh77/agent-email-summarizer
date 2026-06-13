#!/bin/bash

# Parse command and environment.
# Supported forms:
#   ./run_locally.sh <workflow-command> [dev|staging|prod] [runner-arg]
#   ./run_locally.sh [dev|staging|prod] <workflow-command> [runner-arg]
COMMAND="${1:-}"
ENVIRONMENT="dev"
RUNNER_ARG=""

is_environment() {
    case "$1" in
        dev|staging|prod)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

if [ -z "$COMMAND" ]; then
    echo "No environment specified, defaulting to: dev"
elif is_environment "$COMMAND"; then
    ENVIRONMENT="$COMMAND"
    COMMAND="${2:-}"
    RUNNER_ARG="${3:-}"
elif [ -z "${2:-}" ]; then
    echo "No environment specified, defaulting to: dev"
elif is_environment "$2"; then
    ENVIRONMENT="$2"
    RUNNER_ARG="${3:-}"
elif [[ "$COMMAND" == *-runner ]]; then
    echo "No environment specified, defaulting to: dev"
    RUNNER_ARG="$2"
else
    echo "Error: Invalid environment '$2'. Expected one of: dev, staging, prod"
    exit 1
fi

# Set up environment variables
# Source setup_env.sh to create .env and set environment variables
echo "Setting up environment variables from ${ENVIRONMENT}..."
source ./setup_env.sh "$ENVIRONMENT"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: Could not create or find .env file"
    exit 1
fi

# Unset OPENAI_API_KEY to avoid conflicts
unset OPENAI_API_KEY

# Create Temporal search attributes if they don't exist
temporal operator search-attribute create --name mailboxId --type Keyword
temporal operator search-attribute create --name messageId --type Keyword
temporal operator search-attribute create --name tenantId --type Keyword

source .venv/bin/activate

case "$COMMAND" in
    summarize_email-worker)
        echo -ne "\033]0;Summarize_email\007"
        uv run workflows/summarize_email/src/summarize_email/worker.py
        ;;
    summarize_email-runner)
        uv run workflows/summarize_email/src/summarize_email/summarize_email_runner.py ${RUNNER_ARG:+ "$RUNNER_ARG"}
        ;;
    *)
        echo "Usage: $0 summarize_email-worker|summarize_email-runner [dev|staging|prod]"
        exit 1
        ;;
esac
