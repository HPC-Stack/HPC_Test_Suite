# ReFrame environment configuration for HPC_Test_Suite
# ReFrame is now installed via pip — run: pip install reframe
# This file is optional; env vars are auto-set by `continusbench run`.
module load miniconda 
conda activate continusbench

SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")

# Find all config fragments — common + environments always first, then pseudo-cluster + systems
_CONFIG_FILES="$SCRIPT_DIR/config/common/settings.py:$SCRIPT_DIR/config/environments/settings.py:$SCRIPT_DIR/config/systems/pseudo-cluster/settings.py"
for _dir in pseudo-cluster systems; do
  for _f in "$SCRIPT_DIR/config/$_dir"/*.py; do
    [ -f "$_f" ] && _CONFIG_FILES="$_CONFIG_FILES:$_f"
  done
done
export RFM_CONFIG_FILES=$_CONFIG_FILES

export RFM_CHECK_SEARCH_PATH=$SCRIPT_DIR/hpctestlib
export RFM_CHECK_SEARCH_RECURSIVE=yes
export RFM_GENERATE_FILE_REPORTS=true
