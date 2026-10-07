#!/bin/bash
# Script temporaire — lancer Claude Code dans tmux avec remote-control
# Usage : bash ~/jupyter/launch_remote.sh

set -e

# Installer tmux si absent
if ! command -v tmux &>/dev/null; then
    echo "Installation de tmux..."
    sudo apt-get update -qq && sudo apt-get install -y -qq tmux
fi

SESSION="claude-remote"

# Tuer une session existante du même nom
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Créer une session tmux détachée qui lance claude avec remote-control
tmux new-session -d -s "$SESSION" -c "$HOME/jupyter" "claude --dangerously-skip-permissions --remote-control"

echo ""
echo "Session tmux '$SESSION' créée."
echo ""
echo "Commandes utiles :"
echo "  tmux attach -t $SESSION    — se rattacher à la session"
echo "  tmux kill-session -t $SESSION — tuer la session"
echo ""
echo "L'URL de remote control s'affichera dans la session tmux."
echo "Pour la voir : tmux attach -t $SESSION"
