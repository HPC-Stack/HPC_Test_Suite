# ReFrame environment configuration for HPC_Test_Suite
# ReFrame is now installed via pip — run: pip install reframe
# This file is optional; env vars are auto-set by `continusbench run`.

SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
export RFM_CONFIG_FILES=$SCRIPT_DIR/config/common/settings.py:$SCRIPT_DIR/config/environments/settings.py:$SCRIPT_DIR/config/pseudo-cluster/settings.py
export RFM_CHECK_SEARCH_PATH=$SCRIPT_DIR
export RFM_CHECK_SEARCH_RECURSIVE=yes
export RFM_GENERATE_FILE_REPORTS=true
