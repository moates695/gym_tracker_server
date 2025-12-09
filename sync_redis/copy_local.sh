#! /bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp ../app/api/middleware/database.py database.py
cp ../app/api/middleware/misc.py misc.py