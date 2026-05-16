# ReFrame environment configuration for HPC_Test_Suite
# ReFrame is now installed via pip — run: pip install reframe
# This file is optional; env vars are auto-set by `continusbench run`.

export RFM_CONFIG_FILES=$(dirname "$(realpath "$0")")/config/common/settings.py:$(dirname "$(realpath "$0")")/config/environments/settings.py:$(dirname "$(realpath "$0")")/config/pseudo-cluster/settings.py
export RFM_CHECK_SEARCH_PATH=$(dirname "$(realpath "$0")")
export RFM_CHECK_SEARCH_RECURSIVE=yes
export RFM_GENERATE_FILE_REPORTS=true
