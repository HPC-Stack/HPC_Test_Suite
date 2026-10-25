#!/usr/bin/env bash

# Unified environment setup for HPC_Test_Suite

# Identify the script directory (Bash/Zsh compatible)
if [ -n "${BASH_VERSION-}" ]; then
    _this_file=${BASH_SOURCE[0]}
elif [ -n "${ZSH_VERSION-}" ]; then
    eval '_this_file=${(%):-%N}'
else
    echo "This script must be sourced from bash or zsh." >&2
    return 1 2>/dev/null || exit 1
fi

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$_this_file")" && pwd -P)"

# Add project bin directory to PATH
case ":$PATH:" in
    *":$SCRIPT_DIR/bin:"*) ;;
    *) PATH="$SCRIPT_DIR/bin${PATH+:$PATH}"; export PATH ;;
esac

# Dynamically discover ReFrame configuration files
_CONFIG_FILES="$SCRIPT_DIR/config/common/settings.py"
_CONFIG_FILES+=":$SCRIPT_DIR/config/environments/settings.py"

while IFS= read -r _f; do
    _CONFIG_FILES+=":$_f"
done < <(
    find "$SCRIPT_DIR/config/systems" "$SCRIPT_DIR/config/pseudo-cluster" \
        -type f -name 'settings.py' 2>/dev/null | sort
)

export RFM_CONFIG_FILES="$_CONFIG_FILES"

# ReFrame test discovery
export RFM_CHECK_SEARCH_PATH="$SCRIPT_DIR/hpctestlib"
export RFM_CHECK_SEARCH_RECURSIVE=yes
export RFM_GENERATE_FILE_REPORTS=true

echo "HPC_Test_Suite environment configured."
echo "ReFrame config files: $(echo "$RFM_CONFIG_FILES" | tr ':' '\n' | wc -l)"
