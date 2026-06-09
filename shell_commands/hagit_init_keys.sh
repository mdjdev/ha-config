#!/bin/bash
set -euo pipefail

mkdir -p /config/.ssh
#chmod 700 /config/.ssh
ssh-keygen -t rsa -b 4096 -f /config/.ssh/id_rsa_github
#ssh-keygen -t ed25519 -f /config/.ssh/id_ed25519_github -N "" -C "gitwatch-$(hostname)" >/dev/null

exit 0
