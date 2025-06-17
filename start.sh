#!/bin/sh
flask db upgrade
# Get log level from env variable
if [ -z "$LOG_LEVEL" ]; then
    LOG_LEVEL=info
fi
# Start Gunicorn processes
echo Starting Gunicorn with $LOG_LEVEL log level
exec gunicorn -b :8080 --workers 4 --worker-class uvicorn.workers.UvicornWorker "app.fastapi_app:app" --log-level=$LOG_LEVEL
