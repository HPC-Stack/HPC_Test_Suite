# Spack auto-install utility for ContinuousBench.
# Ensures a Spack package is available on any system.

import subprocess
import os
import sys

_installed_cache = {}


def spack_ensure(spec):
    '''Ensure a Spack package is installed.

    Args:
        spec: Spack spec string (e.g. 'gromacs@2024.2')

    Returns:
        Install prefix path (str), or empty string if unavailable.
    '''
    if spec in _installed_cache:
        return _installed_cache[spec]

    # Check if already installed
    try:
        result = subprocess.run(
            ['spack', 'location', '-i', spec],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            prefix = result.stdout.strip()
            _installed_cache[spec] = prefix
            return prefix
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # location may fail on ambiguous spec — try find with prefix format
    try:
        result = subprocess.run(
            ['spack', 'find', '--format', '{prefix}', spec],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            prefix = result.stdout.strip().split('\n')[0]
            _installed_cache[spec] = prefix
            return prefix
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Not installed — try to install
    try:
        print(f'[spack_ensure] Installing {spec} ...', file=sys.stderr)
        subprocess.run(
            ['spack', 'install', '--no-checksum', spec],
            check=True, capture_output=True, text=True, timeout=1800
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f'[spack_ensure] Failed to install {spec}: {e}', file=sys.stderr)
        _installed_cache[spec] = ''
        return ''

    # Get prefix after install
    try:
        result = subprocess.run(
            ['spack', 'location', '-i', spec],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            prefix = result.stdout.strip()
            _installed_cache[spec] = prefix
            return prefix
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    _installed_cache[spec] = ''
    return ''


def find_binary(name, spack_spec=None):
    '''Locate a binary, optionally via Spack install.

    Returns full path if found, or just *name* as PATH fallback.
    '''
    if spack_spec:
        prefix = spack_ensure(spack_spec)
        if prefix:
            bin_path = os.path.join(prefix, 'bin', name)
            if os.path.isfile(bin_path):
                return bin_path

    # Fall back to PATH
    return name


def clear_cache():
    '''Clear installation cache (e.g. at start of a new session).'''
    _installed_cache.clear()
