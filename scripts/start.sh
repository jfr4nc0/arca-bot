#!/bin/bash

# Exit on any error
set -e

echo "Starting ArcaAutoVep API with cron support..."

# Create log directory for cron
mkdir -p /var/log/cron

# Install/update all crontab files to /etc/cron.d/
echo "Setting up crontabs..."

# Install each crontab file to cron.d (will overwrite existing)
for crontab_file in /app/cron/*-crontab; do
    if [ -f "$crontab_file" ]; then
        filename=$(basename "$crontab_file")
        echo "Installing/updating $filename to /etc/cron.d/..."
        cp "$crontab_file" "/etc/cron.d/$filename"
        chmod 0644 "/etc/cron.d/$filename"
    fi
done

echo "All crontabs installed/updated successfully"

# Start cron daemon in background if not already running
echo "Starting cron daemon..."
if ! ps aux | grep -q '[c]ron'; then
    echo "Cron daemon not running, starting it..."
    service cron start
else
    echo "Cron daemon already running"
fi

# Start the API server
echo "Starting API server..."
exec poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000
