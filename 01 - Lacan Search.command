#!/bin/bash
PROJECT="$HOME/Documents/01-lionel/01-psychanalyse/lacan-search"

echo ""
echo "  ╔══════════════════════════════╗"
echo "  ║       Lacan Search           ║"
echo "  ╚══════════════════════════════╝"
echo ""

if [ ! -f "$PROJECT/app.py" ]; then
    echo "  ✗ Dossier introuvable : $PROJECT"
    read -p "  Appuyez sur Entrée pour fermer..."
    exit 1
fi

if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "  → Installation des dépendances..."
    pip3 install fastapi uvicorn jinja2 python-multipart --quiet
fi

PID=$(lsof -ti tcp:8000 2>/dev/null)
if [ -n "$PID" ]; then
    kill -9 $PID 2>/dev/null
    sleep 1
fi

cd "$PROJECT"
echo "  → http://localhost:8000"
echo ""
(sleep 1.5 && open "http://localhost:8000") &
python3 -m uvicorn app:app --host 127.0.0.1 --port 8000
