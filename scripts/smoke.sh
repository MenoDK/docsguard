#!/usr/bin/env bash
# Black-box check of the running lab: every guard once, through the HTTP API, plus the two gates in front of it.
#
#   scripts/smoke.sh [base-url]        default http://localhost:8200   (make playground first)
#
# It leaves the sample clean, so it can be run again.
set -uo pipefail

A="${1:-http://localhost:8200}"
n=0
pass() { n=$((n + 1)); printf '  ok %2d  %s\n' "$n" "$1"; }
die() { printf '  FAIL    %s\n' "$1" >&2; exit 1; }

post() { curl -sS -m 20 -X POST "$A$1" -H 'content-type: application/json' -d "${2:-{\}}"; }
get() { curl -sS -m 10 "$A$1"; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
# check <label> <json> <jq expression that must be true>
check() { printf '%s' "$2" | jq -e "$3" >/dev/null 2>&1 || die "$1  (got: $(printf '%s' "$2" | jq -c 'del(.rendered)' 2>/dev/null | head -c 300))"; pass "$1"; }

echo "docsguard smoke test against $A"
post /api/lab/reset >/dev/null

# --- the front door ------------------------------------------------------------------------------------------------------
check "health says the lab is on" "$(get /api/health)" '.ok == true and .lab == true'
[ "$(code -H 'Host: evil.example.test' "$A/api/health")" = "403" ] || die "a foreign Host header was accepted"
pass "a foreign Host header is refused"
[ "$(code -X POST -H 'Origin: https://evil.example.test' -H 'content-type: application/json' -d '{}' "$A/api/lab/reset")" = "403" ] || die "a foreign Origin was accepted"
pass "a foreign Origin on a change is refused"
[ "$(code "$A/")" = "200" ] && [ "$(code "$A/lab.html")" = "200" ] || die "the landing page or the lab page is not served"
pass "the landing page and the lab page are served"
curl -sSI -m 5 "$A/" | grep -qi "^content-security-policy: default-src 'self'" || die "the page has no strict content security policy"
pass "the page carries a strict content security policy"
[ "$(code "$A/../README.md")" = "404" ] && [ "$(code --path-as-is "$A/../README.md")" = "404" ] || die "a path outside the site was served"
pass "nothing outside the site is served"

# --- the guards ----------------------------------------------------------------------------------------------------------
overview="$(get /api/overview)"
check "ten ways to break the sample and nine guards" "$overview" '(.breaks | length) == 10 and (.rules | length) == 9'
check "a fresh sample passes every guard" "$(get /api/check)" '.ok == true and .problems == 0 and ([.rules[] | select(.ok | not)] | length) == 0'

while IFS=$'\t' read -r id guard; do
  post /api/lab/break "{\"id\":\"$id\",\"on\":true}" >/dev/null
  answer="$(get /api/check)"
  check "break $id is caught by $guard" "$answer" ".ok == false and ([.rules[] | select(.rule == \"$guard\" and (.ok | not))] | length) == 1"
  post /api/lab/break "{\"id\":\"$id\",\"on\":false}" >/dev/null
  check "putting $id back restores every guard" "$(get /api/check)" '.ok == true'
done < <(printf '%s' "$overview" | jq -r '.breaks[] | [.id, .guard] | @tsv')

post /api/lab/break '{"id":"secret","on":true}' >/dev/null
if get /api/check | grep -q 'AKIA'; then die "the secret is in the answer"; fi
pass "the pasted key never appears in an answer"
post /api/lab/reset >/dev/null

# --- the hooks ------------------------------------------------------------------------------------------------------------
check "git-guard denies reset --hard" "$(post /api/hooks/git '{"command":"git reset --hard HEAD~3"}')" '.allowed == false and .rule == "reset-hard"'
check "git-guard denies it inside bash -c" "$(post /api/hooks/git '{"command":"bash -c \"git reset --hard\""}')" '.allowed == false'
check "git-guard lets git status through" "$(post /api/hooks/git '{"command":"git status"}')" '.allowed == true and .wire == ""'
check "scope-guard denies a write to .env" "$(post /api/hooks/scope '{"tool":"Write","target":".env"}')" '.allowed == false and .rule == "protected-path"'
post /api/lab/authorize '{"needle":".env","reason":""}' >/dev/null
check "a line without a reason is ignored, and the answer says so" "$(post /api/hooks/scope '{"tool":"Write","target":".env"}')" '.allowed == false and (.reason | test("ignored because they give no reason"))'
post /api/lab/authorize '{"needle":".env","reason":"staging file, reviewed in the pull request"}' >/dev/null
check "a line with a reason lets the write through" "$(post /api/hooks/scope '{"tool":"Write","target":".env"}')" '.allowed == true'
post /api/lab/reset >/dev/null
check "starting over removes the authorizations" "$(post /api/hooks/scope '{"tool":"Write","target":".env"}')" '.allowed == false'

# --- the budget -----------------------------------------------------------------------------------------------------------
before="$(get /api/budget | jq '.session_tokens')"
post /api/lab/break '{"id":"bloat","on":true}' >/dev/null
check "a grown CLAUDE.md goes over the budget" "$(get /api/budget)" ".session_tokens > $before * 4 and .session_tokens > .session_budget"
post /api/lab/reset >/dev/null
check "and starting over brings it back" "$(get /api/budget)" ".session_tokens == $before"

echo "all $n checks passed"
