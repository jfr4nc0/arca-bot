#!/bin/bash

# Exit on any error
set -e

echo "Starting (Debug) ArcaAutoVep API..."

set -euo pipefail

# Start the API server
echo "Starting API server..."
exec poetry run python -Xfrozen_modules=off -m debugpy \
         --listen 0.0.0.0:5678 \
         --wait-for-client \
         -m uvicorn api.main:app \
         --host 0.0.0.0 \
         --port 8000 \
         --reload
