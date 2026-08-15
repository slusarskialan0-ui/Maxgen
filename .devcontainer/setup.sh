#!/bin/bash
# Setup script for GitHub Codespaces
set -e
echo "=== Instalacja zależności ==="
cd /workspaces/Polska-Auto-Leads-Engine-max/backend
pip install -r requirements.txt -q

cd /workspaces/Polska-Auto-Leads-Engine-max/frontend
npm install --silent

echo "=== Konfiguracja frontend ==="
if [ ! -f .env ]; then
  echo "VITE_API_URL=http://localhost:8000" > .env
fi

echo "=== Setup zakończony! ==="
echo "Uruchom: bash start_all.sh"
