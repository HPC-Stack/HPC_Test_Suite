import os
import json
from datetime import datetime

import questionary
import yaml


class SystemGenerator:
    def __init__(self, config_dir=None):
        self.config_dir = config_dir or os.path.join(
            os.path.dirname(__file__), '..', '..', 'config', 'systems'
        )
        os.makedirs(self.config_dir, exist_ok=True)

    def interactive_onboard(self):
        name = questionary.text("System name (e.g., supermuc, paramrudra):").ask()
        if not name:
            return None

        hostname = questionary.text("Login hostname (or empty for local):").ask() or ""
        description = questionary.text("Short description:").ask() or ""

        partitions = []
        while True:
            pname = questionary.text("Partition name (leave empty to finish):").ask()
            if not pname:
                break
            ptype = questionary.select(
                f"Partition '{pname}' type:",
                choices=["cpu", "gpu", "hm", "login"],
            ).ask()
            scheduler = questionary.select(
                f"Scheduler for '{pname}':",
                choices=["slurm", "pbs", "local"],
            ).ask()
            partitions.append({"name": pname, "type": ptype, "scheduler": scheduler})

        if not partitions:
            partitions.append({"name": "default", "type": "cpu", "scheduler": "local"})

        config = {
            "name": name,
            "hostname": hostname,
            "description": description,
            "generated_at": datetime.now().isoformat(),
            "partitions": partitions,
        }

        filepath = os.path.join(self.config_dir, f"{name}.yaml")
        with open(filepath, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return filepath

    def load_system(self, name):
        filepath = os.path.join(self.config_dir, f"{name}.yaml")
        if not os.path.exists(filepath):
            return None
        with open(filepath) as f:
            return yaml.safe_load(f)
