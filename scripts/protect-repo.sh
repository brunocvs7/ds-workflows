#!/usr/bin/env bash
# Aplica (ou atualiza) o ruleset protect-main e as configurações de merge em um repo.
# Uso: ./scripts/protect-repo.sh dono/repo
set -euo pipefail
REPO="${1:?uso: $0 dono/repo}"
RULESET="$(cd "$(dirname "$0")/.." && pwd)/rulesets/protect-main.json"

id=$(gh api "repos/$REPO/rulesets" -q '.[] | select(.name=="protect-main") | .id')
if [ -n "$id" ]; then
  gh api -X PUT "repos/$REPO/rulesets/$id" --input "$RULESET" >/dev/null
  echo "• ruleset atualizado em $REPO"
else
  gh api -X POST "repos/$REPO/rulesets" --input "$RULESET" >/dev/null
  echo "• ruleset criado em $REPO"
fi

gh api -X PATCH "repos/$REPO" \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true >/dev/null
echo "• merge configurado (só squash, apaga branch após merge) em $REPO"
