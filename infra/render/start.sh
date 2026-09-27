#!/bin/sh
# Render entrypoint: joins the tailnet (userspace mode, no /dev/net/tun) and starts the API.
# Tailnet traffic goes through tailscaled's local proxy at localhost:1055.
set -eu

if [ -n "${TAILSCALE_AUTHKEY:-}" ]; then
  SOCK=/tmp/tailscaled.sock
  tailscaled \
    --tun=userspace-networking \
    --state=mem: \
    --socket="$SOCK" \
    --socks5-server=localhost:1055 \
    --outbound-http-proxy-listen=localhost:1055 \
    > /tmp/tailscaled.log 2>&1 &

  # A tailnet outage must not take down the API; cloud providers keep working.
  if tailscale --socket="$SOCK" up \
      --auth-key="$TAILSCALE_AUTHKEY" \
      --hostname="${TAILSCALE_HOSTNAME:-goblin-render}" \
      --timeout=30s; then
    # SOCKS5 is the canonical userspace-networking transport for private tailnet HTTP clients.\n    # Set it here so Render dashboard/Blueprint drift cannot silently switch the provider back to HTTP proxy mode.\n    export LLAMACPP_ORACLE_PROXY="socks5://localhost:1055"\n    echo "[tailscale] joined tailnet as ${TAILSCALE_HOSTNAME:-goblin-render}"
  else
    echo "[tailscale] WARNING: tailscale up failed; continuing without tailnet" >&2
    tail -20 /tmp/tailscaled.log >&2 || true
  fi
fi

exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8080}"
