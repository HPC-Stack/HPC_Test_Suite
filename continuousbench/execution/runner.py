import os
import subprocess
import sys
import tempfile
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

    def _require_reframe(self):
        import shutil
        if shutil.which("reframe"):
            return True
        print("Error: reframe not found in PATH.", file=sys.stderr)
        print("Install it with:  pip install reframe", file=sys.stderr)
        print("Then verify:      reframe --version", file=sys.stderr)
        return False

    def _set_rfm_env(self):
        config_dir = os.path.join(self.repo_dir, "config")
        config_files = os.pathsep.join([
            os.path.join(config_dir, "common", "settings.py"),
            os.path.join(config_dir, "environments", "settings.py"),
            os.path.join(config_dir, "pseudo-cluster", "settings.py"),
        ])
        os.environ.setdefault("RFM_CONFIG_FILES", config_files)
        os.environ.setdefault("RFM_CHECK_SEARCH_PATH", self.repo_dir)
        os.environ.setdefault("RFM_CHECK_SEARCH_RECURSIVE", "yes")
        os.environ.setdefault("RFM_GENERATE_FILE_REPORTS", "true")

    def _default_system(self):
        config_path = os.path.join(self.repo_dir, "config", "pseudo-cluster", "settings.py")
        if os.path.isfile(config_path):
            try:
                ns = {}
                with open(config_path) as f:
                    exec(compile(f.read(), config_path, 'exec'), ns)
                systems = ns.get("site_configuration", {}).get("systems", [])
                if systems:
                    name = systems[0].get("name")
                    parts = systems[0].get("partitions", [])
                    if name and parts:
                        for p in parts:
                            if p.get("scheduler", p.get("name")) != "local":
                                return f"{name}:{p['name']}"
                        return f"{name}:{parts[0]['name']}"
                    if name:
                        return f"{name}:cpu"
            except Exception:
                pass
        return "paramrudra.snbose:cpu"

    def run_experiment(self, experiment, system=None, environ=None, dry_run=False):
        import yaml

        if not self._require_reframe():
            return None

        self._set_rfm_env()

        spec_path = self._resolve_spec_path(experiment)
        if not spec_path:
            print(f"Experiment spec not found: {experiment}", file=sys.stderr)
            return None

        with open(spec_path) as f:
            spec = yaml.safe_load(f)

        benchmarks = spec.get("benchmarks")
        if benchmarks:
            from continuousbench.generators.test_generator import TestGenerator
            temp_dir = tempfile.mkdtemp(prefix="cb_run_")
            gen = TestGenerator()
            gen.generate_from_spec(spec_path, temp_dir)
            search_path = temp_dir
        else:
            source = spec.get("source", spec.get("search_path", spec.get("path")))
            if source:
                source_path = os.path.join(self.repo_dir, source)
                if os.path.isfile(source_path):
                    search_path = source_path
                else:
                    search_path = source_path
            else:
                search_path = "."

        tag = spec.get("tag")

        sys_arg = system or spec.get("system") or self._default_system()
        env_arg = environ or spec.get("environ", spec.get("environment", "gnu"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = os.path.splitext(os.path.basename(experiment))[0]
        report_file = os.path.join(
            self.repo_dir, "reports", f"{safe_name}_{timestamp}.json"
        )
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        cmd = [
            "reframe", "-c", search_path,
            "-S", f"valid_prog_environs={env_arg}",
            "--report-file", report_file,
            "-r",
        ]
        if sys_arg:
            cmd.extend(["--system", sys_arg])
        if tag:
            cmd.extend(["-t", tag])
        name_filter = spec.get("name_filter")
        if name_filter:
            cmd.extend(["-n", name_filter])

        print(f"Running: {' '.join(cmd)}")
        if dry_run:
            print("[DRY RUN] Would execute above command")
            return report_file

        env = os.environ.copy()
        hooks_dir = os.path.join(self.repo_dir, 'continuousbench', 'hooks')
        env['PYTHONPATH'] = f"{hooks_dir}:{env.get('PYTHONPATH', '')}"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, env=env)
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
