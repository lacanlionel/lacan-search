#!/bin/bash

cd "$(dirname "$0")"

echo ""
echo "  ╔══════════════════════════════╗"
echo "  ║   Lacan Search - Push Git    ║"
echo "  ╚══════════════════════════════╝"
echo ""

# Vérifie s'il y a des changements à pousser
if [[ -z $(git status --porcelain) ]]; then
    echo "  Aucun changement détecté. Rien à pousser."
    echo ""
    read -p "Appuyez sur Entrée pour fermer..."
    exit 0
fi

echo "  Fichiers modifiés :"
git status --short
echo ""

read -p "  Message de commit (Entrée = message par défaut avec la date) : " msg

if [[ -z "$msg" ]]; then
    msg="Mise à jour du $(date '+%d/%m/%Y %H:%M')"
fi

git add .
git commit -m "$msg"
git push

echo ""
echo "  → Terminé. Render va redéployer automatiquement."
echo ""
read -p "Appuyez sur Entrée pour fermer..."
