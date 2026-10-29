#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export USE_SPARK_SHIM=1 IPYTHONDIR="$ROOT/tools/ipython"
mkdir -p "$ROOT/data/lakehouse/Files"
cd "$ROOT/data/lakehouse"
for nb in "${@:-01_ingest 02_features_iris 03_ml 04_export_bi}"; do
  for n in $nb; do
    jupyter nbconvert --to notebook --execute "$ROOT/notebooks/$n.ipynb" --output "$ROOT/outputs/executions/run_$n.ipynb"
  done
done
