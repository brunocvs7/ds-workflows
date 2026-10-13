#!/usr/bin/env bash
# Aplica (ou atualiza) o ruleset protect-main e as configurações de merge em um repo.
# Uso: ./scripts/protect-repo.sh dono/repo [aprovacoes]
#   aprovacoes: quantas aprovações o PR exige (padrão 1; use 0 em projeto com um dev só)
set -euo pipefail
REPO="${1:?uso: $0 dono/repo [aprovacoes]}"
APPROVALS="${2:-1}"
TEMPLATE="$(cd "$(dirname "$0")/.." && pwd)/rulesets/protect-main.json"
RULESET="$(mktemp)"
trap 'rm -f "$RULESET"' EXIT

# Sem aprovação exigida, não há o que invalidar no último push.
jq --argjson n "$APPROVALS" '
  (.rules[] | select(.type == "pull_request") | .parameters)
    |= (.required_approving_review_count = $n | .require_last_push_approval = ($n > 0))
' "$TEMPLATE" > "$RULESET"

id=$(gh api "repos/$REPO/rulesets" -q '.[] | select(.name=="protect-main") | .id')
if [ -n "$id" ]; then
  gh api -X PUT "repos/$REPO/rulesets/$id" --input "$RULESET" >/dev/null
  echo "• ruleset atualizado em $REPO ($APPROVALS aprovação(ões))"
else
  gh api -X POST "repos/$REPO/rulesets" --input "$RULESET" >/dev/null
  echo "• ruleset criado em $REPO ($APPROVALS aprovação(ões))"
fi

gh api -X PATCH "repos/$REPO" \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true >/dev/null
echo "• merge configurado (só squash, apaga branch após merge) em $REPO"
