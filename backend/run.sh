#!/usr/bin/env bash
# Start MARPS (map + planner + SLM API) using the Ollama server on the SLM machine through an SSH tunnel.
#   SLM_SSH_HOST  SSH host running Ollama on 127.0.0.1:11434 (default tfm-lab). Ignored if OLLAMA_HOST is set.
#   PYTHON        interpreter with backend/ and planner/ requirements (default python3)
# Extra arguments go to backend/app.py (for example --port 8770).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${OLLAMA_HOST:-}" ] && ! curl -sf --max-time 3 http://127.0.0.1:11434/api/version >/dev/null; then
  host="${SLM_SSH_HOST:-tfm-lab}"
  echo "Opening SSH tunnel to Ollama on $host…"
  ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:11434:127.0.0.1:11434 "$host"
fi
exec "${PYTHON:-python3}" backend/app.py "$@"
