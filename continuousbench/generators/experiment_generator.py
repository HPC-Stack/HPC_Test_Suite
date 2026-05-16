import os
from datetime import datetime

import questionary
import yaml


class ExperimentGenerator:
    def __init__(self, experiments_dir=None):
        self.experiments_dir = experiments_dir or os.path.join(
            os.path.dirname(__file__), '..', '..', 'benchmarks', 'experiments'
        )
        os.makedirs(self.experiments_dir, exist_ok=True)

    def interactive_create(self):
        name = questionary.text("Experiment name (e.g., hpcg_gpu_scale):").ask()
        if not name:
            return None

        description = questionary.text("Description:").ask() or ""

        benchmark = questionary.text("Benchmark spec file (relative to benchmarks/specs/):").ask()
        if not benchmark:
            benchmark = "hpcg.yaml"

        system = questionary.text("Target system (name:partition):").ask()
        environ = questionary.text("Programming environment:").ask() or "gnu"

        params = {}
        while True:
            pkey = questionary.text("Parameter name (leave empty to finish):").ask()
            if not pkey:
                break
            pval = questionary.text(f"  Value for '{pkey}':").ask()
            if pval:
                params[pkey] = pval

        experiment = {
            "name": name,
            "description": description,
            "generated_at": datetime.now().isoformat(),
            "benchmark": benchmark,
            "system": system,
            "environ": environ,
        }
        if params:
            experiment["params"] = params

        filepath = os.path.join(self.experiments_dir, f"{name}.yaml")
        with open(filepath, "w") as f:
            yaml.dump(experiment, f, default_flow_style=False, sort_keys=False)

        return filepath

    def load_experiment(self, name_or_path):
        if os.path.isfile(name_or_path):
            filepath = name_or_path
        else:
            filepath = os.path.join(self.experiments_dir, f"{name_or_path}.yaml")
            if not os.path.exists(filepath):
                return None
        with open(filepath) as f:
            return yaml.safe_load(f)
