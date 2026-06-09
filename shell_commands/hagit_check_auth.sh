#!/bin/bash
ssh -T git@github.com -i /config/.ssh/id_rsa_github -o StrictHostKeyChecking=no -o BatchMode=yes
status=$?
if [ $status -eq 1 ]; then
  echo "Erfolgreich via SSH bei GitHub authentifiziert."
  exit 0
elif [ $status -eq 255 ]; then
  echo "SSH-Authentifizierung zu GitHub fehlgeschlagen."
  exit 1
else
  echo "Unbekannte SSH-Antwort mit Status: $status"
  exit 2
fi
