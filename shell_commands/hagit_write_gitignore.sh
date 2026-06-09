#!/bin/bash
set -euo pipefail

touch /config/.gitignore
cat > /config/.gitignore << EOF
$1
EOF

exit 0
