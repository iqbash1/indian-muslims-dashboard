#!/bin/zsh
# Run the full NADA banking batch (resumable; surveys with MANIFEST.json skip).
# Detach-friendly: nohup nada/run_bank.sh & — survives session/terminal restarts.
# Log: ~/Desktop/nada-work/bank.log
set -u
cd "$(dirname "$0")/.."   # repo root
export NADA_API_KEY="$(cat nada/.key)"
LOG="$HOME/Desktop/nada-work/bank.log"
mkdir -p "$HOME/Desktop/nada-work"
{
  echo "=== batch start $(date '+%F %T') ==="
  while read -r slug idno; do
    [ -z "${slug:-}" ] && continue
    echo "######## $slug ########"
    .venv/bin/python nada/bank.py autoget "$idno" "$HOME/Desktop/nada-work/$slug" \
      || echo "!! survey error: $slug"
  done < nada/pairs.tsv
  echo "=== BATCH COMPLETE $(date '+%F %T') ==="
  n=0
  for d in "$HOME"/Desktop/nada-work/*/; do
    [ -f "$d/MANIFEST.json" ] && n=$((n+1))
  done
  echo "complete surveys: $n / $(wc -l < nada/pairs.tsv | tr -d ' ')"
  du -sh "$HOME/Desktop/nada-work"
} >> "$LOG" 2>&1
