#!/bin/bash
# Convenience script: run benchmarks with env capture and report generation.
#
# Usage:
#   ./scripts/run_benchmark.sh                      # run all smoke tests
#   ./scripts/run_benchmark.sh basics/               # run basics smoke tests
#   ./scripts/run_benchmark.sh application/ cpu      # run app tests on cpu
#   ./scripts/run_benchmark.sh . gpu -t nightly      # run nightly-tagged tests on gpu

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

# Source environment
source setup.sh 2>/dev/null || echo "Warning: setup.sh not found, relying on existing env"

SEARCH_PATH="${1:-.}"
PARTITION="${2:-cpu}"
TAG="${3:-smoke}"
EXTRA_ARGS="${@:4}"

SYSTEM="paramrudra.snbose:$PARTITION"
ENVIRON="gnu"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="reports/benchmark_${TIMESTAMP}.json"
REPORT_HTML="reports/benchmark_${TIMESTAMP}.html"

mkdir -p reports

echo "=== ContinuousBench Run ==="
echo "  Search path: $SEARCH_PATH"
echo "  System:      $SYSTEM"
echo "  Environ:     $ENVIRON"
echo "  Tag:         $TAG"
echo "  Report:      $REPORT_FILE"
echo ""

reframe -c "$SEARCH_PATH" -t "$TAG" \
    -S valid_systems="$SYSTEM" \
    -S valid_prog_environs="$ENVIRON" \
    --report-file="$REPORT_FILE" \
    -r "$EXTRA_ARGS"

echo ""
echo "=== Generating Report ==="
python3 "$SCRIPT_DIR/generate_report.py" "$REPORT_FILE" "$REPORT_HTML"

echo ""
echo "=== Done ==="
echo "  JSON report: $REPORT_FILE"
echo "  HTML report: $REPORT_HTML"
