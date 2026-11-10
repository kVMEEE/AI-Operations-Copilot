#!/bin/sh
set -eu
cd "$(dirname "$0")"
python -m pip install -r requirements.txt
make -C cpp_engine
python -m app.investigation.cli init-db
python -m app.investigation.cli index
