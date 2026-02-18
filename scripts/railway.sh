#!/usr/bin/env bash
# Railway deployment helper - uses GraphQL API directly
# Usage: bash scripts/railway.sh <command>
set -euo pipefail

RAILWAY_TOKEN=$(python3 -c "import json; print(json.load(open('$HOME/.railway/config.json'))['user']['token'])")
API="https://backboard.railway.com/graphql/v2"
PROJECT_ID="f2147eb0-bdbc-41db-aeef-0befebd03be6"
SERVICE_ID="ee2928bc-1b39-4e46-8104-932c9ab968e5"
ENV_ID="f42b4d03-3c50-4584-b062-b38a8695f4f4"
APP_URL="https://linkedinbanana-production.up.railway.app"

gql() {
  curl -s -X POST "$API" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $RAILWAY_TOKEN" \
    -d "$1"
}

case "${1:-help}" in
  status)
    gql "{\"query\": \"query { deployments(first: 1, input: { projectId: \\\"$PROJECT_ID\\\", serviceId: \\\"$SERVICE_ID\\\", environmentId: \\\"$ENV_ID\\\" }) { edges { node { id status createdAt staticUrl } } } }\"}" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']['deployments']['edges'][0]['node']
print(f\"Deployment: {d['id']}\")
print(f\"Status:     {d['status']}\")
print(f\"Created:    {d['createdAt']}\")
print(f\"URL:        $APP_URL\")
"
    ;;
  logs)
    DEPLOY_ID=$(gql "{\"query\": \"query { deployments(first: 1, input: { projectId: \\\"$PROJECT_ID\\\", serviceId: \\\"$SERVICE_ID\\\", environmentId: \\\"$ENV_ID\\\" }) { edges { node { id } } } }\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['deployments']['edges'][0]['node']['id'])")
    gql "{\"query\": \"query { buildLogs(deploymentId: \\\"$DEPLOY_ID\\\", limit: 500) { message } }\"}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for log in data.get('data', {}).get('buildLogs', []):
    print(log.get('message', ''))
"
    ;;
  errors)
    DEPLOY_ID=$(gql "{\"query\": \"query { deployments(first: 1, input: { projectId: \\\"$PROJECT_ID\\\", serviceId: \\\"$SERVICE_ID\\\", environmentId: \\\"$ENV_ID\\\" }) { edges { node { id status } } } }\"}" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']['deployments']['edges'][0]['node']; print(d['id'])")
    STATUS=$(gql "{\"query\": \"query { deployments(first: 1, input: { projectId: \\\"$PROJECT_ID\\\", serviceId: \\\"$SERVICE_ID\\\", environmentId: \\\"$ENV_ID\\\" }) { edges { node { status } } } }\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['deployments']['edges'][0]['node']['status'])")
    echo "Status: $STATUS"
    echo "---"
    gql "{\"query\": \"query { buildLogs(deploymentId: \\\"$DEPLOY_ID\\\", limit: 500) { message } }\"}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
logs = data.get('data', {}).get('buildLogs', [])
error_keywords = ['error', 'Error', 'ERROR', 'fatal', 'FATAL', 'Failed', 'failed', 'FAILED', 'not found', 'denied', 'Traceback', 'exception', 'Exception']
found = False
for log in logs:
    msg = log.get('message', '')
    if any(kw in msg for kw in error_keywords):
        print(msg)
        found = True
if not found:
    print('No errors found in build logs.')
"
    ;;
  deploy-logs)
    DEPLOY_ID=$(gql "{\"query\": \"query { deployments(first: 1, input: { projectId: \\\"$PROJECT_ID\\\", serviceId: \\\"$SERVICE_ID\\\", environmentId: \\\"$ENV_ID\\\" }) { edges { node { id } } } }\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['deployments']['edges'][0]['node']['id'])")
    gql "{\"query\": \"query { deploymentLogs(deploymentId: \\\"$DEPLOY_ID\\\", limit: 200) { message } }\"}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for log in data.get('data', {}).get('deploymentLogs', []):
    print(log.get('message', ''))
"
    ;;
  redeploy)
    DEPLOY_ID=$(gql "{\"query\": \"query { deployments(first: 1, input: { projectId: \\\"$PROJECT_ID\\\", serviceId: \\\"$SERVICE_ID\\\", environmentId: \\\"$ENV_ID\\\" }) { edges { node { id } } } }\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['deployments']['edges'][0]['node']['id'])")
    gql "{\"query\": \"mutation { deploymentRedeploy(id: \\\"$DEPLOY_ID\\\") { id status } }\"}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'errors' in d:
    print(f\"Error: {d['errors'][0]['message']}\")
else:
    node = d['data']['deploymentRedeploy']
    print(f\"Redeployed: {node['id']} ({node['status']})\")
"
    ;;
  wait)
    # Poll until build finishes (SUCCESS or FAILED)
    echo "Waiting for deployment to finish..."
    while true; do
      STATUS=$(gql "{\"query\": \"query { deployments(first: 1, input: { projectId: \\\"$PROJECT_ID\\\", serviceId: \\\"$SERVICE_ID\\\", environmentId: \\\"$ENV_ID\\\" }) { edges { node { status } } } }\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['deployments']['edges'][0]['node']['status'])")
      echo "  Status: $STATUS"
      if [[ "$STATUS" == "SUCCESS" || "$STATUS" == "FAILED" || "$STATUS" == "CRASHED" ]]; then
        break
      fi
      sleep 10
    done
    echo "Final status: $STATUS"
    if [[ "$STATUS" != "SUCCESS" ]]; then
      echo "--- Errors ---"
      bash "$0" errors
    fi
    ;;
  help|*)
    echo "Railway deployment helper for LinkedInBanana"
    echo ""
    echo "Usage: bash scripts/railway.sh <command>"
    echo ""
    echo "Commands:"
    echo "  status       Show latest deployment status and URL"
    echo "  logs         Show full build logs"
    echo "  errors       Show only error lines from build logs"
    echo "  deploy-logs  Show runtime/deploy logs"
    echo "  redeploy     Trigger a redeploy"
    echo "  wait         Poll until build finishes, show errors if failed"
    echo ""
    echo "App URL: $APP_URL"
    ;;
esac
