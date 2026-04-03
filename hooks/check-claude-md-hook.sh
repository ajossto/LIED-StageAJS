#!/usr/bin/env bash
# check-claude-md-hook.sh — PostToolUse hook Claude Code.
#
# Déclenché après Edit ou Write. Si le fichier modifié est un fichier
# structurel du projet, rappelle à Claude de vérifier CLAUDE.md.
#
# Reçoit le tool input en JSON sur stdin.

KEY_FILES="config.py models.py simulation.py main.py statistics.py output.py analysis.py"

file_path=$(python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null || true)

[ -z "$file_path" ] && exit 0

basename=$(basename "$file_path")

for kf in $KEY_FILES; do
    if [ "$basename" = "$kf" ]; then
        echo "Note: '$basename' vient d'être modifié."
        echo "Vérifier si CLAUDE.md doit être mis à jour (commandes, paramètres, architecture, Repo Map)."
        exit 0
    fi
done

exit 0
