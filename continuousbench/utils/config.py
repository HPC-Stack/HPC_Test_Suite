import os
import glob

import yaml


class ConfigManager:
    def __init__(self, config_dir=None):
        self.config_dir = config_dir or os.path.join(
            os.path.dirname(__file__), '..', '..', 'config'
        )
        self.systems_dir = os.path.join(self.config_dir, 'systems')
        self.partitions_dir = os.path.join(self.config_dir, 'partitions')
        self.generated_dir = os.path.join(self.config_dir, 'generated')

    def list_systems(self):
        pattern = os.path.join(self.systems_dir, "**", "*.yaml")
        systems = {}
        for fpath in sorted(glob.glob(pattern, recursive=True)):
            name = os.path.splitext(os.path.basename(fpath))[0]
            with open(fpath) as f:
                data = yaml.safe_load(f)
            systems[name] = data or {}
        return systems

    def get_system(self, name):
        fpath = os.path.join(self.systems_dir, f"{name}.yaml")
        if not os.path.exists(fpath):
            return None
        with open(fpath) as f:
            return yaml.safe_load(f)

    def save_generated_config(self, name, data):
        os.makedirs(self.generated_dir, exist_ok=True)
        fpath = os.path.join(self.generated_dir, f"{name}.py")
        with open(fpath, "w") as f:
            f.write(data)
        return fpath

    def read_config_file(self, *parts):
        fpath = os.path.join(self.config_dir, *parts)
        if not os.path.exists(fpath):
            return None
        with open(fpath) as f:
            return f.read()
