#!/usr/bin/env bash
set -euo pipefail

cd /home/site/wwwroot

# Azure App Service's Python/Oryx image normally activates the environment
# before invoking the configured startup command.
if [ -f antenv/bin/activate ]; then
  source antenv/bin/activate
elif [ -f /opt/venv/bin/activate ]; then
  source /opt/venv/bin/activate
fi

echo "Applying SplitSmart database migrations..."
python manage.py migrate --noinput

echo "Starting SplitSmart..."
exec gunicorn --bind "0.0.0.0:${PORT:-8000}" --timeout 120 splitsmart.wsgi:application
