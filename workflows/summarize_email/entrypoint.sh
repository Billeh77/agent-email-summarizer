#!/bin/sh

echo "Activating virtual environment..."
. /workspace/.venv/bin/activate

echo "Running command: $@"
python "$@"

echo "Command finished."