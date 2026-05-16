import os
import re

import yaml

REQUIRED_SPEC_FIELDS = ["name", "tags", "systems", "environ"]
RECOMMENDED_FIELDS = ["spack_spec", "binary", "time_limit"]
VALID_TAG_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
VALID_SYSTEM_PATTERN = re.compile(r'^[a-zA-Z0-9_*.\-]+(:[a-zA-Z0-9_*.\-]+)?$')


class BenchmarkValidator:
    def validate_file(self, path):
        if not os.path.exists(path):
            return False, [f"File not found: {path}"]

        _, ext = os.path.splitext(path)
        if ext not in (".yaml", ".yml", ".py"):
            return False, [f"Unsupported file extension: {ext} (expected .yaml or .py)"]

        if ext in (".yaml", ".yml"):
            return self._validate_yaml(path)
        return self._validate_python(path)

    def _validate_yaml(self, path):
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return False, [f"YAML parse error: {e}"]

        if not isinstance(data, dict):
            return False, ["YAML root must be a mapping"]

        errors = []

        benchmarks = data.get("benchmarks", [data])
        for i, bench in enumerate(benchmarks):
            prefix = f"benchmark[{i}]" if len(benchmarks) > 1 else "spec"
            merged = dict(data)
            merged.update(bench)
            for field in REQUIRED_SPEC_FIELDS:
                if field not in merged:
                    errors.append(f"{prefix}: missing required field '{field}'")

            if "name" in bench and not isinstance(bench["name"], str):
                errors.append(f"{prefix}: 'name' must be a string")

            if "tags" in bench:
                if isinstance(bench["tags"], list):
                    for tag in bench["tags"]:
                        if not VALID_TAG_PATTERN.match(str(tag)):
                            errors.append(f"{prefix}: invalid tag '{tag}' (lowercase alphanumeric + underscores only)")
                else:
                    errors.append(f"{prefix}: 'tags' must be a list")

            if "systems" in bench:
                if isinstance(bench["systems"], list):
                    for sys_name in bench["systems"]:
                        if not VALID_SYSTEM_PATTERN.match(str(sys_name)):
                            errors.append(f"{prefix}: invalid system '{sys_name}' (expected 'system:partition')")
                else:
                    errors.append(f"{prefix}: 'systems' must be a list")

            if "time_limit" in bench:
                tl = str(bench["time_limit"])
                if not re.match(r'^\d+[mhs]$', tl):
                    errors.append(f"{prefix}: invalid time_limit '{tl}' (e.g. '10m', '1h', '30s')")

            if "params" in bench and not isinstance(bench["params"], dict):
                errors.append(f"{prefix}: 'params' must be a mapping")

        return len(errors) == 0, errors

    def _validate_python(self, path):
        import ast
        errors = []
        try:
            with open(path) as f:
                ast.parse(f.read())
        except SyntaxError as e:
            errors.append(f"Python syntax error: {e}")
        return len(errors) == 0, errors

    def validate_spec_dict(self, spec):
        errors = []
        for field in REQUIRED_SPEC_FIELDS:
            if field not in spec:
                errors.append(f"Missing required field: '{field}'")
        if "tags" in spec and isinstance(spec["tags"], list):
            for tag in spec["tags"]:
                if not VALID_TAG_PATTERN.match(str(tag)):
                    errors.append(f"Invalid tag: '{tag}'")
        return len(errors) == 0, errors
