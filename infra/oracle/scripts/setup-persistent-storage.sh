#!/usr/bin/env bash
set -euo pipefail

STORAGE_DEVICE="${STORAGE_DEVICE:-/dev/oracleoci/oraclevdb}"
STORAGE_MOUNT_POINT="${STORAGE_MOUNT_POINT:-/opt/goblin/data}"
STORAGE_FS_TYPE="${STORAGE_FS_TYPE:-ext4}"

log() {
  printf '[storage] %s\n' "$*"
}

append_fstab_entry() {
  local source="$1"
  local target="$2"
  local fstype="$3"
  local options="$4"
  local dump="${5:-0}"
  local pass="${6:-0}"
  local entry="${source} ${target} ${fstype} ${options} ${dump} ${pass}"

  if ! grep -Fqx -- "$entry" /etc/fstab; then
    printf '%s\n' "$entry" >> /etc/fstab
  fi
}

wait_for_device() {
  local attempts=0
  while [[ ! -b "$STORAGE_DEVICE" ]]; do
    attempts=$((attempts + 1))
    if [[ "$attempts" -ge 60 ]]; then
      log "storage device $STORAGE_DEVICE did not appear"
      exit 1
    fi
    sleep 2
  done
}

format_device_if_needed() {
  if blkid "$STORAGE_DEVICE" >/dev/null 2>&1; then
    return 0
  fi

  log "formatting $STORAGE_DEVICE as $STORAGE_FS_TYPE"
  mkfs."$STORAGE_FS_TYPE" -F "$STORAGE_DEVICE"
}

main() {
  log "preparing OCI persistent storage"
  systemctl stop docker.service docker.socket >/dev/null 2>&1 || true

  wait_for_device
  format_device_if_needed

  mkdir -p \
    "$STORAGE_MOUNT_POINT" \
    /var/lib/docker \
    /var/lib/redis \
    /var/log/goblin \
    /backups

  local volume_uuid
  volume_uuid="$(blkid -s UUID -o value "$STORAGE_DEVICE")"
  append_fstab_entry "UUID=${volume_uuid}" "$STORAGE_MOUNT_POINT" "$STORAGE_FS_TYPE" "defaults,_netdev,nofail" 0 2
  mountpoint -q "$STORAGE_MOUNT_POINT" || mount "$STORAGE_MOUNT_POINT"

  mkdir -p \
    "$STORAGE_MOUNT_POINT/docker" \
    "$STORAGE_MOUNT_POINT/redis" \
    "$STORAGE_MOUNT_POINT/logs/goblin/api" \
    "$STORAGE_MOUNT_POINT/logs/goblin/celery-worker" \
    "$STORAGE_MOUNT_POINT/backups" \
    "$STORAGE_MOUNT_POINT/state/api"

  append_fstab_entry "$STORAGE_MOUNT_POINT/docker" /var/lib/docker none "bind,nofail,x-systemd.requires-mounts-for=${STORAGE_MOUNT_POINT}" 0 0
  append_fstab_entry "$STORAGE_MOUNT_POINT/redis" /var/lib/redis none "bind,nofail,x-systemd.requires-mounts-for=${STORAGE_MOUNT_POINT}" 0 0
  append_fstab_entry "$STORAGE_MOUNT_POINT/logs/goblin" /var/log/goblin none "bind,nofail,x-systemd.requires-mounts-for=${STORAGE_MOUNT_POINT}" 0 0
  append_fstab_entry "$STORAGE_MOUNT_POINT/backups" /backups none "bind,nofail,x-systemd.requires-mounts-for=${STORAGE_MOUNT_POINT}" 0 0

  mount -a

  chown root:root "$STORAGE_MOUNT_POINT" "$STORAGE_MOUNT_POINT/docker"
  chown -R 999:999 "$STORAGE_MOUNT_POINT/redis"
  chown -R 1000:1000 "$STORAGE_MOUNT_POINT/logs/goblin"
  chown -R 1000:1000 "$STORAGE_MOUNT_POINT/state/api"
  chown ubuntu:ubuntu "$STORAGE_MOUNT_POINT/backups"

  chmod 0755 "$STORAGE_MOUNT_POINT" "$STORAGE_MOUNT_POINT/docker" "$STORAGE_MOUNT_POINT/redis" "$STORAGE_MOUNT_POINT/backups"
  chmod -R 0755 "$STORAGE_MOUNT_POINT/logs/goblin" "$STORAGE_MOUNT_POINT/state/api"

  log "persistent storage mounted at $STORAGE_MOUNT_POINT"
}

main "$@"
