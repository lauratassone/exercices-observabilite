#!/usr/bin/env bash
# traffic.sh - generate synthetic traffic against demo-api
# Usage: ./traffic.sh                   # defaults to http://localhost:8000
#        ./traffic.sh http://host:port  # override base URL
set -eu
BASE="${1:-http://localhost:8000}"
echo "Generating traffic against $BASE - Ctrl+C to stop"
while true; do
  curl -s -o /dev/null "$BASE/api/users"
  curl -s -o /dev/null "$BASE/api/orders"
  sleep 0.5
done
