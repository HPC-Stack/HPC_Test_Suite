import os
import subprocess
import sys
from datetime import datetime


class BenchmarkRunner:
    def __init__(self):
        self.repo_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..')
        )

    def _resolve_spec_path(self, experiment_name):
        ext = os.path.splitext(experiment_name)[1]
        candidates = [
            experiment_name,
            os.path.join(self.repo_dir, 'benchmarks', 'specs', f'{experiment_name}.yaml'),
            os.path.join(self.repo_dir, 'benchmarks', 'specs', f'{experiment_name}.yml'),
            os.path.join(self.repo_dir, 'benchmarks', 'experiments', f'{experiment_name}.yaml'),
            os.path.join(self.repo_dir, 'benchmarks', 'experiments', f'{experiment_name}.yml'),
            os.path.join(self.repo_dir, 'benchmarks', 'specs', f'{experiment_name}.py'),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    def run_experiment(self, experiment, system=None, environ=None, dry_run=False):
        import yaml

        spec_path = self._resolve_spec_path(experiment)
        if not spec_path:
            print(f"Experiment spec not found: {experiment}", file=sys.stderr)
            return None

        with open(spec_path) as f:
            spec = yaml.safe_load(f)

        search_path = spec.get("search_path", spec.get("path", "."))
        tag = spec.get("tag", spec.get("tags", ["smoke"])[0] if isinstance(spec.get("tags"), list) else "smoke")
        if isinstance(tag, list):
            tag = tag[0]

        sys_arg = system or spec.get("system", "*:cpu")
        env_arg = environ or spec.get("environ", spec.get("environment", "gnu"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(
            self.repo_dir, "reports", f"{experiment}_{timestamp}.json"
        )
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        cmd = [
            "reframe", "-c", search_path, "-t", tag,
            "-S", f"valid_systems={sys_arg}",
            "-S", f"valid_prog_environs={env_arg}",
            "--report-file", report_file,
            "-r",
        ]

        print(f"Running: {' '.join(cmd)}")
        if dry_run:
            print("[DRY RUN] Would execute above command")
            return report_file

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            if result.stderr:
                print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr, file=sys.stderr)
            if result.returncode != 0:
                print(f"Benchmark exited with code {result.returncode}", file=sys.stderr)
            return report_file
        except subprocess.TimeoutExpired:
            print("Benchmark timed out (1h limit)", file=sys.stderr)
            return None
        except FileNotFoundError:
            print("reframe not found. Is the environment loaded?", file=sys.stderr)
            return None
