#!/bin/zsh
# Run a NADA banking batch (resumable; surveys with MANIFEST.json skip).
# Detach-friendly: nohup nada/run_bank.sh [pairs.tsv] [log] & — survives session
# restarts. Run several in parallel on DISJOINT pairs files for slow servers.
# Defaults: the full list nada/pairs.tsv, log ~/Desktop/nada-work/bank.log
set -u
cd "$(dirname "$0")/.."   # repo root
export NADA_API_KEY="$(cat nada/.key)"
PAIRS="${1:-nada/pairs.tsv}"
LOG="${2:-$HOME/Desktop/nada-work/bank.log}"
mkdir -p "$HOME/Desktop/nada-work"
{
  echo "=== batch start $(date '+%F %T')  pairs=$PAIRS ==="
  while read -r slug idno; do
    [ -z "${slug:-}" ] && continue
    echo "######## $slug ########"
    .venv/bin/python nada/bank.py autoget "$idno" "$HOME/Desktop/nada-work/$slug" \
      || echo "!! survey error: $slug"
  done < "$PAIRS"
  echo "=== BATCH COMPLETE $(date '+%F %T')  pairs=$PAIRS ==="
  n=0
  for d in "$HOME"/Desktop/nada-work/*/; do
    [ -f "$d/MANIFEST.json" ] && n=$((n+1))
  done
  echo "complete surveys overall: $n"
  du -sh "$HOME/Desktop/nada-work"
} >> "$LOG" 2>&1
