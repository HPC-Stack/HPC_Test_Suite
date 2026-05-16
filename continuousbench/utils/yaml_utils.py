import os

import yaml


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def dump_yaml(data, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def merge_specs(base, override):
    merged = dict(base)
    for key, val in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = {**merged[key], **val}
        elif key in merged and isinstance(merged[key], list) and isinstance(val, list):
            merged[key] = merged[key] + val
        else:
            merged[key] = val
    return merged


def find_spec(name, search_dirs=None):
    if os.path.isfile(name):
        return name
    if search_dirs is None:
        search_dirs = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'benchmarks', 'specs'),
        ]
    for d in search_dirs:
        for ext in ['', '.yaml', '.yml']:
            fpath = os.path.join(d, f"{name}{ext}")
            if os.path.isfile(fpath):
                return fpath
    return None
