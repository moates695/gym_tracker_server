#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$SCRIPT_DIR/../app/api/middleware/database.py" "$SCRIPT_DIR/shared/" 